import logging

import openai
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Azure OpenAIとの連携を行うサービスクラス
    """

    def __init__(self) -> None:
        self.api_key = settings.AZURE_OPENAI_KEY
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.embedding_deployment = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        self.completion_deployment = (
            settings.AZURE_OPENAI_COMPLETION_DEPLOYMENT
        )
        # 埋め込みモデル用のAPIバージョン
        self.embedding_api_version = getattr(
            settings, "AZURE_OPENAI_EMBEDDING_API_VERSION", "2023-05-15"
        )
        # 回答生成モデル用のAPIバージョン
        self.completion_api_version = getattr(
            settings, "AZURE_OPENAI_COMPLETION_API_VERSION", "2025-01-31"
        )

        # 埋め込みモデル用のクライアント
        self.embedding_client = openai.AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.embedding_api_version,
        )

        # 回答生成モデル用のクライアント
        self.completion_client = openai.AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.completion_api_version,
        )

    def create_embedding(self, text: str) -> list[float] | None:
        """
        テキストのベクトル表現（埋め込み）を生成する
        """
        try:
            # テキストが長すぎる場合は切り詰める
            max_tokens = 8000
            if len(text) > max_tokens * 4:  # 大まかな推定（1トークン≒4文字）
                text = text[: max_tokens * 4]

            response = self.embedding_client.embeddings.create(
                input=text, model=self.embedding_deployment
            )

            # レスポンスからベクトルを取得
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            return None

    def generate_answer(self, question: str, context: str) -> str | None:
        """
        質問と文脈から回答を生成する
        """
        try:
            # デバッグ情報を出力
            logger.info(f"API Version: {self.completion_api_version}")
            logger.info(f"Deployment Name: {self.completion_deployment}")
            logger.info(f"Endpoint: {self.endpoint}")

            # プロンプトを構築
            system_message = """
            あなたは企業の内部ドキュメントに基づいて質問に答える日本語のアシスタントです。
            与えられた文脈情報のみを使用して質問に答えてください。
            文脈情報に答えがない場合は、「その情報は文脈に含まれていません」と正直に答えてください。
            回答は簡潔で明確な日本語で提供してください。
            """

            user_message = f"""
            質問: {question}

            文脈情報:
            {context}
            """

            # ChatCompletionリクエストを送信
            try:
                response = self.completion_client.chat.completions.create(
                    model=self.completion_deployment,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    max_completion_tokens=1000,
                    stop=None,
                )

                # レスポンスから回答を取得
                content = response.choices[0].message.content
                answer = content.strip() if content else ""
                return answer
            except Exception as api_error:
                # APIエラーの詳細をログに出力
                logger.error(f"API エラー詳細: {str(api_error)}")
                raise
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return None

    def summarize_text(self, text: str, max_length: int = 1000) -> str | None:
        """
        長いテキストを要約する
        """
        try:
            # プロンプトを構築
            system_message = """
            あなたは長いテキストを簡潔に要約する専門家です。
            与えられたテキストの重要なポイントを抽出し、明確で簡潔な要約を作成してください。
            要約は日本語で提供してください。
            """

            # ChatCompletionリクエストを送信
            response = self.completion_client.chat.completions.create(
                model=self.completion_deployment,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": text},
                ],
                max_completion_tokens=max_length,
                stop=None,
            )

            # レスポンスから要約を取得
            content = response.choices[0].message.content
            summary = content.strip() if content else ""
            return summary
        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            return None

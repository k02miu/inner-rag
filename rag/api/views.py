import json
import logging
import re
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from slack_sdk.signature import SignatureVerifier

from rag.services.document_service import DocumentService
from rag.services.openai_service import OpenAIService
from rag.services.search_service import SearchService
from rag.services.slack_service import SlackService

logger = logging.getLogger(__name__)

# Slackの署名検証
signature_verifier = SignatureVerifier(settings.SLACK_SIGNING_SECRET)


def send_slack_message(
    slack_service: SlackService,
    channel: str,
    text: str,
    thread_ts: str,
) -> None:
    """Slackメッセージを送信する共通関数"""
    slack_service.post_message(
        channel=channel,
        text=text,
        thread_ts=thread_ts,
    )


def index_document(
    search_service: SearchService,
    openai_service: OpenAIService,
    slack_service: SlackService,
    content: str,
    source: str,
    doc_type: str,
    doc_id: str,
    channel: str,
    thread_ts: str,
) -> bool:
    """ドキュメントをインデックスに追加する共通関数"""
    embedding = openai_service.create_embedding(content)
    if not embedding:
        send_slack_message(
            slack_service,
            channel,
            f"テキストのベクトル化に失敗しました: {source}",
            thread_ts,
        )
        return False

    success = search_service.index_document(
        {
            "id": doc_id,
            "content": content,
            "embedding": embedding,
            "source": source,
            "type": doc_type,
        }
    )

    if success:
        send_slack_message(
            slack_service,
            channel,
            f"ドキュメントをインデックスに追加しました: {source}",
            thread_ts,
        )
    else:
        send_slack_message(
            slack_service,
            channel,
            f"ドキュメントのインデックス追加に失敗しました: {source}",
            thread_ts,
        )

    return success


@csrf_exempt
@api_view(["POST"])
def slack_events(request: HttpRequest) -> HttpResponse:
    """
    Slackからのイベントを処理するエンドポイント
    """
    # リクエストの署名検証
    headers = dict(request.headers.items())
    if not signature_verifier.is_valid_request(request.body, headers):
        logger.warning("Invalid request signature")
        return HttpResponse(status=403)

    # リクエストボディをJSONとしてパース
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return HttpResponse(status=400)

    # チャレンジリクエストに応答
    if payload.get("type") == "url_verification":
        return JsonResponse({"challenge": payload["challenge"]})

    # イベントタイプを確認
    if payload.get("type") != "event_callback":
        logger.warning(f"Unsupported event type: {payload.get('type')}")
        return HttpResponse(status=200)

    # イベントIDを確認し、重複イベントを処理しないようにする
    # (SlackはイベントIDを重複して送信してくるため、この仕組みがないと複数回イベントがトリガーされる)
    event_id = payload.get("event_id")
    if event_id:
        # グローバル変数で簡易的なキャッシュを管理
        # 分散環境の場合Redisなどにキャッシュさせるべき
        if not hasattr(slack_events, "processed_events"):
            slack_events.processed_events = {}

        # すでに処理済みのイベントIDかチェック
        if event_id in slack_events.processed_events:
            logger.info(f"重複イベントをスキップしました: {event_id}")
            return HttpResponse(status=200)

        # 処理済みとしてマーク（最大1000件保持）
        slack_events.processed_events[event_id] = True
        if len(slack_events.processed_events) > 1000:
            # 最も古いエントリから削除（簡易実装）
            key = next(iter(slack_events.processed_events))
            slack_events.processed_events.pop(key)

    event = payload.get("event", {})
    event_type = event.get("type")

    # メンションイベントを処理
    if event_type == "app_mention":
        return handle_app_mention(event, payload)

    # その他のイベントは無視
    return HttpResponse(status=200)


def handle_app_mention(
    event: dict[str, Any], payload: dict[str, Any]
) -> HttpResponse:
    """
    アプリへのメンションを処理する
    """
    text = event.get("text", "")
    channel = event.get("channel", "")
    ts = event.get("ts", "")

    # ファイルが添付されているか確認
    files = event.get("files", [])

    slack_service = SlackService()
    search_service = SearchService()
    openai_service = OpenAIService()
    document_service = DocumentService()

    try:
        # ファイルが添付されている場合はベクトルデータの投入処理
        if files:
            for file in files:
                file_id = file.get("id")
                file_name = file.get("name", "")
                file_type = file.get("filetype", "").lower()

                # サポートされているファイルタイプかチェック
                if file_type not in ["pdf", "docx", "xlsx", "doc", "xls"]:
                    send_slack_message(
                        slack_service,
                        channel,
                        f"サポートされていないファイル形式です: {file_name}",
                        ts,
                    )
                    continue

                # ファイルをダウンロード
                file_content = slack_service.download_file(file_id)
                if not file_content:
                    send_slack_message(
                        slack_service,
                        channel,
                        f"ファイルのダウンロードに失敗しました: {file_name}",
                        ts,
                    )
                    continue

                # ファイルからテキストを抽出
                text_content = document_service.extract_text(
                    file_content, file_type
                )
                if not text_content:
                    send_slack_message(
                        slack_service,
                        channel,
                        f"ファイルからテキストの抽出に失敗しました: {file_name}",
                        ts,
                    )
                    continue

                index_document(
                    search_service,
                    openai_service,
                    slack_service,
                    text_content,
                    file_name,
                    file_type,
                    file_id,
                    channel,
                    ts,
                )

        # URLを含む場合または import rag キーワードを含む場合はコンテンツ取り込み処理
        elif (
            "http://" in text
            or "https://" in text
            or "import rag" in text.lower()
        ):
            # URLを抽出（末尾の記号を削除）
            urls = re.findall(r"(https?://[^\s<>]+)", text)
            # URLから終端の記号を削除（>など）
            clean_urls = []
            for url in urls:
                clean_url = re.sub(r"[^\w/:\.-]$", "", url)
                clean_urls.append(clean_url)

            if clean_urls:
                for url in clean_urls:
                    # URLからコンテンツを取得
                    content = document_service.extract_from_url(url)
                    if not content:
                        send_slack_message(
                            slack_service,
                            channel,
                            f"URLからコンテンツの取得に失敗しました: {url}",
                            ts,
                        )
                        continue

                    import hashlib
                    url_hash = hashlib.md5(url.encode()).hexdigest()

                    index_document(
                        search_service,
                        openai_service,
                        slack_service,
                        content,
                        url,
                        "url",
                        url_hash,
                        channel,
                        ts,
                    )
            elif "import rag" in text.lower():
                send_slack_message(
                    slack_service,
                    channel,
                    "取り込みモードですが、有効なURLが見つかりませんでした。URLを含めてメッセージを送信してください。",
                    ts,
                )

        # それ以外の場合は質問に対する回答を生成
        else:
            # ボットメンションを除去して質問テキストを取得
            question = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

            if not question:
                send_slack_message(
                    slack_service,
                    channel,
                    "質問が空です。何について知りたいですか？",
                    ts,
                )
                return HttpResponse(status=200)

            # 質問のベクトル表現を作成
            query_embedding = openai_service.create_embedding(question)
            if not query_embedding:
                send_slack_message(
                    slack_service,
                    channel,
                    "質問のベクトル化に失敗しました。もう一度試してください。",
                    ts,
                )
                return HttpResponse(status=200)

            # ベクトル検索を実行
            search_results = search_service.search_documents(
                query_embedding, top_k=3
            )

            if not search_results:
                send_slack_message(
                    slack_service,
                    channel,
                    "関連する情報が見つかりませんでした。",
                    ts,
                )
                return HttpResponse(status=200)

            # 検索結果をコンテキストとして結合
            context = ""
            for i, result in enumerate(search_results, 1):
                content = result["content"]
                source = result["source"]
                context += f"[{i}] {content}\n\n出典: {source}\n\n"

            # 回答を生成
            answer = openai_service.generate_answer(question, context)

            if not answer:
                send_slack_message(
                    slack_service,
                    channel,
                    "回答の生成に失敗しました。もう一度試してください。",
                    ts,
                )
                return HttpResponse(status=200)

            # 回答を投稿
            send_slack_message(slack_service, channel, answer, ts)

        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Error handling app mention: {str(e)}")
        send_slack_message(
            slack_service,
            channel,
            f"エラーが発生しました: {str(e)}",
            ts,
        )
        return HttpResponse(status=200)

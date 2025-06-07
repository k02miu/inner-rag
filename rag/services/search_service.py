import logging
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from django.conf import settings

logger = logging.getLogger(__name__)


class SearchService:
    """
    Azure AI Searchとの連携を行うサービスクラス
    """

    def __init__(self) -> None:
        self.endpoint = settings.AZURE_SEARCH_ENDPOINT
        self.key = settings.AZURE_SEARCH_ADMIN_KEY
        self.index_name = settings.AZURE_SEARCH_INDEX_NAME
        self.credential = AzureKeyCredential(self.key)
        self.client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
        )

    def index_document(self, document: dict[str, Any]) -> bool:
        """
        ドキュメントをインデックスに追加する
        document: インデックスに追加するドキュメント
            {
                "id": ドキュメントID,
                "content": ドキュメントの内容,
                "embedding": ベクトル表現,
                "source": ドキュメントのソース（ファイル名やURL）,
                "type": ドキュメントの種類（pdf, docx, url等）
            }
        """
        try:
            result = self.client.upload_documents(documents=[document])
            return len(result) > 0 and result[0].succeeded
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            return False

    def search_documents(
        self, query_vector: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        ベクトル検索を実行する
        """
        try:
            # ベクトル検索クエリを作成
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top_k,
                fields="embedding",
            )

            # 検索を実行
            results = self.client.search(
                search_text=None,
                vector_queries=[vector_query],
                select=["id", "content", "source", "type"],
                top=top_k,
            )

            # 結果を整形
            documents = []
            for result in results:
                documents.append(
                    {
                        "id": result["id"],
                        "content": result["content"],
                        "source": result["source"],
                        "type": result["type"],
                        "score": result["@search.score"],
                    }
                )

            return documents
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """
        ドキュメントをインデックスから削除する
        """
        try:
            result = self.client.delete_documents(
                documents=[{"id": document_id}]
            )
            return len(result) > 0 and result[0].succeeded
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False

    def create_or_update_index(self) -> bool:
        """
        インデックスを作成または更新する
        """
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            VectorSearch,
            VectorSearchAlgorithmConfiguration,
            VectorSearchAlgorithmKind,
            VectorSearchProfile,
        )

        try:
            # インデックスクライアントを作成
            index_client = SearchIndexClient(
                endpoint=self.endpoint, credential=self.credential
            )

            # フィールドを定義
            fields = [
                SearchField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    searchable=True,
                ),
                SearchField(
                    name="content",
                    type=SearchFieldDataType.String,
                    searchable=True,
                ),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(
                        SearchFieldDataType.Single
                    ),
                    vector_search_dimensions=1536,  # OpenAI Ada-002の次元数
                    vector_search_profile_name="vector-profile",
                ),
                SearchField(
                    name="source",
                    type=SearchFieldDataType.String,
                    searchable=True,
                ),
                SearchField(
                    name="type",
                    type=SearchFieldDataType.String,
                    searchable=True,
                ),
            ]

            # ベクトル検索の設定
            vector_search = VectorSearch(
                algorithms=[
                    VectorSearchAlgorithmConfiguration(
                        name="vector-algorithm",
                        kind=VectorSearchAlgorithmKind.HNSW,
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="vector-profile",
                        algorithm_configuration_name="vector-algorithm",
                    )
                ],
            )

            # インデックスを作成
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
            )

            # インデックスを作成または更新
            result = index_client.create_or_update_index(index)
            return result is not None
        except Exception as e:
            logger.error(f"Error creating or updating index: {str(e)}")
            return False

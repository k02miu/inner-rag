import logging
from typing import Any

import requests
from django.conf import settings
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class SlackService:
    """
    Slack APIとの連携を行うサービスクラス
    """

    def __init__(self) -> None:
        self.client = WebClient(token=settings.SLACK_APP_TOKEN)

    def post_message(
        self, channel: str, text: str, thread_ts: str | None = None
    ) -> bool:
        """
        Slackチャンネルにメッセージを投稿する
        """
        try:
            kwargs = {"channel": channel, "text": text}

            if thread_ts:
                kwargs["thread_ts"] = thread_ts

            response = self.client.chat_postMessage(**kwargs)
            return response["ok"]
        except SlackApiError as e:
            logger.error(f"Error posting message to Slack: {str(e)}")
            return False

    def download_file(self, file_id: str) -> bytes | None:
        """
        Slackからファイルをダウンロードする
        """
        try:
            # ファイル情報を取得
            file_info = self.client.files_info(file=file_id)

            if not file_info["ok"]:
                logger.error(
                    f"Error getting file info: {file_info.get('error', 'Unknown error')}"  # noqa: E501
                )
                return None

            # ファイルのURLを取得
            file_url = file_info["file"]["url_private"]

            # ファイルをダウンロード
            headers = {"Authorization": f"Bearer {settings.SLACK_APP_TOKEN}"}
            response = requests.get(file_url, headers=headers)

            if response.status_code != 200:
                logger.error(
                    f"Error downloading file: HTTP {response.status_code}"
                )
                return None

            return response.content
        except SlackApiError as e:
            logger.error(f"Error downloading file from Slack: {str(e)}")
            return None
        except requests.RequestException as e:
            logger.error(f"Request error downloading file: {str(e)}")
            return None

    def get_user_info(self, user_id: str) -> dict[str, Any] | None:
        """
        ユーザー情報を取得する
        """
        try:
            response = self.client.users_info(user=user_id)
            if response["ok"]:
                return response["user"]
            else:
                logger.error(
                    f"Error getting user info: {response.get('error', 'Unknown error')}"  # noqa: E501
                )
                return None
        except SlackApiError as e:
            logger.error(f"Error getting user info from Slack: {str(e)}")
            return None

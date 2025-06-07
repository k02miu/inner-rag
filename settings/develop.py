from settings.base import *  # noqa: F401, F403

ENV = "develop"
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "deploy.your-domain.com"
    ]

# X-Forwarded-ヘッダーを信頼する
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Slack API設定
SLACK_APP_TOKEN = "xoxb-TOKEN_STRING"
SLACK_SIGNING_SECRET = "SECRET_STRING"
SLACK_BOT_NAME = "bot_chat"

# Azure AI Search設定
AZURE_SEARCH_ENDPOINT = "https://your-endpoint.search.windows.net"
AZURE_SEARCH_ADMIN_KEY = "KEY_STRING"
AZURE_SEARCH_INDEX_NAME = "documents-index"

# Azure OpenAI設定
AZURE_OPENAI_ENDPOINT = "https://your-endpoint.openai.azure.com"
AZURE_OPENAI_KEY = "KEY_STRING"  # noqa: E501
AZURE_OPENAI_EMBEDDING_API_VERSION = "YYYY-MM-DD"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "text-embedding-3-small"
AZURE_OPENAI_COMPLETION_API_VERSION = "YYYY-MM-DD-preview"
AZURE_OPENAI_COMPLETION_DEPLOYMENT = "gpt-4o"

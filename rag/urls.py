from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from rag.api.views import slack_events

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/slack/events", slack_events, name="slack_events"),
]

# 開発環境でのメディアファイルの提供
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

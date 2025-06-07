FROM python:3.11-slim

WORKDIR /app

# 依存パッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pythonのライブラリのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトファイルをコピー
COPY . .

# 環境変数を設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=settings.production

# 静的ファイルを収集
RUN mkdir -p /app/staticfiles
RUN python manage.py collectstatic --noinput

# ポートを公開
EXPOSE 8000

# 起動コマンド
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:application"] 

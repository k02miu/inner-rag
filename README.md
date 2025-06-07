# inner-rag

## 概要
Azureのサンドボックスもらったので試しに作ったもの。  
企業内でSlackと接続してドキュメントを読み込ませて応答するRAGのChatbotを目的としていたが、
画像の読み込みやExcelの表現の読み込みでかなり作り込まないとうまくこちらのコンテキストを汲み取れず
劣化Notebook LMにしかならないため断念した。（ものを上げた）

## 技術スタック

- Azure Container Apps
- Azure AI Search
- Azure Open AI 4o
- Open AI text-embedding-3
- Slack App
- Python
- Docker

## 機能

### ベクトルデータの検索とチャット回答

1. Slack Appにたいしてメンションと質問がつけられた場合に動作
2. 質問内容をSlack AppからAZure Container Appsに送信
3. Azure Container AppsはOpen AIのtext-embedding-3を使ってチャットの内容をベクトル化
4. ベクトルデータをAzure AI Searchで検索
5. 検索結果をAzure Open AI 4oを利用して回答を生成、Slack Appに返信

### ドキュメントのアップロード（ベクトルデータの投入）

1. Slack Appに対するメンションとワードがつけられたドキュメントファイル（pdf, word, excel）またはURLが添付されている場合に動作。
2. ドキュメントまたはURLをAzure Container Appsに送信。
3. Azure Container AppsはOpenAIのtext-embedding-3を使ってドキュメントをベクトル化
4. ベクトルデータをAzure AI Searchに取り込む

## 課題

- Slackから複数回送信されてくるイベントの重複処理制御が分散環境に対応していない
- ExcelやPDFで図やグラフ、位置関係によるコンテキストを読み取ることができない
- ドキュメントやURL先の画像などは完全に無視する

## 結論
現時点だとNotebook LMを利用する方が明らかにコスパがいい。
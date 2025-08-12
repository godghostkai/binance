# Binance to Google Sheets Updater

此專案會透過 GitHub Actions 定期抓取 Binance 交易紀錄並更新到 Google Sheets。

## 使用方式
1. Fork 此專案到你的 GitHub 帳號
2. 在 GitHub 設定 Secrets:
   - BINANCE_API_KEY
   - BINANCE_API_SECRET
   - GOOGLE_SHEET_ID
   - GOOGLE_SERVICE_ACCOUNT_JSON
3. Google Sheet 必須分享給 Service Account Email
4. GitHub Actions 會每 6 小時自動更新一次

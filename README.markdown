# 免費中小企業排班通

## 簡介
免費中小企業排班通 是一個免費的線上排班系統，專為中小企業設計，支援 Google 帳戶登入、多人協作、和直觀的日曆視圖。系統提供創建班表、加入班表、管理班次等功能，免費版支援最多 5 名協作者，日期範圍為 2025-01-01 至 2099-12-31。

網站最終部署於 `https://123go.tw/`，提供響應式設計，適配手機、平板、和桌面設備。

## 功能
- **Google 登入**：使用 Google 帳戶快速註冊與登入。
- **班表管理**：
  - 創建班表，自動生成 10 位數唯一 ID（唯讀）。
  - 加入他人班表，支援最多 5 名協作者。
  - 管理班次，支援月/週/日視圖，包含提醒功能。
- **權限管理**：
  - 擁有者可管理協作者、更新班次類型、匯出班表。
  - 協作者可新增/刪除自己的班次。
- **歷史記錄**：追蹤所有班表操作（僅擁有者可見）。
- **SEO 優化**：針對「排班系統」「免費排班系統」「線上排班系統」「排班」優化，支援 Google 搜尋。

## 專案結構
```
├── app.py
├── index.html           # 登入頁面
├── freeindex.html       # 主頁，含「如何開始」區塊
├── schedule.html        # 班表管理頁面
├── static/
│   ├── style.css
│   ├── logo.png        # 需自行提供
│   ├── favicon.ico     # 需自行提供
│   └── img/
│       ├── 01.jpg      # 創建班表示意圖
│       ├── 02.jpg      # 加入班表示意圖
│       └── 03.jpg      # 管理班次示意圖
├── init.sql
├── requirements.txt
├── .gitignore
└── README.md
```

## 安裝與本地運行
1. **克隆倉庫**：
   ```bash
   git clone https://github.com/yourusername/free-sme-scheduler.git
   cd free-sme-scheduler
   ```

2. **設置虛擬環境**：
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **安裝依賴**：
   ```bash
   pip install -r requirements.txt
   ```

4. **設置 Google OAuth**：
   - 在 [Google Cloud Console](https://console.cloud.google.com/) 創建 OAuth 2.0 憑證。
   - 設置回調 URL 為 `http://localhost:5000/authorize`（本地測試）。
   - 在環境變數中設置：
     ```bash
     export GOOGLE_CLIENT_ID=your_client_id
     export GOOGLE_CLIENT_SECRET=your_client_secret
     ```

5. **初始化資料庫**：
   ```bash
   sqlite3 schedule.db < init.sql
   ```

6. **運行應用**：
   ```bash
   python app.py
   ```
   - 訪問 `http://localhost:5000` 進行測試。

## 部署到 GitHub
請參考下方「部署到 GitHub」部分。

## 注意事項
- **圖片準備**：需自行提供 `/img/01.jpg`, `/img/02.jpg`, `/img/03.jpg`（建議 600x400 像素，JPG，<100KB）。
- **Google OAuth**：確保 `client_id` 和 `client_secret` 正確配置。
- **RWD**：所有頁面已使用 Tailwind CSS 優化，支援手機、平板、桌面。
- **SEO**：已針對關鍵字「排班系統」「免費排班系統」「線上排班系統」「排班」優化。

## 聯繫
如需支援或升級高級版，請聯繫：support@123go.tw（模擬）。
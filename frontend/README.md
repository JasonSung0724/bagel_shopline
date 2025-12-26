# 減醣市集 訂單報告生成器

將多平台電商訂單整合並生成標準化出貨報告的網頁應用程式。

## 功能特點

- 支援 4 個電商平台：SHOPLINE、C2C、MIXX、奧世國際
- 拖曳上傳 Excel 檔案
- 即時資料預覽
- 自動計算紙箱類型
- 產品配置管理（支援匯入/匯出）
- 一鍵生成並下載報告

## 技術架構

- **框架**: Next.js 14 + React 18
- **語言**: TypeScript
- **樣式**: Tailwind CSS
- **Excel 處理**: xlsx + exceljs
- **部署**: Vercel

## 本地開發

```bash
npm install
npm run dev
```

## 部署設定

### Vercel 設定

1. 在 Vercel 建立專案
2. 設定 GitHub Secrets:
   - `VERCEL_TOKEN`: Vercel API Token
   - `VERCEL_ORG_ID`: 組織 ID
   - `VERCEL_PROJECT_ID`: 專案 ID

### 取得 Vercel 設定

```bash
npm i -g vercel
vercel login
vercel link
```

執行後會在 `.vercel/project.json` 找到 `orgId` 和 `projectId`。

## 專案結構

```
├── src/
│   ├── app/              # Next.js App Router
│   ├── components/       # React 元件
│   ├── lib/
│   │   ├── excel/        # Excel 讀寫
│   │   ├── hooks/        # React Hooks
│   │   ├── processors/   # 訂單處理器
│   │   ├── types/        # TypeScript 類型
│   │   └── utils/        # 工具函數
│   └── config/           # 配置檔案
└── .github/workflows/    # CI/CD
```

## 分支說明

- `main` - Next.js 網頁版（生產環境）
- `app` - 原始 Python 桌面版

## 授權

MIT

# Coach Vocabulary Backend

基於間隔重複記憶法（Spaced Repetition）的英語單字學習 API 後端。

## 技術棧

- **框架**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **資料庫**: PostgreSQL
- **遷移工具**: Alembic

## 快速開始

### 1. 環境設定

```bash
# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 複製環境變數檔案
cp .env.example .env
```

### 2. 啟動資料庫

使用 Docker Compose：

```bash
docker compose up -d
```

或者使用本地 PostgreSQL，並修改 `.env` 中的 `DATABASE_URL`。

### 3. 執行資料庫遷移

```bash
# 生成遷移
alembic revision --autogenerate -m "Initial migration"

# 執行遷移
alembic upgrade head
```

### 4. 啟動 API 伺服器

```bash
uvicorn app.main:app --reload
```

API 將運行在 http://localhost:8000

### 5. 查看 API 文件

開啟瀏覽器訪問：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端點

| 模組 | 端點 | 方法 | 說明 |
|------|------|------|------|
| Auth | `/api/auth/login` | POST | 登入/自動註冊 |
| Home | `/api/home/stats` | GET | 首頁統計 |
| Home | `/api/home/word-pool` | GET | 單字池列表 |
| Learn | `/api/learn/session` | GET | 取得學習 Session |
| Learn | `/api/learn/complete` | POST | 完成學習 |
| Practice | `/api/practice/session` | GET | 取得練習 Session |
| Practice | `/api/practice/submit` | POST | 提交練習答案 |
| Review | `/api/review/session` | GET | 取得複習 Session |
| Review | `/api/review/complete` | POST | 完成複習展示 |
| Review | `/api/review/submit` | POST | 提交複習答案 |
| Admin | `/api/admin/reset-progress` | POST | 重置進度 |
| Admin | `/api/admin/seed-words` | POST | 匯入單字 |
| Admin | `/api/admin/words` | GET | 取得所有單字 |

## 使用流程

1. **登入**：POST `/api/auth/login` 取得 user ID
2. **匯入單字**：POST `/api/admin/seed-words` 匯入單字庫
3. **查看統計**：GET `/api/home/stats` 確認可用操作
4. **開始學習**：GET `/api/learn/session` → POST `/api/learn/complete`
5. **等待時間**：等待 10 分鐘後可以練習
6. **開始練習**：GET `/api/practice/session` → POST `/api/practice/submit`

## 匯入單字庫

使用 `/api/admin/seed-words` 匯入單字：

```bash
curl -X POST http://localhost:8000/api/admin/seed-words \
  -H "Content-Type: application/json" \
  -d @data/words.json
```

或者在 Swagger UI 中使用。

## 專案結構

```
coach-vocabulary-backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 設定檔
│   ├── database.py          # 資料庫連線
│   ├── dependencies.py      # 依賴注入
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API 路由
│   ├── services/            # 業務邏輯
│   ├── repositories/        # 資料存取層
│   └── utils/               # 工具函式
├── alembic/                 # 資料庫遷移
├── data/                    # 測試資料
├── static/                  # 靜態檔案
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 課程架構 (Curriculum)

學習系統引入了「等級 (Level)」和「分類 (Category)」的機制：

1. **等級 (Level)**：如 A1.1, A1.2, A2.1 等。
2. **分類 (Category)**：如 "Basic Descriptors", "Time & Space" 等。

### 學習流程
- 系統會優先提供使用者「目前等級」與「目前分類」中的單字。
- 當目前分類單字學完後，會自動進入同等級的下一個分類。
- 當該等級所有分類學完後，會自動晉升到下一個等級。

### 資料庫初始化
執行以下指令來初始化等級與分類資料：

```bash
python scripts/seed_levels_and_categories.py
```

## 池系統

| 池 | 等待時間 | 測驗題型 |
|----|----------|----------|
| P0 | - | 待學習 |
| P1 | 10 分鐘 | Reading Lv1 |
| P2 | 20 小時 | Listening Lv1 |
| P3 | 44 小時 | Speaking Lv1 |
| P4 | 68 小時 | Reading Lv2 |
| P5 | 164 小時 | Speaking Lv2 |
| P6 | ∞ | 完全掌握 |
| R1-R5 | 複習:10分鐘 / 練習:20小時 | 同對應P池 |

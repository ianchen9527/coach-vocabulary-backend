# Coach Vocabulary API 使用說明

## 概述

Coach Vocabulary API 是一個基於間隔重複記憶法（Spaced Repetition）的英語單字學習後端服務。

- **Base URL**: `http://localhost:8000`
- **API 文件**: `http://localhost:8000/docs` (Swagger UI)
- **認證方式**: 透過 HTTP Header `X-User-Id` 傳遞用戶 UUID

---

## 認證

除了 `/api/auth/login` 和 `/api/admin/seed-words` 外，所有 API 都需要在 Header 中帶入用戶 ID：

```
X-User-Id: <user-uuid>
```

---

## API 端點

### 1. 認證 (Auth)

#### POST /api/auth/login

登入或自動註冊。若用戶名存在則返回該用戶，不存在則自動建立。

**Request Body:**
```json
{
  "username": "string (1-50字元)"
}
```

**Response 200:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "created_at": "2024-01-08T10:30:00Z",
  "is_new_user": true
}
```

---

### 2. 首頁 (Home)

#### GET /api/home/stats

取得首頁統計資料。

**Headers:** `X-User-Id: <uuid>`

**Response 200:**
```json
{
  "today_learned": 5,
  "available_practice": 10,
  "available_review": 3,
  "upcoming_24h": 8,
  "can_learn": true,
  "can_practice": true,
  "can_review": true,
  "next_available_time": "2024-01-08T11:30:00Z"
}
```

| 欄位 | 說明 |
|------|------|
| today_learned | 今日已學習的新單字數 |
| available_practice | 目前可練習的單字數 |
| available_review | 目前可複習的單字數 |
| upcoming_24h | 24小時內即將可用的單字數 |
| can_learn | 是否可以開始學習模式 |
| can_practice | 是否可以開始練習模式 |
| can_review | 是否可以開始複習模式 |
| next_available_time | 下次最早可用時間（僅當無可用活動時） |

---

#### GET /api/home/word-pool

取得所有單字池狀態（Debug 用）。

**Headers:** `X-User-Id: <uuid>`

**Response 200:**
```json
{
  "pools": {
    "P0": [{"word_id": "...", "word": "ubiquitous", "translation": "無處不在的", "next_available_time": null}],
    "P1": [],
    "P2": [],
    "P3": [],
    "P4": [],
    "P5": [],
    "P6": [],
    "R1": [],
    "R2": [],
    "R3": [],
    "R4": [],
    "R5": []
  },
  "total_count": 214
}
```

---

### 3. 學習 (Learn)

#### GET /api/learn/session

取得學習 Session（5 個新單字 + 測驗題目）。

**Headers:** `X-User-Id: <uuid>`

**Response 200 (可學習):**
```json
{
  "available": true,
  "reason": null,
  "words": [
    {
      "id": "550e8400-...",
      "word": "ubiquitous",
      "translation": "無處不在的",
      "sentence": "Smartphones have become ubiquitous.",
      "sentence_zh": "智慧型手機已經變得無處不在。",
      "image_url": "/static/images/abc123.png",
      "audio_url": null
    }
  ],
  "exercises": [
    {
      "word_id": "550e8400-...",
      "type": "reading_lv1",
      "options": [
        {"index": 0, "word_id": "...", "translation": "模糊的", "image_url": "..."},
        {"index": 1, "word_id": "...", "translation": "無處不在的", "image_url": "..."},
        {"index": 2, "word_id": "...", "translation": "明確的", "image_url": "..."},
        {"index": 3, "word_id": "...", "translation": "隱含的", "image_url": "..."}
      ],
      "correct_index": 1
    }
  ]
}
```

**Response 200 (不可學習):**
```json
{
  "available": false,
  "reason": "daily_limit_reached",
  "words": [],
  "exercises": []
}
```

| reason | 說明 |
|--------|------|
| daily_limit_reached | 今日已學習 50 個單字 |
| p1_pool_full | P1 池中即將可用的單字 ≥ 10 個 |
| no_words_in_p0 | P0 池已無單字可學習 |

---

#### POST /api/learn/complete

完成學習，將單字從 P0 移到 P1。

**Headers:** `X-User-Id: <uuid>`

**Request Body:**
```json
{
  "word_ids": ["uuid1", "uuid2", "uuid3", "uuid4", "uuid5"]
}
```

**Response 200:**
```json
{
  "success": true,
  "words_moved": 5,
  "today_learned": 10
}
```

---

### 4. 練習 (Practice)

#### GET /api/practice/session

取得練習 Session（5 個單字，依題型排序）。

**Headers:** `X-User-Id: <uuid>`

**Response 200 (可練習):**
```json
{
  "available": true,
  "reason": null,
  "exercises": [
    {
      "word_id": "...",
      "word": "ubiquitous",
      "translation": "無處不在的",
      "image_url": "/static/images/abc123.png",
      "audio_url": null,
      "pool": "P1",
      "type": "reading_lv1",
      "options": [...],
      "correct_index": 0
    }
  ],
  "exercise_order": ["reading_lv1", "listening_lv1", "speaking_lv1"]
}
```

**Response 200 (不可練習):**
```json
{
  "available": false,
  "reason": "not_enough_words",
  "exercises": [],
  "exercise_order": []
}
```

---

#### POST /api/practice/submit

提交練習答案。

**Headers:** `X-User-Id: <uuid>`

**Request Body:**
```json
{
  "answers": [
    {"word_id": "uuid1", "correct": true},
    {"word_id": "uuid2", "correct": false}
  ]
}
```

**Response 200:**
```json
{
  "success": true,
  "results": [
    {
      "word_id": "uuid1",
      "correct": true,
      "previous_pool": "P1",
      "new_pool": "P2",
      "next_available_time": "2024-01-09T06:30:00Z"
    },
    {
      "word_id": "uuid2",
      "correct": false,
      "previous_pool": "P2",
      "new_pool": "R2",
      "next_available_time": "2024-01-08T10:40:00Z"
    }
  ],
  "summary": {
    "correct_count": 1,
    "incorrect_count": 1
  }
}
```

---

### 5. 複習 (Review)

複習模式分為兩階段：
1. **展示階段**: 顯示單字內容
2. **測驗階段**: 進行測驗（20 小時後）

#### GET /api/review/session

取得複習 Session（3-5 個單字）。

**Headers:** `X-User-Id: <uuid>`

**Response 200:**
```json
{
  "available": true,
  "reason": null,
  "words": [
    {
      "id": "...",
      "word": "ephemeral",
      "translation": "短暫的",
      "sentence": "Fame is often ephemeral.",
      "sentence_zh": "名聲往往是短暫的。",
      "image_url": "...",
      "audio_url": null,
      "pool": "R1"
    }
  ],
  "exercises": [...]
}
```

---

#### POST /api/review/complete

完成複習展示階段，標記進入練習階段。

**Headers:** `X-User-Id: <uuid>`

**Request Body:**
```json
{
  "word_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response 200:**
```json
{
  "success": true,
  "words_completed": 3,
  "next_practice_time": "2024-01-09T06:30:00Z"
}
```

---

#### POST /api/review/submit

提交複習測驗答案（R 池練習階段）。

**Headers:** `X-User-Id: <uuid>`

**Request Body:**
```json
{
  "answers": [
    {"word_id": "uuid1", "correct": true},
    {"word_id": "uuid2", "correct": false}
  ]
}
```

**Response 200:**
```json
{
  "success": true,
  "results": [
    {
      "word_id": "uuid1",
      "correct": true,
      "previous_pool": "R1",
      "new_pool": "P1",
      "next_available_time": "2024-01-08T10:40:00Z"
    },
    {
      "word_id": "uuid2",
      "correct": false,
      "previous_pool": "R2",
      "new_pool": "R2",
      "next_available_time": "2024-01-08T10:40:00Z"
    }
  ],
  "summary": {
    "correct_count": 1,
    "incorrect_count": 1,
    "returned_to_p": 1
  }
}
```

---

### 6. 管理 (Admin)

#### POST /api/admin/reset-progress

重置用戶的所有學習進度。

**Headers:** `X-User-Id: <uuid>`

**Response 200:**
```json
{
  "success": true,
  "words_reset": 50
}
```

---

#### POST /api/admin/seed-words

匯入單字庫。

**Request Body:**
```json
{
  "words": [
    {
      "word": "ubiquitous",
      "translation": "無處不在的",
      "sentence": "Smartphones have become ubiquitous.",
      "sentence_zh": "智慧型手機已經變得無處不在。",
      "image_url": "/static/images/abc123.png",
      "audio_url": null
    }
  ],
  "clear_existing": false
}
```

**Response 200:**
```json
{
  "success": true,
  "words_imported": 200,
  "words_skipped": 5
}
```

---

#### GET /api/admin/words

取得所有單字列表。

**Response 200:**
```json
{
  "words": [
    {
      "id": "...",
      "word": "ubiquitous",
      "translation": "無處不在的",
      "sentence": "...",
      "sentence_zh": "...",
      "image_url": "...",
      "audio_url": null,
      "created_at": "2024-01-08T10:00:00Z"
    }
  ],
  "total_count": 214
}
```

---

## 錯誤回應

所有錯誤回應格式：

```json
{
  "detail": "Error message"
}
```

| HTTP Status | 說明 |
|-------------|------|
| 400 | 請求參數錯誤 |
| 401 | X-User-Id header 缺失 |
| 404 | 資源不存在 |
| 500 | 伺服器內部錯誤 |

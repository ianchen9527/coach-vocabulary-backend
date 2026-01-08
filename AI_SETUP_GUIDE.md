# AI Agent Setup Guide

This document provides step-by-step instructions for AI agents (Claude Code, Gemini CLI, etc.) to set up the Coach Vocabulary Backend development environment from scratch.

## Overview

**Goal**: Set up a fully functional development server with seeded data.

**Prerequisites to install if missing**:
- Python 3.9+ (3.11 recommended)
- PostgreSQL 14+
- pip

**Final verification**: `curl http://localhost:8000/health` returns `{"status":"healthy"}`

---

## Step 1: Check and Install Prerequisites

### 1.1 Check Python

```bash
python3 --version
```

**Expected**: Python 3.9.x or higher

**If not installed or version too old**:
- macOS: `brew install python@3.11`
- Ubuntu/Debian: `sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip`
- Windows: Download from https://www.python.org/downloads/

### 1.2 Check PostgreSQL

```bash
psql --version
```

**Expected**: psql (PostgreSQL) 14.x or higher

**If not installed**:
- macOS: `brew install postgresql@14 && brew services start postgresql@14`
- Ubuntu/Debian: `sudo apt update && sudo apt install postgresql postgresql-contrib && sudo systemctl start postgresql`
- Windows: Download from https://www.postgresql.org/download/windows/

**Verify PostgreSQL is running**:
```bash
pg_isready
```

**Expected**: `/tmp:5432 - accepting connections` or similar success message

### 1.3 Check pip

```bash
pip3 --version
```

**Expected**: pip 21.x or higher

**If not installed**:
```bash
python3 -m ensurepip --upgrade
```

---

## Step 2: Set Up Python Environment

### 2.1 Create Virtual Environment

```bash
python3 -m venv venv
```

### 2.2 Activate Virtual Environment

**macOS/Linux**:
```bash
source venv/bin/activate
```

**Windows**:
```bash
.\venv\Scripts\activate
```

**Verify activation**:
```bash
which python
```

**Expected**: Path should contain `venv/bin/python`

### 2.3 Install Dependencies

```bash
pip install -r requirements.txt
```

**Verify installation**:
```bash
pip list | grep -E "(fastapi|sqlalchemy|psycopg2)"
```

**Expected**: Should show fastapi, sqlalchemy, psycopg2-binary

---

## Step 3: Configure Environment Variables

### 3.1 Create .env File

```bash
cp .env.example .env
```

### 3.2 Determine Database Connection

**Option A: Using system username (macOS default)**

Check your PostgreSQL user:
```bash
psql -c "SELECT current_user;" postgres 2>/dev/null || psql -c "SELECT current_user;" -U $(whoami) postgres
```

If successful, update `.env`:
```
DATABASE_URL=postgresql://YOUR_USERNAME@localhost:5432/coach_vocabulary
```

Replace `YOUR_USERNAME` with your actual username (usually your system username on macOS).

**Option B: Using postgres user with password**

If you have a `postgres` user with password, keep the default:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/coach_vocabulary
```

### 3.3 Verify .env Content

```bash
cat .env
```

**Expected**: Should contain valid DATABASE_URL, HOST, PORT, DEBUG settings

---

## Step 4: Set Up Database

### 4.1 Create Database

**Using your username (macOS)**:
```bash
createdb coach_vocabulary
```

**Using postgres user**:
```bash
createdb -U postgres coach_vocabulary
```

**Verify database exists**:
```bash
psql -l | grep coach_vocabulary
```

**Expected**: Should show `coach_vocabulary` in the list

### 4.2 Run Database Migrations

```bash
alembic upgrade head
```

**Expected output**:
```
INFO  [alembic.runtime.migration] Running upgrade  -> a93f64b8188d, Initial tables: users, words, word_progress
```

**Verify tables exist**:
```bash
psql -d coach_vocabulary -c "\dt"
```

**Expected**: Should show tables: `users`, `words`, `word_progress`, `alembic_version`

---

## Step 5: Seed Data

### 5.1 Run Seed Script

The seed script processes `words.json`, copies images to `static/images/`, and imports words to the database.

```bash
python scripts/seed_words.py --direct
```

**Expected output**:
```
Processing words and images...
...
Processed 214 words
Images copied: 214
Importing directly to database...
Cleared existing words
Imported: 214, Skipped: 0
```

### 5.2 Verify Seed Data

```bash
psql -d coach_vocabulary -c "SELECT COUNT(*) FROM words;"
```

**Expected**: `count` should be `214`

---

## Step 6: Start Development Server

### 6.1 Start Server

```bash
uvicorn app.main:app --reload
```

**Expected output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### 6.2 Verify Server Health (in another terminal)

```bash
curl http://localhost:8000/health
```

**Expected**: `{"status":"healthy"}`

---

## Step 7: Final Verification

### 7.1 Test Login API

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test_user"}'
```

**Expected**: JSON response with `id`, `username`, `is_new_user`

### 7.2 Test Stats API

Using the `id` from the previous response:

```bash
curl http://localhost:8000/api/home/stats \
  -H "X-User-Id: <user-id-from-previous-response>"
```

**Expected**: JSON with `today_learned: 0`, `can_learn: true`, etc.

### 7.3 Access Swagger UI

Open browser: http://localhost:8000/docs

**Expected**: Interactive API documentation page

---

## Troubleshooting

### PostgreSQL Connection Refused

**Symptom**: `psql: error: connection refused`

**Solution**:
```bash
# macOS
brew services start postgresql@14

# Linux
sudo systemctl start postgresql
```

### Permission Denied on Database

**Symptom**: `FATAL: role "postgres" does not exist`

**Solution**: Use your system username instead:
```bash
# Check your username
whoami

# Update .env
DATABASE_URL=postgresql://YOUR_USERNAME@localhost:5432/coach_vocabulary
```

### Module Not Found Errors

**Symptom**: `ModuleNotFoundError: No module named 'xxx'`

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Port 8000 Already in Use

**Symptom**: `ERROR: [Errno 48] Address already in use`

**Solution**:
```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn app.main:app --reload --port 8001
```

### Database Migration Errors

**Symptom**: `alembic.util.exc.CommandError`

**Solution**:
```bash
# Check current migration status
alembic current

# If database is fresh, upgrade to head
alembic upgrade head

# If migration history is corrupted, stamp and upgrade
alembic stamp head
alembic upgrade head
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `source venv/bin/activate` | Activate virtual environment |
| `pip install -r requirements.txt` | Install dependencies |
| `alembic upgrade head` | Run database migrations |
| `python scripts/seed_words.py --direct` | Seed word data |
| `uvicorn app.main:app --reload` | Start dev server |
| `curl http://localhost:8000/health` | Health check |
| `curl http://localhost:8000/docs` | API documentation |

---

## Success Criteria

The setup is complete when:

1. `curl http://localhost:8000/health` returns `{"status":"healthy"}`
2. `psql -d coach_vocabulary -c "SELECT COUNT(*) FROM words;"` returns 214
3. Login API returns valid user data
4. Swagger UI loads at http://localhost:8000/docs

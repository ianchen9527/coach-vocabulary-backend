# AI Agent Setup Guide

This document provides step-by-step instructions for AI agents (Claude Code, Gemini CLI, etc.) to set up the Coach Vocabulary Backend development environment from scratch.

## Important Notes for AI Agents

1. **Execute commands sequentially** - Each step depends on the previous one
2. **Verify each step** - Use the verification commands to confirm success before proceeding
3. **Handle errors** - If a step fails, check the Troubleshooting section
4. **Platform detection** - Check `uname -s` to determine OS (Darwin=macOS, Linux=Linux)
5. **Working directory** - All commands assume you are in the repository root directory

---

## Step 0: Verify Working Directory

```bash
# Check current directory contains expected files
ls -la app/main.py requirements.txt alembic.ini
```

**Expected**: Files should exist. If not, navigate to the correct directory:
```bash
cd /path/to/coach-vocabulary-backend
```

---

## Step 1: Detect Platform and Check Prerequisites

### 1.1 Detect Operating System

```bash
uname -s
```

**Result interpretation**:
- `Darwin` → macOS
- `Linux` → Linux
- For Windows (PowerShell), this command won't work; use `$env:OS` instead

### 1.2 Check Python

```bash
python3 --version
```

**Expected**: Python 3.9.x or higher

**If command fails or version too old**:

For macOS:
```bash
# Check if Homebrew is installed
which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11
```

For Linux (Ubuntu/Debian):
```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip
```

### 1.3 Check PostgreSQL

```bash
which psql && psql --version
```

**Expected**: psql (PostgreSQL) 14.x or higher

**If not installed**:

For macOS:
```bash
brew install postgresql@14
brew services start postgresql@14
```

For Linux (Ubuntu/Debian):
```bash
sudo apt update && sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Verify PostgreSQL is running**:
```bash
pg_isready
```

**Expected**: Message containing `accepting connections`

### 1.4 Check pip

```bash
python3 -m pip --version
```

**If not available**:
```bash
python3 -m ensurepip --upgrade
```

---

## Step 2: Set Up Python Virtual Environment

### 2.1 Remove Existing venv (if corrupted)

```bash
# Only run if venv exists and is corrupted
[ -d "venv" ] && rm -rf venv
```

### 2.2 Create Virtual Environment

```bash
python3 -m venv venv
```

### 2.3 Activate Virtual Environment

For macOS/Linux:
```bash
source venv/bin/activate
```

**Verify activation**:
```bash
which python | grep -q "venv" && echo "OK: venv activated" || echo "ERROR: venv not activated"
```

### 2.4 Upgrade pip

```bash
pip install --upgrade pip
```

### 2.5 Install Dependencies

```bash
pip install -r requirements.txt
```

**Verify installation**:
```bash
python -c "import fastapi, sqlalchemy, psycopg2; print('OK: All packages installed')"
```

---

## Step 3: Configure Environment Variables

### 3.1 Create .env File

```bash
# Create .env from example (won't overwrite if exists)
[ ! -f ".env" ] && cp .env.example .env
```

### 3.2 Detect PostgreSQL User and Update .env

**Step A: Try to detect the correct PostgreSQL user**

```bash
# Try connecting with current system user (common on macOS)
PGUSER=$(whoami)
if psql -U "$PGUSER" -c "SELECT 1;" postgres >/dev/null 2>&1; then
    echo "OK: PostgreSQL user is $PGUSER"
else
    # Try postgres user
    PGUSER="postgres"
    if psql -U "$PGUSER" -c "SELECT 1;" postgres >/dev/null 2>&1; then
        echo "OK: PostgreSQL user is postgres"
    else
        echo "ERROR: Cannot connect to PostgreSQL"
        exit 1
    fi
fi
```

**Step B: Update .env with detected user**

```bash
# For macOS/Linux - update DATABASE_URL with detected user
PGUSER=$(whoami)
if psql -U "$PGUSER" -c "SELECT 1;" postgres >/dev/null 2>&1; then
    # Using system username (no password)
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql://${PGUSER}@localhost:5432/coach_vocabulary|" .env
else
    # Using postgres user with password (keep default)
    echo "Using default postgres user configuration"
fi
```

**Note for Linux**: If `sed -i.bak` fails, try `sed -i''` instead.

### 3.3 Verify .env Content

```bash
grep "DATABASE_URL" .env
```

**Expected**: Should show a valid PostgreSQL connection string

---

## Step 4: Set Up Database

### 4.1 Create Database

```bash
# Extract username from DATABASE_URL
DB_USER=$(grep DATABASE_URL .env | sed 's/.*:\/\/\([^:@]*\).*/\1/')

# Create database (ignore error if already exists)
createdb -U "$DB_USER" coach_vocabulary 2>/dev/null || echo "Database may already exist"
```

**Verify database exists**:
```bash
DB_USER=$(grep DATABASE_URL .env | sed 's/.*:\/\/\([^:@]*\).*/\1/')
psql -U "$DB_USER" -l | grep -q "coach_vocabulary" && echo "OK: Database exists" || echo "ERROR: Database not found"
```

### 4.2 Run Database Migrations

```bash
alembic upgrade head
```

**Expected output**: Message containing `Running upgrade`

**Verify tables exist**:
```bash
DB_USER=$(grep DATABASE_URL .env | sed 's/.*:\/\/\([^:@]*\).*/\1/')
psql -U "$DB_USER" -d coach_vocabulary -c "\dt" | grep -q "words" && echo "OK: Tables created" || echo "ERROR: Tables not found"
```

---

## Step 5: Seed Data

### 5.1 Run Seed Script

```bash
python scripts/seed_words.py --direct
```

**Expected output**: Should end with `Imported: 214, Skipped: 0`

### 5.2 Verify Seed Data

```bash
DB_USER=$(grep DATABASE_URL .env | sed 's/.*:\/\/\([^:@]*\).*/\1/')
WORD_COUNT=$(psql -U "$DB_USER" -d coach_vocabulary -t -c "SELECT COUNT(*) FROM words;")
[ "$WORD_COUNT" -ge 200 ] && echo "OK: $WORD_COUNT words imported" || echo "ERROR: Only $WORD_COUNT words found"
```

---

## Step 6: Start Development Server

### 6.1 Start Server in Background

```bash
# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start server in background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &

# Wait for server to start
sleep 3
```

### 6.2 Verify Server is Running

```bash
curl -s http://localhost:8000/health
```

**Expected**: `{"status":"healthy"}`

**If server not responding, check logs**:
```bash
cat /tmp/uvicorn.log
```

---

## Step 7: Final Verification

### 7.1 Test Complete Flow

```bash
# Test login and get user ID
USER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"setup_test_user"}')

echo "Login response: $USER_RESPONSE"

# Extract user ID using Python (more reliable than grep/sed for JSON)
USER_ID=$(echo "$USER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "User ID: $USER_ID"

# Test stats endpoint
STATS_RESPONSE=$(curl -s http://localhost:8000/api/home/stats \
  -H "X-User-Id: $USER_ID")

echo "Stats response: $STATS_RESPONSE"

# Verify can_learn is true
echo "$STATS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('OK: Setup complete!' if data.get('can_learn') else 'ERROR: Unexpected state')"
```

### 7.2 Summary Check

```bash
echo "=== Setup Verification ==="
curl -s http://localhost:8000/health | grep -q "healthy" && echo "✓ Server running" || echo "✗ Server not running"
DB_USER=$(grep DATABASE_URL .env | sed 's/.*:\/\/\([^:@]*\).*/\1/')
psql -U "$DB_USER" -d coach_vocabulary -t -c "SELECT COUNT(*) FROM words;" | grep -q "214" && echo "✓ Words seeded (214)" || echo "✗ Words not seeded"
echo "=== Setup Complete ==="
```

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

### Role Does Not Exist

**Symptom**: `FATAL: role "postgres" does not exist`

**Solution**:
```bash
# Use your system username instead
PGUSER=$(whoami)
sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql://${PGUSER}@localhost:5432/coach_vocabulary|" .env
```

### Database Already Exists

**Symptom**: `ERROR: database "coach_vocabulary" already exists`

**Solution**: This is OK, continue to next step.

### Module Not Found

**Symptom**: `ModuleNotFoundError: No module named 'xxx'`

**Solution**:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Port 8000 Already in Use

**Symptom**: `ERROR: [Errno 48] Address already in use`

**Solution**:
```bash
lsof -ti:8000 | xargs kill -9
uvicorn app.main:app --reload
```

### Migration Errors

**Symptom**: `alembic.util.exc.CommandError`

**Solution**:
```bash
# Check status
alembic current

# If corrupted, reset and retry
alembic stamp head
alembic upgrade head
```

### Seed Script Fails

**Symptom**: `FileNotFoundError` or import errors

**Solution**:
```bash
# Ensure you're in repo root with venv activated
pwd  # Should be coach-vocabulary-backend
source venv/bin/activate
python scripts/seed_words.py --direct
```

---

## Quick Reference

| Step | Command | Purpose |
|------|---------|---------|
| Activate venv | `source venv/bin/activate` | Enter virtual environment |
| Install deps | `pip install -r requirements.txt` | Install Python packages |
| Run migrations | `alembic upgrade head` | Create database tables |
| Seed data | `python scripts/seed_words.py --direct` | Import 214 words |
| Start server | `uvicorn app.main:app --reload` | Start dev server |
| Health check | `curl http://localhost:8000/health` | Verify server running |
| API docs | Open http://localhost:8000/docs | Swagger UI |

---

## Success Criteria

Setup is complete when ALL of the following pass:

```bash
# 1. Server health check
curl -s http://localhost:8000/health | grep -q "healthy" && echo "PASS" || echo "FAIL"

# 2. Database has words
DB_USER=$(grep DATABASE_URL .env | sed 's/.*:\/\/\([^:@]*\).*/\1/')
[ $(psql -U "$DB_USER" -d coach_vocabulary -t -c "SELECT COUNT(*) FROM words;") -ge 200 ] && echo "PASS" || echo "FAIL"

# 3. Login API works
curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"test"}' | grep -q "id" && echo "PASS" || echo "FAIL"
```

All three checks should output `PASS`.

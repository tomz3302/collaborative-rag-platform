# Database Migration to Supabase (PostgreSQL)

## ✅ Migration Complete

This project has been migrated from local MySQL to Supabase PostgreSQL.

## Database Architecture

### Primary Database: **Supabase PostgreSQL**
All production tables and queries now use PostgreSQL hosted on Supabase.

### Files Updated:

#### ✅ Core Database Files
- **`database_manager.py`** - All CRUD operations now use PostgreSQL/psycopg2
- **`db.py`** - Authentication tables use PostgreSQL with asyncpg
- **`supabase_sql_setup.py`** - Creates ALL tables (users, spaces, documents, threads, messages, context_anchors)

#### ✅ Configuration
- **`.env`** - Contains both MySQL (legacy) and PostgreSQL (active) credentials
- All active code reads from `POSTGRES_*` variables

#### ⚠️ Deprecated Files
- **`database_setup.py`** - MySQL setup script (DEPRECATED, kept for reference only)

## Database Credentials

Located in `.env`:
```
POSTGRES_HOST=aws-1-eu-central-1.pooler.supabase.com
POSTGRES_PORT=6543
POSTGRES_USER=postgres.rrcvxnrtjejetktzkesz
POSTGRES_PASSWORD=<your_password>
POSTGRES_DATABASE=postgres
```

## Database Schema

### Tables Created by `supabase_sql_setup.py`:

1. **`user`** - Authentication (email, password, verification status)
2. **`spaces`** - Workspaces for organizing content
3. **`documents`** - PDF files and their metadata
4. **`threads`** - Conversation threads
5. **`messages`** - Chat messages with branching support
6. **`context_anchors`** - Links threads to documents

## Setup Instructions

### First Time Setup:

1. Install PostgreSQL dependencies:
```bash
pip install psycopg2-binary asyncpg
```

2. Configure `.env` with your Supabase credentials

3. Create all tables:
```bash
python supabase_sql_setup.py
```

4. (Optional) Create auth tables via SQLAlchemy:
```bash
python create_auth_tables.py
```

## Key Differences: MySQL → PostgreSQL

| Feature | MySQL | PostgreSQL (Supabase) |
|---------|-------|----------------------|
| **Auto Increment** | `AUTO_INCREMENT` | `SERIAL` |
| **Get Last ID** | `cursor.lastrowid` | `RETURNING id` |
| **Upsert** | `INSERT IGNORE` | `INSERT ... ON CONFLICT` |
| **Dictionary Cursor** | `cursor(dictionary=True)` | `cursor(cursor_factory=RealDictCursor)` |
| **Driver** | `mysql.connector` | `psycopg2` / `asyncpg` |

## Connection Pools

- **Sync Operations** (`database_manager.py`): Uses `psycopg2.pool.SimpleConnectionPool`
- **Async Operations** (`db.py`): Uses SQLAlchemy with `asyncpg`

## Verification

All database operations have been tested and verified:
- ✅ User registration and authentication
- ✅ Space creation and retrieval
- ✅ Document upload and indexing
- ✅ Thread and message management
- ✅ Branch creation and navigation
- ✅ Context anchoring

## Rollback (Emergency Only)

If you need to rollback to MySQL:
1. Update `database_manager.py` imports back to `mysql.connector`
2. Change `.env` references from `POSTGRES_*` to `MYSQL_*`
3. Update `db.py` connection string to use `mysql+aiomysql`
4. Run `database_setup.py` to recreate MySQL tables

**Note: This is not recommended. All future development should use Supabase.**

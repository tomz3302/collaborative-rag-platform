import psycopg2
from psycopg2 import sql, extras
import logging
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Supabase_Setup")

# -------------------------------------------------------------------------
# DATABASE CONFIGURATION (Supabase/PostgreSQL)
# Loaded from .env file
# -------------------------------------------------------------------------
DB_HOST = os.getenv('POSTGRES_HOST')
DB_NAME = os.getenv('POSTGRES_DATABASE', 'postgres')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_PORT = int(os.getenv('POSTGRES_PORT', 6543))

TABLES = {}

# 0. USER TABLE (for FastAPI-Users authentication)
TABLES['user'] = (
    """
    CREATE TABLE IF NOT EXISTS "user" (
        id SERIAL PRIMARY KEY,
        email VARCHAR(320) NOT NULL UNIQUE,
        hashed_password VARCHAR(1024) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
        is_verified BOOLEAN NOT NULL DEFAULT FALSE,
        full_name VARCHAR(100)
    )
    """
)

# 1. SPACES TABLE
# MySQL AUTO_INCREMENT -> Postgres SERIAL
TABLES['spaces'] = (
    """
    CREATE TABLE IF NOT EXISTS spaces (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """
)

# 2. DOCUMENTS TABLE
TABLES['documents'] = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        space_id INT NOT NULL,
        filename VARCHAR(255) NOT NULL,
        file_type VARCHAR(50),
        file_url TEXT, 
        uploaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
    )
    """
)

# 3. THREADS TABLE
TABLES['threads'] = (
    """
    CREATE TABLE IF NOT EXISTS threads (
        id SERIAL PRIMARY KEY,
        space_id INT NOT NULL,
        title VARCHAR(255),
        creator_user_id INT, 
        is_public BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
    )
    """
)

# 4. CONTEXT ANCHORS TABLE
# UNIQUE KEY (col1, col2) -> UNIQUE (col1, col2)
TABLES['context_anchors'] = (
    """
    CREATE TABLE IF NOT EXISTS context_anchors (
        id SERIAL PRIMARY KEY,
        thread_id INT NOT NULL,
        document_id INT NOT NULL,
        page_number INT DEFAULT 1, 
        UNIQUE (thread_id, document_id, page_number),
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    )
    """
)

# 5. MESSAGES TABLE
# MySQL CHECK syntax is compatible with Postgres
TABLES['messages'] = (
    """
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        thread_id INT NOT NULL,
        user_id INT NOT NULL, 
        role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL, 
        path TEXT NOT NULL,
        parent_message_id INT,
        branch_id INT DEFAULT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL
    )
    """
)

# 6. INDEXES
# Note: Postgres doesn't use path(20) prefix indexing; it's handled automatically or via B-Tree.
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_messages_path ON messages (path);",
    "CREATE INDEX IF NOT EXISTS idx_messages_branching ON messages (thread_id, branch_id);",
    "CREATE INDEX IF NOT EXISTS idx_anchors_doc_page ON context_anchors (document_id, page_number);",
    "CREATE INDEX IF NOT EXISTS idx_documents_space ON documents (space_id);",
    "CREATE INDEX IF NOT EXISTS idx_threads_space ON threads (space_id);"
]

def create_tables():
    conn = None
    try:
        logger.info(f"Connecting to Supabase Postgres at {DB_HOST}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        cur = conn.cursor()

        # 1. Create Tables
        for name, ddl in TABLES.items():
            logger.info(f"Processing table {name}...")
            cur.execute(ddl)

        # 2. Create Indexes
        logger.info("Creating indexes...")
        for idx_ddl in INDEXES:
            cur.execute(idx_ddl)

        conn.commit()
        cur.close()
        logger.info("✅ Success: Supabase schema updated successfully.")

    except Exception as err:
        logger.error(f"❌ Database Error: {err}")
        sys.exit(1)
    finally:
        if conn is not None:
            conn.close()
            logger.info("Database connection closed.")

if __name__ == '__main__':
    create_tables()
import mysql.connector
from mysql.connector import errorcode
import logging
import sys
import os
from dotenv import load_dotenv

# ===========================================================================
# ⚠️ DEPRECATED: This file is for LOCAL MYSQL SETUP ONLY
# ⚠️ The project now uses SUPABASE (PostgreSQL)
# ⚠️ Use supabase_sql_setup.py instead for production setup
# ===========================================================================

# Load environment variables
load_dotenv()

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Setup")

# -------------------------------------------------------------------------
# DATABASE CONFIGURATION (MySQL - LOCAL ONLY)
# Loaded from .env file
# -------------------------------------------------------------------------
DB_HOST = os.getenv('MYSQL_HOST', 'localhost')
DB_NAME = os.getenv('MYSQL_DATABASE', 'rag')
DB_USER = os.getenv('MYSQL_USER', 'root')
DB_PASS = os.getenv('MYSQL_PASSWORD', '')
DB_PORT = int(os.getenv('MYSQL_PORT', 3306))

TABLES = {}

# 1. SPACES TABLE (New)
# This is the top-level container. Documents and Threads belong here.
TABLES['spaces'] = (
    """
    CREATE TABLE IF NOT EXISTS spaces (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
    """
)

# 2. DOCUMENTS TABLE
TABLES['documents'] = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        space_id INT NOT NULL,
        filename VARCHAR(255) NOT NULL,
        file_type VARCHAR(50),
        file_url TEXT, 

        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """
)

# 3. THREADS TABLE (Updated)
# Added 'space_id'. A thread lives inside a space.
# While 'context_anchors' links a thread to a specific document,
# the thread itself belongs to the Space context.
TABLES['threads'] = (
    """
    CREATE TABLE IF NOT EXISTS threads (
        id INT AUTO_INCREMENT PRIMARY KEY,
        space_id INT NOT NULL,
        title VARCHAR(255),
        creator_user_id INT, 
        is_public BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """
)

# 4. CONTEXT ANCHORS TABLE
# Connects a Thread to a Document
# NOTE: Application logic should ensure the Thread and Document belong to the same Space.
TABLES['context_anchors'] = (
    """
    CREATE TABLE IF NOT EXISTS context_anchors (
        id INT AUTO_INCREMENT PRIMARY KEY,
        thread_id INT NOT NULL,
        document_id INT NOT NULL,
        page_number INT DEFAULT 1, 

        UNIQUE KEY unique_anchor (thread_id, document_id, page_number),

        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """
)

# 5. MESSAGES TABLE
TABLES['messages'] = (
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        thread_id INT NOT NULL,
        user_id INT NOT NULL, 
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL, 
        path TEXT NOT NULL,
        parent_message_id INT,
        branch_id INT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL,

        CHECK (role IN ('user', 'assistant', 'system'))
    ) ENGINE=InnoDB
    """
)

# 6. INDEXES
INDEXES = [
    # Fast Path Search
    "CREATE INDEX idx_messages_path ON messages (path(20));",

    # Fast Branch Lookup
    "CREATE INDEX idx_messages_branching ON messages (thread_id, branch_id);",

    # Fast Document/Page Lookup
    "CREATE INDEX idx_anchors_doc_page ON context_anchors (document_id, page_number);",

    # NEW: Fast Space lookups
    "CREATE INDEX idx_documents_space ON documents (space_id);",
    "CREATE INDEX idx_threads_space ON threads (space_id);"
]


def create_tables():
    conn = None
    cur = None
    try:
        logger.info(f"Connecting to MySQL server at {DB_HOST}:{DB_PORT}...")
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            database=DB_NAME
        )
        cur = conn.cursor()

        # 1. Create Tables
        logger.info(f"Creating tables in database '{DB_NAME}'...")
        # Iterating directly isn't guaranteed order in older Python versions,
        # but in modern Python it inserts order. To be safe, we rely on the define order above.
        for name, ddl in TABLES.items():
            try:
                logger.info(f"Processing table {name}...")
                cur.execute(ddl)
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    logger.warning(f"Table {name} already exists. Skipping.")
                else:
                    logger.error(f"Error creating table {name}: {err}")
                    # If a critical table fails, we might want to stop
                    if name in ['spaces', 'documents', 'threads']:
                        raise err

        # 2. Create Indexes
        logger.info("Creating indexes...")
        for idx_ddl in INDEXES:
            try:
                cur.execute(idx_ddl)
            except mysql.connector.Error as err:
                # Error code 1061 is "Duplicate key/index name"
                if err.errno == 1061:
                    logger.warning(f"Index already exists, skipping...")
                else:
                    logger.error(f"Error creating index: {err}")

        # 3. Commit and Success
        conn.commit()
        logger.info("✅ Success: Database schema updated successfully.")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logger.error("❌ Connection Error: Invalid username or password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            logger.error(f"❌ Database Error: Database '{DB_NAME}' does not exist.")
        else:
            logger.error(f"❌ Database Error: {err}")
        sys.exit(1)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
            logger.info("Database connection closed.")


if __name__ == '__main__':
    create_tables()
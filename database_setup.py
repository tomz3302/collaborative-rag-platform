import mysql.connector
from mysql.connector import errorcode
import logging
import sys

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB_Setup")

# -------------------------------------------------------------------------
# DATABASE CONFIGURATION (MySQL)
# Update these values to match your local MySQL credentials
# -------------------------------------------------------------------------
DB_HOST = "localhost"
DB_NAME = "rag"
DB_USER = "root"
DB_PASS = ""
DB_PORT = 3306

TABLES = {}

# 1. DOCUMENTS TABLE (Unchanged)
TABLES['documents'] = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        file_type VARCHAR(50),
        file_data LONGBLOB, 
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
    """
)

# 2. THREADS TABLE (Unchanged)
TABLES['threads'] = (
    """
    CREATE TABLE IF NOT EXISTS threads (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255),
        creator_user_id INT, 
        is_public BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
    """
)

# 3. CONTEXT ANCHORS TABLE (Updated)
# - Added 'page_number' to support split-screen logic per page.
# - Updated UNIQUE constraint to include page_number.
TABLES['context_anchors'] = (
    """
    CREATE TABLE IF NOT EXISTS context_anchors (
        id INT AUTO_INCREMENT PRIMARY KEY,
        thread_id INT NOT NULL,
        document_id INT NOT NULL,

        -- NEW: Defaults to 1 if not specified
        page_number INT DEFAULT 1, 

        -- UPDATED: One thread per page per document
        UNIQUE KEY unique_anchor (thread_id, document_id, page_number),

        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """
)

# 4. MESSAGES TABLE (The "Hybrid" Logic)
# - Stores 'path' as TEXT for deep nesting.
# - Stores 'parent_message_id' for future optimization.
# - Stores 'branch_id' for easy Fork management.
TABLES['messages'] = (
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        thread_id INT NOT NULL,
        user_id INT NOT NULL, 
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL, 

        -- MATERIALIZED PATH: Changed to TEXT to support 6000+ levels of nesting.
        -- We will index the first 20 chars for speed.
        path TEXT NOT NULL,

        -- PARENT ID: Essential for Data Integrity and future Recursive SQL support.
        parent_message_id INT,

        -- BRANCH ID: 
        -- NULL = Main Thread (The "Canon" conversation)
        -- INT = ID of the message where the fork started.
        branch_id INT DEFAULT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL,

        CHECK (role IN ('user', 'assistant', 'system'))
    ) ENGINE=InnoDB
    """
)

# 5. INDEXES (Optimized for the new columns)
INDEXES = [
    # 1. Fast Path Search: Only indexes the first 20 chars of the TEXT column
    "CREATE INDEX idx_messages_path ON messages (path(20));",

    # 2. Fast Branch Lookup: Instantly find 'Main Thread' (NULL) or 'Fork X'
    "CREATE INDEX idx_messages_branching ON messages (thread_id, branch_id);",

    # 3. Fast Document/Page Lookup
    "CREATE INDEX idx_anchors_doc_page ON context_anchors (document_id, page_number);"
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
        for name, ddl in TABLES.items():
            try:
                logger.info(f"Processing table {name}...")
                cur.execute(ddl)
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    logger.warning(f"Table {name} already exists. Skipping.")
                else:
                    logger.error(f"Error creating table {name}: {err}")

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
            logger.error(f"❌ Unhandled Database Error: {err}")
        sys.exit(1)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
            logger.info("Database connection closed.")


if __name__ == '__main__':
    create_tables()
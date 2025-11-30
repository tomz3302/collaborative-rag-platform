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
DB_NAME = "rag"  # Using the 'rag' database you already created
DB_USER = "root"  # Change this to your MySQL username
DB_PASS = ""  # Change this to your MySQL password
DB_PORT = 3306  # Default MySQL port

# --- SQL Commands adapted for MySQL ---
# NOTE: InnoDB is assumed for transactionality and foreign keys.
# - SERIAL PRIMARY KEY is replaced with INT AUTO_INCREMENT PRIMARY KEY.
# - BYTEA is replaced with LONGBLOB (for large binary files like PDFs).
# - TEXT is used for message content.
# - BOOLEAN is handled by TINYINT(1) but declared as BOOLEAN for compatibility.
# - IF NOT EXISTS and foreign key syntax are adjusted.
# -------------------------------------------------------------------------
TABLES = {}

# 1. DOCUMENTS TABLE
# Stores the actual file binaries (PDF/PPTX) using LONGBLOB.
TABLES['documents'] = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        file_type VARCHAR(50),

        -- MySQL equivalent of BYTEA for large binary files
        file_data LONGBLOB, 

        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
    """
)

# 2. THREADS TABLE
# The container for a specific conversation.
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

# 3. CONTEXT ANCHORS TABLE (The "Split Screen" Logic)
# Links a Thread to a specific Document.
TABLES['context_anchors'] = (
    """
    CREATE TABLE IF NOT EXISTS context_anchors (
        id INT AUTO_INCREMENT PRIMARY KEY,
        thread_id INT NOT NULL,
        document_id INT NOT NULL,
        UNIQUE KEY unique_anchor (thread_id, document_id),

        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """
)

# 4. MESSAGES TABLE (The "Reddit" Logic - Materialized Path)
# Stores the actual chat content.
TABLES['messages'] = (
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        thread_id INT NOT NULL,

        -- 0 could represent the AI, >0 represents students
        user_id INT NOT NULL, 

        -- explicit role defines who is talking
        role VARCHAR(20) NOT NULL,

        -- Use TEXT for potentially long chat messages/responses
        content TEXT NOT NULL, 

        -- MATERIALIZED PATH PATTERN: e.g., '1/2/5/'
        path VARCHAR(255) NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,

        -- Add a constraint to ensure role is one of the valid values
        CHECK (role IN ('user', 'assistant', 'system'))
    ) ENGINE=InnoDB
    """
)

# 5. INDEXES (Separated from CREATE TABLE for cleaner MySQL compatibility)
INDEXES = [
    # Index for fast search by path prefix (crucial for nested comments)
    "CREATE INDEX idx_messages_path ON messages (path(10));",

    # Index for fast lookup when a document is opened
    "CREATE INDEX idx_anchors_doc ON context_anchors (document_id);"
]


def create_tables():
    conn = None
    cur = None
    try:
        # Establish connection without specifying the database name first
        logger.info(f"Connecting to MySQL server at {DB_HOST}:{DB_PORT}...")
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            database=DB_NAME  # Connect directly to the 'rag' database
        )
        cur = conn.cursor()

        # 1. Create Tables
        logger.info(f"Creating tables in database '{DB_NAME}'...")
        for name, ddl in TABLES.items():
            try:
                logger.info(f"Creating table {name}...")
                cur.execute(ddl)
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    logger.warning(f"Table {name} already exists, skipping.")
                else:
                    logger.error(f"Error creating table {name}: {err}")
                    # Don't exit, try to continue with next table

        # 2. Create Indexes
        logger.info("Creating non-unique indexes...")
        for idx_ddl in INDEXES:
            # We use a non-standard method to check if index exists because
            # MySQL's CREATE INDEX IF NOT EXISTS is sometimes unreliable or not supported.
            # Executing it directly is often fine, as it gives a warning if it exists.
            try:
                # We only index the first 10 chars of the VARCHAR(255) 'path'
                # for performance, which is sufficient for most hierarchies.
                cur.execute(idx_ddl)
            except mysql.connector.Error as err:
                # Error code 1061 is "Duplicate key/index name"
                if err.errno == 1061:
                    logger.warning(f"Index already exists, skipping: {idx_ddl[:40]}...")
                else:
                    logger.error(f"Error creating index: {err}")

        # 3. Commit and Success
        conn.commit()
        logger.info("✅ Success: All tables and indexes created/verified successfully.")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logger.error("❌ Connection Error: Invalid username or password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            logger.error(f"❌ Database Error: Database '{DB_NAME}' does not exist.")
        else:
            logger.error(f"❌ Unhandled Database Error: {err}")
        sys.exit(1)  # Exit if connection fails
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()
            logger.info("Database connection closed.")


if __name__ == '__main__':
    create_tables()
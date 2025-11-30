import mysql.connector
from mysql.connector import errorcode
import logging

# Configuration (Same as your setup)
DB_CONFIG = {
    'user': 'root',
    'password': '',  # Update this
    'host': 'localhost',
    'port': 3306,
    'database': 'rag'
}


class DBManager:
    def __init__(self):
        self.config = DB_CONFIG

    def get_connection(self):
        return mysql.connector.connect(**self.config)


    def create_thread(self, title: str, creator_id: int = 1) -> int:
        """Starts a new conversation thread."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "INSERT INTO threads (title, creator_user_id) VALUES (%s, %s)"
            cursor.execute(query, (title, creator_id))
            conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

    def add_message(self, thread_id: int, user_id: int, role: str, content: str, parent_message_id: int = None) -> int:
        """
        Adds a message and handles the Materialized Path logic (e.g., '1/5/12/')
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 1. Insert the message with a placeholder path first
            insert_query = """
                INSERT INTO messages (thread_id, user_id, role, content, path) 
                VALUES (%s, %s, %s, %s, '')
            """
            cursor.execute(insert_query, (thread_id, user_id, role, content))
            new_msg_id = cursor.lastrowid

            # 2. Calculate the Path
            if parent_message_id is None:
                # Root message path: "ID/"
                new_path = f"{new_msg_id}/"
            else:
                # Fetch parent's path
                cursor.execute("SELECT path FROM messages WHERE id = %s", (parent_message_id,))
                result = cursor.fetchone()
                if result:
                    parent_path = result[0]
                    new_path = f"{parent_path}{new_msg_id}/"
                else:
                    # Fallback if parent not found (shouldn't happen)
                    new_path = f"{new_msg_id}/"

            # 3. Update the message with the correct path
            update_query = "UPDATE messages SET path = %s WHERE id = %s"
            cursor.execute(update_query, (new_path, new_msg_id))
            conn.commit()

            return new_msg_id
        finally:
            cursor.close()
            conn.close()

    def link_thread_to_doc(self, thread_id, doc_id, page_num):
        """Creates the Context Anchor (The Split Screen Logic)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = """
                INSERT IGNORE INTO context_anchors (thread_id, document_id, page_number)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (thread_id, doc_id, page_num))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def get_last_message_id(self, thread_id: int):
        """Finds the ID of the most recent message in a thread."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Get the message with the highest ID for this thread
            query = "SELECT id FROM messages WHERE thread_id = %s ORDER BY id DESC LIMIT 1"
            cursor.execute(query, (thread_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            cursor.close()
            conn.close()

    def get_document_id_by_filename(self, filename: str):
        """Finds the ID of a document based on its filename."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # We use LIKE in case path differences exist, or exact match
            query = "SELECT id FROM documents WHERE filename LIKE %s LIMIT 1"
            # The filename in DB usually includes 'temp_', so we might need fuzzy match
            # For now, let's try exact match based on your upload logic
            cursor.execute(query, (f"%{filename}",))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            cursor.close()
            conn.close()
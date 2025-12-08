import mysql.connector
import logging
from typing import List, Dict, Optional

# Configuration
DB_CONFIG = {
    'user': 'root',
    'password': '',  # Update this
    'host': 'localhost',
    'port': 3306,
    'database': 'rag'
}

logger = logging.getLogger("DB_Manager")


class DBManager:
    def __init__(self):
        self.config = DB_CONFIG

    def get_connection(self):
        return mysql.connector.connect(**self.config)

    # --- THREADS ---
    def create_thread(self, space_id: int, title: str, creator_id: int = 1) -> int:
        """
        Starts a new conversation thread inside a specific Space.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Added space_id to the INSERT statement
            query = "INSERT INTO threads (space_id, title, creator_user_id) VALUES (%s, %s, %s)"
            cursor.execute(query, (space_id, title, creator_id))
            conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

    def get_threads_for_space(self, space_id: int) -> List[Dict]:
        """(New) Gets all conversations in a specific workspace."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT id, title, creator_user_id, created_at
                FROM threads
                WHERE space_id = %s
                ORDER BY created_at DESC
            """
            cursor.execute(query, (space_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_last_message_id(self, thread_id: int) -> Optional[int]:
        """Gets the very last message added to a thread (for simple continuation)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # We order by ID desc to get the chronological last message
            query = "SELECT id FROM messages WHERE thread_id = %s ORDER BY id DESC LIMIT 1"
            cursor.execute(query, (thread_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            cursor.close()
            conn.close()

    # --- MESSAGES & FORKING LOGIC ---
    def add_message(self, thread_id: int, user_id: int, role: str, content: str,
                    parent_message_id: int = None, is_fork_start: bool = False) -> int:
        """
        Adds a message and handles Path + Branch logic.
        :param is_fork_start: If True, this message starts a new Branch (Branch ID = New Message ID).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 1. Determine Parent Info (Path and Branch ID)
            parent_path = ""
            inherited_branch_id = None  # Default for Main Thread (NULL)

            if parent_message_id:
                cursor.execute("SELECT path, branch_id FROM messages WHERE id = %s", (parent_message_id,))
                result = cursor.fetchone()
                if result:
                    parent_path = result[0]
                    inherited_branch_id = result[1]

            # 2. Insert the message (with temp path)
            # We insert 'branch_id' as NULL initially if it's a new fork, we'll update it momentarily.
            insert_query = """
                INSERT INTO messages (thread_id, user_id, role, content, path, parent_message_id, branch_id) 
                VALUES (%s, %s, %s, %s, '', %s, %s)
            """
            # If it's a normal reply, we inherit. If it's a fork start, we set NULL (to fill later)
            initial_branch_val = None if is_fork_start else inherited_branch_id

            cursor.execute(insert_query, (thread_id, user_id, role, content, parent_message_id, initial_branch_val))
            new_msg_id = cursor.lastrowid

            # 3. Calculate Final Path & Branch ID
            new_path = f"{parent_path}{new_msg_id}/" if parent_message_id else f"{new_msg_id}/"

            # Logic: If this is a fork start, the Branch ID is the Message's OWN ID.
            final_branch_id = new_msg_id if is_fork_start else initial_branch_val

            # 4. Update the record
            update_query = "UPDATE messages SET path = %s, branch_id = %s WHERE id = %s"
            cursor.execute(update_query, (new_path, final_branch_id, new_msg_id))
            conn.commit()

            return new_msg_id
        finally:
            cursor.close()
            conn.close()

    # --- CONTEXT RETRIEVAL (MEMORY) ---
    def get_context_messages(self, parent_message_id: int) -> List[Dict]:
        """
        Retrieves the conversation history for the AI.
        Uses the Materialized Path to instantly fetch ancestors.
        """
        if not parent_message_id:
            return []

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)  # Return dicts for easy parsing
        try:
            # 1. Get the path of the parent message
            cursor.execute("SELECT path FROM messages WHERE id = %s", (parent_message_id,))
            result = cursor.fetchone()

            if not result:
                return []

            path_string = result['path']  # e.g., "1/5/20/"

            # 2. Convert path to list of IDs
            # Remove trailing slash and split
            ancestor_ids = [int(x) for x in path_string.strip('/').split('/') if x.isdigit()]

            if not ancestor_ids:
                return []

            # 3. Fetch all messages in that chain
            # Dynamically create placeholder string: %s, %s, %s...
            format_strings = ','.join(['%s'] * len(ancestor_ids))
            query = f"""
                SELECT role, content 
                FROM messages 
                WHERE id IN ({format_strings}) 
                ORDER BY id ASC
            """
            cursor.execute(query, tuple(ancestor_ids))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_documents_for_space(self, space_id: int) -> List[Dict]:
        """
        (Edited from get_all_documents)
        Now returns documents only for a specific Space.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT id, filename, file_type, file_url, uploaded_at
                FROM documents
                WHERE space_id = %s
                ORDER BY uploaded_at DESC
            """
            cursor.execute(query, (space_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_document_id_by_filename(self, space_id: int, filename: str) -> Optional[int]:
        """
        (Edited) Finds a document ID.
        Now scoped to 'space_id' so you can have 'Invoice.pdf' in two different spaces.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT id FROM documents WHERE space_id = %s AND filename LIKE %s LIMIT 1"
            cursor.execute(query, (space_id, f"%{filename}"))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            cursor.close()
            conn.close()

    def add_document(self, space_id: int, filename: str, file_type: str, file_url: str) -> int:
        """
        (New) Registers a document after uploading to Cloud Storage (Koofr/R2).
        Stores the 'file_url' (path) instead of the actual file bytes.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = """
                INSERT INTO documents (space_id, filename, file_type, file_url) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (space_id, filename, file_type, file_url))
            conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            conn.close()


    def link_thread_to_doc(self, thread_id, doc_id, page_num=1):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # We use INSERT IGNORE to avoid crashing if link already exists
            query = """
                INSERT IGNORE INTO context_anchors (thread_id, document_id, page_number)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (thread_id, doc_id, page_num))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def get_thread_with_messages(self, thread_id: int) -> Optional[Dict]:
        """
        Retrieves a thread and all its messages.
        Returns a dictionary with thread info and list of messages.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Get thread info
            thread_query = """
                SELECT t.id, t.title, t.creator_user_id, t.is_public, t.created_at,
                       ca.page_number
                FROM threads t
                LEFT JOIN context_anchors ca ON t.id = ca.thread_id
                WHERE t.id = %s
                LIMIT 1
            """
            cursor.execute(thread_query, (thread_id,))
            thread = cursor.fetchone()

            if not thread:
                return None

            # Get all messages for this thread
            messages_query = """
                SELECT id, user_id, role, content, path, parent_message_id, 
                       branch_id, created_at
                FROM messages
                WHERE thread_id = %s
                ORDER BY id ASC
            """
            cursor.execute(messages_query, (thread_id,))
            messages = cursor.fetchall()

            # Combine thread info with messages
            thread['messages'] = messages
            return thread
        finally:
            cursor.close()
            conn.close()

    def get_threads_for_document(self, document_id: int) -> List[Dict]:
        """
        Retrieves all threads associated with a specific document.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT t.id, t.title, t.creator_user_id, t.created_at,
                       ca.page_number
                FROM threads t
                INNER JOIN context_anchors ca ON t.id = ca.thread_id
                WHERE ca.document_id = %s
                ORDER BY ca.page_number ASC, t.created_at DESC
            """
            cursor.execute(query, (document_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def create_space(self, name: str, description: str = None) -> int:
        """Creates a new workspace (e.g., 'Legal Team', 'Project Alpha')."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "INSERT INTO spaces (name, description) VALUES (%s, %s)"
            cursor.execute(query, (name, description))
            conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            conn.close()

    def get_spaces(self) -> List[Dict]:
        """Lists all available workspaces."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM spaces ORDER BY created_at DESC")
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()




import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration for Supabase (PostgreSQL)
DB_CONFIG = {
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('POSTGRES_HOST'),
    'port': int(os.getenv('POSTGRES_PORT', 6543)),
    'database': os.getenv('POSTGRES_DATABASE', 'postgres')
}

logger = logging.getLogger("DB_Manager")


class DBManager:
    def __init__(self):
        self.pool = psycopg2.pool.SimpleConnectionPool(1, 20, **DB_CONFIG)

    def get_connection(self):
        return self.pool.getconn()

    # --- THREADS ---
    def create_thread(self, space_id: int, title: str, creator_id: int) -> int:
        """
        Starts a new conversation thread inside a specific Space.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # PostgreSQL uses RETURNING to get the new ID
            query = "INSERT INTO threads (space_id, title, creator_user_id) VALUES (%s, %s, %s) RETURNING id"
            cursor.execute(query, (space_id, title, creator_id))
            thread_id = cursor.fetchone()[0]
            conn.commit()
            return thread_id
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_threads_for_space(self, space_id: int) -> List[Dict]:
        """(New) Gets all conversations in a specific workspace."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
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
            self.pool.putconn(conn)

    def get_last_message_id(self, thread_id: int, branch_id: int = None) -> Optional[int]:
        """
        Gets the last message in a thread, respecting branch context.
        - branch_id=None: returns last MAIN THREAD message (branch_id IS NULL)
        - branch_id=X: returns last message in that specific branch
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if branch_id is not None:
                # Get last message in specific branch
                query = "SELECT id FROM messages WHERE thread_id = %s AND branch_id = %s ORDER BY id DESC LIMIT 1"
                cursor.execute(query, (thread_id, branch_id))
            else:
                # Get last message in main thread only
                query = "SELECT id FROM messages WHERE thread_id = %s AND branch_id IS NULL ORDER BY id DESC LIMIT 1"
                cursor.execute(query, (thread_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            cursor.close()
            self.pool.putconn(conn)

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

            # PostgreSQL: Add RETURNING to get the new ID
            insert_query = """
                INSERT INTO messages (thread_id, user_id, role, content, path, parent_message_id, branch_id) 
                VALUES (%s, %s, %s, %s, '', %s, %s) RETURNING id
            """
            cursor.execute(insert_query, (thread_id, user_id, role, content, parent_message_id, initial_branch_val))
            new_msg_id = cursor.fetchone()[0]

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
            self.pool.putconn(conn)

    # --- CONTEXT RETRIEVAL (MEMORY) ---
    def get_context_messages(self, parent_message_id: int) -> List[Dict]:
        """
        Retrieves the conversation history for the AI.
        Uses the Materialized Path to instantly fetch ancestors.
        """
        if not parent_message_id:
            return []

        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)  # Return dicts for easy parsing
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
            all_messages = cursor.fetchall()
            
            # Return only the last 6 messages
            return all_messages[-6:] if len(all_messages) > 6 else all_messages
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_documents_for_space(self, space_id: int) -> List[Dict]:
        """
        (Edited from get_all_documents)
        Now returns documents only for a specific Space.
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
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
            self.pool.putconn(conn)

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
            self.pool.putconn(conn)

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
                VALUES (%s, %s, %s, %s) RETURNING id
            """
            cursor.execute(query, (space_id, filename, file_type, file_url))
            doc_id = cursor.fetchone()[0]
            conn.commit()
            return doc_id
        finally:
            cursor.close()
            self.pool.putconn(conn)


    def link_thread_to_doc(self, thread_id, doc_id, page_num=1):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # PostgreSQL uses ON CONFLICT DO NOTHING instead of INSERT IGNORE
            query = """
                INSERT INTO context_anchors (thread_id, document_id, page_number)
                VALUES (%s, %s, %s)
                ON CONFLICT (thread_id, document_id, page_number) DO NOTHING
            """
            cursor.execute(query, (thread_id, doc_id, page_num))
            conn.commit()
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_thread_with_messages(self, thread_id: int) -> Optional[Dict]:
        """
        Retrieves a thread and only its MAIN thread messages (branch_id IS NULL).
        Branch messages are excluded to keep the main conversation clean.
        Returns a dictionary with thread info and list of messages.
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
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

            # Get only MAIN THREAD messages (branch_id IS NULL)
            # This excludes all forked/branched messages
            messages_query = """
                SELECT id, user_id, role, content, path, parent_message_id, 
                       branch_id, created_at
                FROM messages
                WHERE thread_id = %s AND branch_id IS NULL
                ORDER BY id ASC
            """
            cursor.execute(messages_query, (thread_id,))
            messages = cursor.fetchall()

            # Combine thread info with messages
            thread['messages'] = messages
            return thread
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_threads_for_document(self, document_id: int) -> List[Dict]:
        """Retrieves all threads associated with a specific document, 
        resolving the creator's name instead of ID.
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Changes made:
            # 1. Selected 'u.full_name' instead of 't.creator_user_id'
            # 2. Added 'INNER JOIN "user" u ON t.creator_user_id = u.id'
            query = """
                SELECT t.id, t.title, u.full_name AS user, t.created_at,
                    ca.page_number
                FROM threads t
                INNER JOIN context_anchors ca ON t.id = ca.thread_id
                INNER JOIN "user" u ON t.creator_user_id = u.id
                WHERE ca.document_id = %s
                ORDER BY ca.page_number ASC, t.created_at DESC
            """
            cursor.execute(query, (document_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            self.pool.putconn(conn)
    def create_space(self, name: str, description: str = None) -> int:
        """Creates a new workspace (e.g., 'Legal Team', 'Project Alpha')."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            query = "INSERT INTO spaces (name, description) VALUES (%s, %s) RETURNING id"
            cursor.execute(query, (name, description))
            space_id = cursor.fetchone()[0]
            conn.commit()
            return space_id
        finally:
            cursor.close()
            self.pool.putconn(conn)

    def get_spaces(self) -> List[Dict]:
        """Lists all available workspaces."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT * FROM spaces ORDER BY created_at DESC")
            return cursor.fetchall()
        finally:
            cursor.close()
            self.pool.putconn(conn)


    def get_message_by_id(self, message_id: int) -> Optional[Dict]:
        """Helper to fetch a single message."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            self.pool.putconn(conn)

    # --- FORKING LOGIC (Fixed & Pooled) ---
    def get_thread_forks(self, thread_id: int) -> Dict[int, List[Dict]]:
        """
        Retrieves all fork start messages for a thread, grouped by their parent message.
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            query = """
                SELECT id, parent_message_id, content, created_at
                FROM messages
                WHERE thread_id = %s 
                AND branch_id = id  -- Identifies start of a new branch
            """
            cursor.execute(query, (thread_id,))
            rows = cursor.fetchall()
        
            forks_map = {}
            for row in rows:
                parent_id = row['parent_message_id']
                if parent_id not in forks_map:
                    forks_map[parent_id] = []
                
                forks_map[parent_id].append({
                    "branch_id": row['id'], 
                    "preview": row['content'][:150], 
                    "created_at": row['created_at']
                })
            return forks_map
        finally:
            cursor.close()
            self.pool.putconn(conn) # Returns connection to pool

    def get_branch_full_view(self, branch_start_message_id: int) -> List[Dict]:
        """
        Fetches the linear conversation path for a specific branch.
        """
        conn = self.get_connection()
        # We need two cursors or separate executions. 
        # Since we call other methods (get_message_by_id, get_context_messages) 
        # which get their OWN connections from the pool, we only use this connection
        # for the final specific query.
        
        try:
            # 1. Fetch start message (This gets its own conn from pool temporarily)
            start_msg = self.get_message_by_id(branch_start_message_id) 
            if not start_msg:
                return []

            # 2. Get Ancestors (This gets its own conn from pool temporarily)
            ancestors = self.get_context_messages(start_msg['parent_message_id'])

            # 3. Get branch descendants using the current connection
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            branch_query = """
                SELECT * FROM messages 
                WHERE thread_id = %s AND branch_id = %s
                ORDER BY created_at ASC
            """
            cursor.execute(branch_query, (start_msg['thread_id'], start_msg['branch_id']))
            branch_descendants = cursor.fetchall()
            cursor.close()

            # Combine: Ancestors -> Fork Start -> Children of Fork
            return ancestors + [start_msg] + branch_descendants
        finally:
            self.pool.putconn(conn) # Returns connection to pool

    def get_branch_messages_only(self, branch_start_message_id: int) -> List[Dict]:
        """
        Fetches only the messages in a branch (starting from the fork question),
        without including ancestor messages from the main thread.
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Get all messages with this branch_id (includes the fork start + descendants)
            query = """
                SELECT id, thread_id, user_id, role, content, created_at, branch_id
                FROM messages 
                WHERE branch_id = %s
                ORDER BY created_at ASC
            """
            cursor.execute(query, (branch_start_message_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            self.pool.putconn(conn)



import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import unquote

# Setup logging
logger = logging.getLogger("ChatState")


class OmarHandlers:
    """
    RESPONSIBILITY:
    Strictly manages conversation state, logging, and database interactions.
    It does NOT know about the AI/RAG system.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def ensure_thread(self, user_id: int, query_text: str,space_id: int, thread_id: int = None) -> int:
        """Creates a new thread if needed, or validates the existing one."""
        if not thread_id:
            # Create Title from query
            title_snippet = (query_text[:47] + '...') if len(query_text) > 47 else query_text
            thread_id = self.db.create_thread(title=title_snippet, creator_id=user_id, space_id=space_id)
            logger.info(f"Created new thread ID: {thread_id}")
            return thread_id
        return thread_id

    def resolve_parent_message(self, thread_id: int, requested_parent_id: int = None, branch_id: int = None) -> Optional[int]:
        """
        Simplified: Just returns the parent ID. 
        Fork detection is now handled by which endpoint is called.
        this function had an older version that detects forks because i made one function
        that texts normally and forks too, but then i made a separate endpoint for forks,
        and the fork detection logic is not needed here anymore.


        Returns the parent message ID for a new message.
        - If requested_parent_id is provided, use it directly
        - Otherwise, find the last message in the appropriate context (main thread or branch)
        - Returns None if no parent exists (first message in thread/branch)

        """
        if requested_parent_id:
            return requested_parent_id
        
        # No parent specified - find the last message in the appropriate context
        last_msg_id = self.db.get_last_message_id(thread_id, branch_id)
        return last_msg_id

    def log_user_message(self, thread_id: int, user_id: int, content: str, parent_id: Optional[int], is_fork: bool) -> int:
        """Saves the user's input to DB."""
        return self.db.add_message(
            thread_id=thread_id,
            user_id=user_id,
            role="user",
            content=content,
            parent_message_id=parent_id,
            is_fork_start=is_fork
        )

    def get_chat_history(self, parent_id: int) -> List[Dict]:
        """Fetches context for the AI."""
        if not parent_id:
            return []

        history = self.db.get_context_messages(parent_id)
        logger.info(f"Fetched {len(history)} messages of history context.")
        return history

    def log_ai_response(self, thread_id: int, content: str, parent_id: int) -> int:
        """Saves the AI's output to DB."""
        return self.db.add_message(
            thread_id=thread_id,
            user_id=0,  # System ID
            role="assistant",
            content=content,
            parent_message_id=parent_id,
            is_fork_start=False  # AI never starts a fork
        )

    def anchor_thread_to_document(self, thread_id: int, source_filename: str, space_id: int):
        """Links the thread to the document used by RAG."""
        if not source_filename:
            return

        # URL-decode the filename (e.g., "RAG%20Test.pdf" -> "RAG Test.pdf")
        clean_filename = unquote(source_filename.replace("temp_", ""))
        doc_id = self.db.get_document_id_by_filename(space_id, clean_filename)

        if doc_id:
            self.db.link_thread_to_doc(thread_id, doc_id, page_num=1)
            logger.info(f"Anchored Thread {thread_id} to Document {doc_id}")
        else:
            logger.warning(f"Could not anchor thread: Document '{clean_filename}' not found in DB.")
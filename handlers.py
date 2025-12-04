import logging
from typing import List, Dict, Optional, Tuple

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

    def ensure_thread(self, user_id: int, query_text: str, thread_id: int = None) -> int:
        """Creates a new thread if needed, or validates the existing one."""
        if not thread_id:
            # Create Title from query
            title_snippet = (query_text[:47] + '...') if len(query_text) > 47 else query_text
            thread_id = self.db.create_thread(title=title_snippet, creator_id=user_id)
            logger.info(f"Created new thread ID: {thread_id}")
            return thread_id
        return thread_id

    def resolve_parent_message(self, thread_id: int, requested_parent_id: int = None) -> Tuple[int, bool]:
        """
        Determines the actual parent message ID and whether this is a fork.
        Returns: (actual_parent_id, is_new_fork)
        """
        if requested_parent_id:
            # User explicitly chose a message to reply to
            last_msg_id = self.db.get_last_message_id(thread_id)
            # If they chose a message that ISN'T the last one, it's a fork
            is_fork = (last_msg_id and requested_parent_id != last_msg_id)
            if is_fork:
                logger.info(f"Fork detected from Message {requested_parent_id}")
            return requested_parent_id, is_fork

        # Default: Reply to the latest message
        last_id = self.db.get_last_message_id(thread_id)
        return last_id, False

    def log_user_message(self, thread_id: int, user_id: int, content: str, parent_id: int, is_fork: bool) -> int:
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

    def anchor_thread_to_document(self, thread_id: int, source_filename: str):
        """Links the thread to the document used by RAG."""
        if not source_filename:
            return

        clean_filename = source_filename.replace("temp_", "")
        doc_id = self.db.get_document_id_by_filename(clean_filename)

        if doc_id:
            self.db.link_thread_to_doc(thread_id, doc_id, page_num=1)
            logger.info(f"Anchored Thread {thread_id} to Document {doc_id}")
        else:
            logger.warning(f"Could not anchor thread: Document '{clean_filename}' not found in DB.")
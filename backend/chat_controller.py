import logging
from handlers import OmarHandlers

# from advanced_rag import AdvancedRAGSystem # The Intelligence (Imported in main, passed in init)

logger = logging.getLogger("ChatController")


class ChatController:
    def __init__(self, db_manager, rag_system):
        """
        The Conductor. Coordinates the Database (State) and the AI (Intelligence).
        """
        # Initialize the state handler
        self.state_handler = OmarHandlers(db_manager)
        self.rag = rag_system

    def process_user_query(self, user_id: int, query_text: str, space_id: int, thread_id: int = None,
                           parent_message_id: int = None, use_history: bool = True):
        """
        Main Business Logic Flow:
        1. Prepare DB State (Thread/Parent/Fork detection)
        2. Log User Message
        3. Fetch History (Memory)
        4. Call AI (RAG)
        5. Log AI Response
        6. Update Document Anchors
        """

        # 1. State Preparation
        current_thread_id = self.state_handler.ensure_thread(user_id, query_text,space_id, thread_id)
        actual_parent_id, is_fork = self.state_handler.resolve_parent_message(current_thread_id, parent_message_id)

        # 2. Log User Message
        user_msg_id = self.state_handler.log_user_message(
            thread_id=current_thread_id,
            user_id=user_id,
            content=query_text,
            parent_id=actual_parent_id,
            is_fork=is_fork
        )

        # 3. Memory Retrieval
        history_context = []
        if use_history and actual_parent_id:
            history_context = self.state_handler.get_chat_history(actual_parent_id)
        else:
            logger.info("Starting fresh context (History disabled or new thread).")

        # 4. Intelligence (RAG Query)
        # We pass the history we just fetched to the AI
        rag_result = self.rag.query(query_text, space_id=space_id,history_messages= history_context)

        ai_text = rag_result.get('answer', "Error processing response.")
        source_doc = rag_result.get('source_document')

        # 5. Log AI Response
        self.state_handler.log_ai_response(
            thread_id=current_thread_id,
            content=ai_text,
            parent_id=user_msg_id  # AI replies to the user's new message
        )

        # 6. Post-Processing (Anchoring)
        if source_doc:
            self.state_handler.anchor_thread_to_document(current_thread_id, source_doc, space_id)

        # 7. Return API Response
        return {
            "thread_id": current_thread_id,
            "response": ai_text,
            "source": source_doc,
            "is_fork": is_fork
        }
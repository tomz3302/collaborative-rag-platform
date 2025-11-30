import logging

# Setup logging
logger = logging.getLogger("ChatService")


class OmarHandlers:
    def __init__(self, db_manager, rag_system):
        """
        :param db_manager: Instance of DBManager
        :param rag_system: Instance of AdvancedRAGSystem
        """
        self.db = db_manager
        self.rag = rag_system

    def handle_user_query(self, user_id: int, query_text: str, thread_id: int = None):
        # --- Step 1: Thread Management ---
        if not thread_id:
            title_snippet = (query_text[:47] + '...') if len(query_text) > 47 else query_text
            thread_id = self.db.create_thread(title=title_snippet, creator_id=user_id)
            logger.info(f"Created new thread ID: {thread_id}")
            parent_msg_id = None
        else:
            parent_msg_id = self.db.get_last_message_id(thread_id)

        # --- Step 2: Save User Question ---
        user_msg_id = self.db.add_message(
            thread_id=thread_id,
            user_id=user_id,
            role="user",
            content=query_text,
            parent_message_id=parent_msg_id
        )

        # --- Step 3: Query the RAG System (Directly, no requests.post) ---
        # We call the python method directly since we are in the same app
        rag_result = self.rag.query(query_text)

        # Ensure we handle the dict response correctly
        ai_response_text = rag_result.get('answer', "I'm sorry, I couldn't process that.")
        source_filename = rag_result.get('source_document')

        # --- Step 4: Save AI Response ---
        self.db.add_message(
            thread_id=thread_id,
            user_id=0,  # 0 usually represents the System/AI
            role="assistant",
            content=ai_response_text,
            parent_message_id=user_msg_id
        )

        # --- Step 5: Automatic Context Anchoring ---
        if source_filename:
            # Clean up filename if needed (e.g., remove 'temp_' prefix if DB stores it differently)
            clean_filename = source_filename.replace("temp_", "")

            doc_id = self.db.get_document_id_by_filename(clean_filename)

            if doc_id:
                page_num = 1  # Default to 1 for now
                self.db.link_thread_to_doc(thread_id, doc_id, page_num)
                logger.info(f"Anchored Thread {thread_id} to Document {doc_id}")
            else:
                logger.warning(f"RAG cited '{source_filename}', but it was not found in the DB.")

        return {
            "thread_id": thread_id,
            "response": ai_response_text,
            "source": source_filename
        }
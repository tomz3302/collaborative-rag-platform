# backend/dependencies.py
import os
from advanced_rag import AdvancedRAGSystem
from database_manager import DBManager
from chat_controller import ChatController
from handlers import OmarHandlers

# 1. Initialize Managers
db_manager = DBManager()
rag_system = AdvancedRAGSystem()

# 2. Load Embeddings safely
try:
    rag_system.load_existing_embeddings()
except Exception as e:
    print(f"Warning: No embeddings loaded. {e}")

# 3. Initialize Controllers
handler = OmarHandlers(db_manager=db_manager)
chat_controller = ChatController(db_manager=db_manager, rag_system=rag_system)

# 4. Shared Constants
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "backend", "storage")
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)
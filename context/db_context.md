# Database Context Documentation

This document provides a comprehensive overview of the database schema, data access layer, state management, and business logic for the Collaborative RAG Platform.

---

## Table of Contents
1. [Database Schema](#database-schema)
2. [Database Manager (`database_manager.py`)](#database-manager)
3. [State Handlers (`handlers.py`)](#state-handlers)
4. [Chat Controller (`chat_controller.py`)](#chat-controller)

---

## Database Schema

The database is MySQL-based with the following structure:

### 1. **spaces** Table
Top-level workspace container. Each course or project gets its own space.

```sql
CREATE TABLE spaces (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Purpose**: Organize documents and threads into isolated workspaces (e.g., "CS101", "Physics Lab").

---

### 2. **documents** Table
Stores metadata for uploaded PDF files.

```sql
CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    space_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    file_url TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
)
```

**Purpose**: Track documents within a space. `file_url` points to Supabase storage.

**Key Fields**:
- `space_id`: Links document to a workspace
- `file_url`: Public URL from Supabase (e.g., `https://xyz.supabase.co/storage/v1/...`)

---

### 3. **threads** Table
Conversation threads for Q&A sessions.

```sql
CREATE TABLE threads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    space_id INT NOT NULL,
    title VARCHAR(255),
    creator_user_id INT,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
)
```

**Purpose**: Organize conversation flows within a space.

**Key Fields**:
- `space_id`: Threads belong to a specific workspace
- `creator_user_id`: User who started the conversation
- `title`: Auto-generated from first query

---

### 4. **context_anchors** Table
Links threads to specific documents and pages.

```sql
CREATE TABLE context_anchors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    thread_id INT NOT NULL,
    document_id INT NOT NULL,
    page_number INT DEFAULT 1,
    UNIQUE KEY unique_anchor (thread_id, document_id, page_number),
    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
)
```

**Purpose**: Track which document/page a conversation is about (for document-aware discussions).

---

### 5. **messages** Table
Core message storage with hierarchical path structure for branching conversations.

```sql
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    thread_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    path TEXT NOT NULL,
    parent_message_id INT,
    branch_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL
)
```

**Purpose**: Store conversation messages with support for forking/branching.

**Key Fields**:
- `path`: Materialized path (e.g., `1/5/20/`) for efficient ancestor queries
- `parent_message_id`: Direct parent for tree structure
- `branch_id`: Identifies which branch the message belongs to (NULL for main thread)
- `role`: 'user', 'assistant', or 'system'

**Path Logic**:
- Main thread: `branch_id = NULL`
- Fork starts: `branch_id = message_id` (self-referencing)
- Fork continuation: `branch_id` inherited from parent

---

### Indexes
Optimized for fast lookups:

```sql
-- Fast path traversal for history
CREATE INDEX idx_messages_path ON messages (path(20));

-- Fast branch queries
CREATE INDEX idx_messages_branching ON messages (thread_id, branch_id);

-- Fast document/page lookups
CREATE INDEX idx_anchors_doc_page ON context_anchors (document_id, page_number);

-- Fast space filtering
CREATE INDEX idx_documents_space ON documents (space_id);
CREATE INDEX idx_threads_space ON threads (space_id);
```

---

## Database Manager

**File**: `database_manager.py`

**Class**: `DBManager`

**Purpose**: Low-level database access layer with CRUD operations. No business logic.

### Methods

#### Space Operations

##### `create_space(name: str, description: str = None) -> int`
Creates a new workspace.

**Returns**: Space ID

**Example**:
```python
space_id = db.create_space("CS101", "Computer Science Fundamentals")
```

---

##### `get_spaces() -> List[Dict]`
Retrieves all workspaces, ordered by creation date (newest first).

**Returns**: List of space dictionaries

---

#### Document Operations

##### `add_document(space_id: int, filename: str, file_type: str, file_url: str) -> int`
Registers a document after uploading to Supabase.

**Parameters**:
- `file_url`: Public Supabase URL

**Returns**: Document ID

---

##### `get_documents_for_space(space_id: int) -> List[Dict]`
Retrieves all documents in a workspace.

**Returns**: List of document dictionaries with `id`, `filename`, `file_type`, `file_url`, `uploaded_at`

---

##### `get_document_id_by_filename(space_id: int, filename: str) -> Optional[int]`
Finds a document by filename within a space (uses LIKE for partial matching).

**Returns**: Document ID or `None`

---

##### `get_threads_for_document(document_id: int) -> List[Dict]`
Retrieves all threads anchored to a document, including creator names and page numbers.

**Returns**: List with `id`, `title`, `user` (full_name), `created_at`, `page_number`

**SQL Join**: Joins with `users` table to resolve creator names

---

#### Thread Operations

##### `create_thread(space_id: int, title: str, creator_id: int) -> int`
Creates a new conversation thread.

**Returns**: Thread ID

---

##### `get_threads_for_space(space_id: int) -> List[Dict]`
Retrieves all threads in a workspace.

**Returns**: List of thread dictionaries

---

##### `get_thread_with_messages(thread_id: int) -> Optional[Dict]`
Retrieves a complete thread with all messages and metadata.

**Returns**: Dictionary with thread info + nested `messages` list

**Structure**:
```python
{
    'id': 1,
    'title': 'What is RAG?',
    'creator_user_id': 123,
    'created_at': '...',
    'page_number': 5,
    'messages': [
        {'id': 1, 'role': 'user', 'content': '...', 'path': '1/', ...},
        {'id': 2, 'role': 'assistant', 'content': '...', 'path': '1/2/', ...}
    ]
}
```

---

##### `get_last_message_id(thread_id: int) -> Optional[int]`
Gets the ID of the most recent message in a thread.

**Use Case**: Determine if a reply is a fork or continuation

---

##### `link_thread_to_doc(thread_id: int, doc_id: int, page_num: int = 1)`
Creates a context anchor linking a thread to a document/page.

**Uses**: `INSERT IGNORE` to avoid duplicate anchors

---

#### Message Operations

##### `add_message(thread_id, user_id, role, content, parent_message_id=None, is_fork_start=False) -> int`
Adds a message with automatic path calculation and branch management.

**Parameters**:
- `is_fork_start`: If `True`, sets `branch_id = message_id` (starts new branch)

**Logic**:
1. Fetch parent's path and branch_id
2. Insert message with temporary empty path
3. Calculate new path: `parent_path + new_id + '/'`
4. Determine branch_id:
   - Fork start: `branch_id = new_id`
   - Normal reply: inherit parent's `branch_id`
5. Update message with final path and branch_id

**Returns**: New message ID

---

##### `get_context_messages(parent_message_id: int) -> List[Dict]`
Retrieves full conversation history using materialized path.

**Algorithm**:
1. Get parent's path (e.g., `"1/5/20/"`)
2. Parse path into list of IDs: `[1, 5, 20]`
3. Fetch all messages with those IDs
4. Return in chronological order

**Returns**: List of `{'role': '...', 'content': '...'}` dictionaries

**Use Case**: Provide context to RAG system for history-aware responses

---

## State Handlers

**File**: `handlers.py`

**Class**: `OmarHandlers`

**Purpose**: High-level state management and conversation flow logic. Bridges database and business logic without knowing about RAG/AI internals.

### Methods

#### `ensure_thread(user_id, query_text, space_id, thread_id=None) -> int`
Creates a new thread if needed, or validates an existing one.

**Logic**:
- If `thread_id` provided: return it
- If `None`: create new thread with auto-generated title (first 47 chars of query)

**Returns**: Thread ID

---

#### `resolve_parent_message(thread_id, requested_parent_id=None) -> Tuple[int, bool]`
Determines the parent message and detects forking.

**Logic**:
1. If `requested_parent_id` is provided:
   - Check if it's the last message in thread
   - If not last → **Fork detected**
2. If `None`: use last message as parent

**Returns**: `(actual_parent_id, is_fork)`

**Fork Detection**:
```python
last_msg = db.get_last_message_id(thread)
is_fork = (last_msg and requested_parent != last_msg)
```

---

#### `log_user_message(thread_id, user_id, content, parent_id, is_fork) -> int`
Saves user input to database with fork flag.

**Returns**: Message ID

---

#### `get_chat_history(parent_id) -> List[Dict]`
Fetches conversation context for AI.

**Returns**: List of messages in `{'role': '...', 'content': '...'}` format

**Use Case**: Passed to RAG system for context-aware responses

---

#### `log_ai_response(thread_id, content, parent_id) -> int`
Saves AI response to database.

**Auto-sets**: `user_id=0` (system), `role='assistant'`, `is_fork_start=False`

---

#### `anchor_thread_to_document(thread_id, source_filename, space_id)`
Links thread to the document that was used by RAG.

**Logic**:
1. URL-decode filename (`RAG%20Test.pdf` → `RAG Test.pdf`)
2. Strip `temp_` prefix if present
3. Look up document ID in database
4. Create context anchor

**URL Decoding**: Handles filenames with spaces from frontend

---

## Chat Controller

**File**: `chat_controller.py`

**Class**: `ChatController`

**Purpose**: Orchestrates the complete chat flow. Coordinates between state management (handlers) and AI (RAG system).

### Constructor

```python
def __init__(self, db_manager, rag_system):
    self.state_handler = OmarHandlers(db_manager)
    self.rag = rag_system
```

**Dependencies**: Requires `DBManager` and `AdvancedRAGSystem` instances

---

### Main Method

#### `process_user_query(user_id, query_text, space_id, thread_id=None, parent_message_id=None, use_history=True)`

**Purpose**: Complete request-response cycle with state persistence.

**Flow**:

##### 1. State Preparation
```python
current_thread_id = self.state_handler.ensure_thread(user_id, query_text, space_id, thread_id)
actual_parent_id, is_fork = self.state_handler.resolve_parent_message(current_thread_id, parent_message_id)
```

**Actions**:
- Create thread if needed
- Detect forking

---

##### 2. Log User Message
```python
user_msg_id = self.state_handler.log_user_message(
    thread_id=current_thread_id,
    user_id=user_id,
    content=query_text,
    parent_id=actual_parent_id,
    is_fork=is_fork
)
```

**Actions**:
- Save user input to database
- Update path and branch_id

---

##### 3. Memory Retrieval
```python
history_context = []
if use_history and actual_parent_id:
    history_context = self.state_handler.get_chat_history(actual_parent_id)
```

**Actions**:
- Fetch conversation history if enabled
- Use materialized path for efficient traversal

---

##### 4. Intelligence (RAG Query)
```python
rag_result = self.rag.query(query_text, space_id=space_id, history_messages=history_context)
```

**Actions**:
- Pass query to RAG system
- Include history for context-aware responses
- RAG performs:
  - Query contextualization (if history exists)
  - Hybrid retrieval (FAISS + BM25)
  - Cross-encoder reranking
  - LLM generation

---

##### 5. Log AI Response
```python
self.state_handler.log_ai_response(
    thread_id=current_thread_id,
    content=ai_text,
    parent_id=user_msg_id
)
```

**Actions**:
- Save AI response as child of user message

---

##### 6. Document Anchoring
```python
if source_doc:
    self.state_handler.anchor_thread_to_document(current_thread_id, source_doc, space_id)
```

**Actions**:
- Link thread to source document
- Enables document-centric threading

---

##### 7. Return API Response
```python
return {
    "thread_id": current_thread_id,
    "response": ai_text,
    "source": source_doc,
    "is_fork": is_fork
}
```

**Response Structure**:
- `thread_id`: For follow-up queries
- `response`: AI-generated answer
- `source`: Source document filename
- `is_fork`: Flag for frontend branching UI

---

## Data Flow Summary

```
API Request
    ↓
ChatController.process_user_query()
    ↓
1. OmarHandlers.ensure_thread()
   → DBManager.create_thread() OR validate existing
    ↓
2. OmarHandlers.resolve_parent_message()
   → DBManager.get_last_message_id()
   → Detect fork
    ↓
3. OmarHandlers.log_user_message()
   → DBManager.add_message() [with path calculation]
    ↓
4. OmarHandlers.get_chat_history()
   → DBManager.get_context_messages() [path-based query]
    ↓
5. AdvancedRAGSystem.query()
   → Contextualize query (if history)
   → Hybrid retrieval
   → Reranking
   → LLM generation
    ↓
6. OmarHandlers.log_ai_response()
   → DBManager.add_message()
    ↓
7. OmarHandlers.anchor_thread_to_document()
   → DBManager.get_document_id_by_filename()
   → DBManager.link_thread_to_doc()
    ↓
API Response
```

---

## Key Design Patterns

### 1. **Separation of Concerns**
- **DBManager**: Pure data access (SQL queries)
- **OmarHandlers**: State management and conversation flow
- **ChatController**: Business logic orchestration
- **AdvancedRAGSystem**: AI/RAG implementation

### 2. **Materialized Path Pattern**
- Enables O(1) ancestor queries for conversation history
- Path format: `"1/5/20/"` represents message chain
- No recursive CTEs needed

### 3. **Branching/Forking Support**
- `branch_id` identifies conversation branches
- Detected by comparing requested parent to last message
- Frontend can visualize as "mind map"

### 4. **Space Isolation**
- All queries scoped to `space_id`
- Enables multi-tenant architecture
- Same filename can exist in different spaces

### 5. **Cloud Storage Integration**
- Documents stored in Supabase
- Database stores only metadata + URL
- RAG downloads temporarily for processing

---

## Common Query Patterns

### Get all threads for a document
```python
threads = db.get_threads_for_document(doc_id)
# Returns threads with creator names and page anchors
```

### Get conversation history for context
```python
history = handlers.get_chat_history(parent_message_id)
# Returns list of role/content dictionaries
```

### Process a new query with history
```python
result = controller.process_user_query(
    user_id=user.id,
    query_text="What is RAG?",
    space_id=1,
    thread_id=existing_thread_id,  # Optional
    use_history=True
)
```

### Start a new branch/fork
```python
result = controller.process_user_query(
    user_id=user.id,
    query_text="Can you elaborate on embeddings?",
    space_id=1,
    thread_id=existing_thread_id,
    parent_message_id=5,  # Specific message to branch from
)
# If message 5 isn't the last message, is_fork=True
```

---

## Error Handling

- **Missing documents**: Warns but doesn't crash when anchoring fails
- **URL encoding**: Automatically handles `%20` in filenames
- **Duplicate anchors**: Uses `INSERT IGNORE` to prevent errors
- **Graceful degradation**: History disabled if parent_id is None
- **Transaction safety**: Each operation uses try/finally for connection cleanup

---

## Performance Considerations

- **Indexed paths**: First 20 chars indexed for fast prefix matching
- **Connection pooling**: Each method opens/closes connections (consider pooling for production)
- **Batch operations**: BM25 rebuild optimized per space
- **Lazy loading**: Documents downloaded only when needed

---

## Future Enhancements

1. **Connection Pooling**: Replace individual connections with pool
2. **Async Database**: Migrate to aiomysql for async operations
3. **Caching**: Add Redis for frequent queries (spaces, documents)
4. **Soft Deletes**: Add `deleted_at` columns instead of hard deletes
5. **Audit Logs**: Track all message edits/deletions
6. **Full-Text Search**: Add MySQL FULLTEXT indexes for message content

---

*Last Updated: December 14, 2025*

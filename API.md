# Nexus RAG API Documentation

## Overview
Nexus RAG is a Retrieval-Augmented Generation (RAG) system with social collaboration features built on FastAPI. It allows users to upload documents, query them intelligently, and have conversations organized in threads with branching discussions.

**Base URL:** `http://localhost:8000`

---

## Table of Contents
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Documents](#documents)
  - [Chat & Queries](#chat--queries)
  - [Threads](#threads)
  - [Messages](#messages)
- [Request/Response Models](#requestresponse-models)
- [Error Handling](#error-handling)

---

## Authentication
Currently, the API uses a default user ID (`user_id: 1`) for all requests. In future versions, implement proper user authentication (JWT tokens, session management, etc.).

---

## Endpoints

### Documents

#### GET `/api/documents`
Fetch a list of all uploaded documents.

**Parameters:** None

**Response:**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "RAG Stress Test.pdf",
      "file_type": "pdf",
      "uploaded_at": "2025-12-03T13:31:10"
    },
    {
      "id": 2,
      "filename": "Agile Software Engineering Project (2).pdf",
      "file_type": "pdf",
      "uploaded_at": "2025-12-04T22:33:55"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved documents
- `500 Internal Server Error` - Database error

---

#### POST `/api/upload`
Upload a PDF file to the knowledge base. The file is processed and indexed for RAG queries.

**Parameters:**
- `file` (multipart/form-data, required) - PDF file to upload

**Response:**
```json
{
  "status": "success",
  "message": "Knowledge Base Ready"
}
```

**Status Codes:**
- `200 OK` - File successfully uploaded and indexed
- `500 Internal Server Error` - File processing error

**Example:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@document.pdf"
```

---

#### GET `/api/documents/{doc_id}/content`
Stream the PDF file content for viewing in the browser.

**Parameters:**
- `doc_id` (path, required) - Document ID

**Response:** PDF file stream

**Status Codes:**
- `200 OK` - File successfully retrieved
- `404 Not Found` - Document not found or file missing

**Example:**
```bash
curl -X GET http://localhost:8000/api/documents/1/content \
  --output document.pdf
```

---

#### GET `/api/documents/{doc_id}/threads`
Fetch all threads (conversations) associated with a specific document.

**Parameters:**
- `doc_id` (path, required) - Document ID

**Response:**
```json
{
  "threads": [
    {
      "id": 1,
      "document_id": 1,
      "title": "QuickSort Complexity Analysis",
      "page_number": 4,
      "created_at": "2025-12-04T10:15:30",
      "updated_at": "2025-12-04T10:45:20"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved threads
- `500 Internal Server Error` - Database error

---

### Chat & Queries

#### POST `/api/chat`
Send a query to the RAG system. Creates a new thread or continues an existing one.

**Request Body:**
```json
{
  "text": "Explain the time complexity of QuickSort",
  "user_id": 1,
  "thread_id": null
}
```

**Response:**
```json
{
  "response": "QuickSort has a time complexity of O(n log n) in the average case and O(n²) in the worst case...",
  "source": "RAG Stress Test.pdf",
  "thread_id": 1
}
```

**Parameters:**
- `text` (string, required) - User query
- `user_id` (integer, optional, default: 1) - User ID
- `thread_id` (integer, optional) - Existing thread ID to continue conversation

**Status Codes:**
- `200 OK` - Query processed successfully
- `500 Internal Server Error` - Processing error

**Example:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is the best sorting algorithm?",
    "user_id": 1
  }'
```

---

#### POST `/api/threads/{thread_id}/branch`
Create a branch from a specific message in a thread. Allows for exploring alternative conversation paths.

**Request Body:**
```json
{
  "content": "Let me explore this further...",
  "parent_message_id": 5,
  "user_id": 1
}
```

**Response:**
```json
{
  "response": "Detailed analysis of the branched topic...",
  "source": "RAG Stress Test.pdf",
  "thread_id": 2
}
```

**Parameters:**
- `thread_id` (path, required) - Parent thread ID
- `content` (string, required) - Message content
- `parent_message_id` (integer, required) - Message ID to branch from
- `user_id` (integer, optional, default: 1) - User ID

**Status Codes:**
- `200 OK` - Branch created successfully
- `500 Internal Server Error` - Processing error

**Example:**
```bash
curl -X POST http://localhost:8000/api/threads/1/branch \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Dig deeper into this concept",
    "parent_message_id": 5,
    "user_id": 1
  }'
```

---

### Threads

#### GET `/api/threads/{thread_id}`
Fetch a single thread with all its messages.

**Parameters:**
- `thread_id` (path, required) - Thread ID

**Response:**
```json
{
  "thread": {
    "id": 1,
    "document_id": 1,
    "title": "QuickSort Complexity Analysis",
    "page_number": 4,
    "created_at": "2025-12-04T10:15:30",
    "messages": [
      {
        "id": 1,
        "thread_id": 1,
        "user_id": 1,
        "role": "user",
        "content": "Explain QuickSort",
        "parent_message_id": null,
        "created_at": "2025-12-04T10:15:30"
      },
      {
        "id": 2,
        "thread_id": 1,
        "user_id": null,
        "role": "assistant",
        "content": "QuickSort is a divide-and-conquer algorithm...",
        "parent_message_id": 1,
        "created_at": "2025-12-04T10:15:45"
      }
    ]
  }
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved thread
- `404 Not Found` - Thread not found
- `500 Internal Server Error` - Database error

**Example:**
```bash
curl -X GET http://localhost:8000/api/threads/1
```

---

### Messages

#### POST `/api/threads/{thread_id}/messages`
Add a new message to an existing thread. The message is linked to the last message in the thread to maintain conversation flow.

**Request Body:**
```json
{
  "content": "Can you provide code examples?",
  "user": "John Doe"
}
```

**Response:**
```json
{
  "status": "success",
  "message_id": 10
}
```

**Parameters:**
- `thread_id` (path, required) - Thread ID
- `content` (string, required) - Message content
- `user` (string, optional, default: "Anonymous") - User name/identifier

**Status Codes:**
- `200 OK` - Message successfully added
- `500 Internal Server Error` - Database error

**Example:**
```bash
curl -X POST http://localhost:8000/api/threads/1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Please provide more examples",
    "user": "Student"
  }'
```

---

## Request/Response Models

### QueryRequest
```python
{
  "text": str,              # Required: User query/message
  "user_id": int,           # Optional, default: 1
  "thread_id": Optional[int] # Optional: Existing thread ID
}
```

### BranchRequest
```python
{
  "content": str,           # Required: Message content
  "parent_message_id": int, # Required: Message ID to branch from
  "user_id": int            # Optional, default: 1
}
```

### MessageRequest
```python
{
  "content": str,           # Required: Message content
  "user": str               # Optional, default: "Anonymous"
}
```

---

## Error Handling

### Standard Error Response
```json
{
  "error": "Error description",
  "status": "error"
}
```

### Common Status Codes
- `200 OK` - Request successful
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error (check logs)

### Logging
All server errors are logged to the console with the prefix `RAG_Server:`. Check the server logs for detailed error messages.

---

## Database Schema Reference

### documents
- `id` (int, PK) - Document ID
- `filename` (str) - Name of the uploaded file
- `file_type` (str) - File type (e.g., "pdf")
- `uploaded_at` (datetime) - Upload timestamp

### threads
- `id` (int, PK) - Thread ID
- `document_id` (int, FK) - Associated document
- `title` (str) - Thread title
- `page_number` (int) - Page reference in document
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp

### messages
- `id` (int, PK) - Message ID
- `thread_id` (int, FK) - Associated thread
- `user_id` (int, FK) - Message author
- `role` (str) - "user" or "assistant"
- `content` (str) - Message text
- `parent_message_id` (int, FK) - Parent message for branching
- `created_at` (datetime) - Creation timestamp

---

## Usage Examples

### Complete Workflow

1. **Upload a document:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@textbook.pdf"
```

2. **Get document list:**
```bash
curl -X GET http://localhost:8000/api/documents
```

3. **Start a new chat:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "What is this document about?"}'
```

4. **Get thread details:**
```bash
curl -X GET http://localhost:8000/api/threads/1
```

5. **Branch from a message:**
```bash
curl -X POST http://localhost:8000/api/threads/1/branch \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Can you explain this more?",
    "parent_message_id": 2
  }'
```

---

## Frontend Integration

The frontend is automatically served from the backend on port 8000. The API endpoints are accessible via the same origin (localhost:8000/api/*).

For development, the frontend dev server can connect to the backend API using:
```
http://localhost:8000/api/...
```

---

## Future Enhancements

- [ ] Implement proper user authentication (JWT)
- [ ] Add pagination for large document lists
- [ ] Implement rate limiting
- [ ] Add API versioning (e.g., `/api/v1/...`)
- [ ] WebSocket support for real-time collaboration
- [ ] Document search/filtering
- [ ] Thread moderation and approval workflow
- [ ] Analytics and usage metrics

---

## Support

For issues or questions:
1. Check server logs (prefixed with `RAG_Server:`)
2. Verify document storage path exists
3. Ensure database is initialized
4. Review error response for details

---

*Last Updated: December 6, 2025*


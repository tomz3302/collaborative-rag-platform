# Clark RAG API Reference

Complete API documentation for the Collaborative RAG Platform backend server.

**Base URL:** `http://localhost:8000`

**Default Port:** 8000

---

## Table of Contents
1. [Authentication & Users](#authentication--users)
2. [Upload API](#upload-api)
3. [Chat APIs](#chat-apis)
4. [Document APIs](#document-apis)
5. [Thread APIs](#thread-apis)
6. [Space APIs](#space-apis)

---

## Authentication & Users

The API uses JWT (JSON Web Tokens) for authentication. Protected routes require the `Authorization` header with a Bearer token.

### POST /auth/register
Create a new user account.

**Endpoint:** `POST /auth/register`

**Auth Required:** No

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "email": "student@alexu.edu.eg",
  "password": "securepassword123",
  "full_name": "Omar Ahmed",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false
}
```

**Request Schema:**
- `email` (string, required): Valid email address
- `password` (string, required): Password (minimum 8 characters)
- `full_name` (string, optional): User's full name
- `is_active` (boolean, optional, default: true): Account active status
- `is_superuser` (boolean, optional, default: false): Superuser privileges
- `is_verified` (boolean, optional, default: false): Email verification status

**Success Response (201 Created):**
```json
{
  "id": 1,
  "email": "student@alexu.edu.eg",
  "is_active": true,
  "is_superuser": false,
  "is_verified": false,
  "full_name": "Omar Ahmed"
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "REGISTER_USER_ALREADY_EXISTS"
}
```
or
```json
{
  "detail": "REGISTER_INVALID_PASSWORD"
}
```

**Common Error Codes:**
- `REGISTER_USER_ALREADY_EXISTS`: A user with this email already exists
- `REGISTER_INVALID_PASSWORD`: Password doesn't meet requirements (min 8 characters)

**Example (PowerShell):**
```powershell
curl -X POST http://localhost:8000/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"student@alexu.edu.eg","password":"securepass123","full_name":"Omar Ahmed"}'
```

**Example (JavaScript/Fetch):**
```javascript
const response = await fetch('/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'student@alexu.edu.eg',
    password: 'securepass123',
    full_name: 'Omar Ahmed'
  })
});
const user = await response.json();
```

---

### POST /auth/jwt/login
Authenticate and receive an access token.

**Endpoint:** `POST /auth/jwt/login`

**Auth Required:** No

**Content-Type:** `application/x-www-form-urlencoded`

**Request Body (Form Data):**
- `username` (string, required): User's email address (field name is "username" but send email)
- `password` (string, required): User's password

**Success Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "LOGIN_BAD_CREDENTIALS"
}
```

**Example (PowerShell):**
```powershell
curl -X POST http://localhost:8000/auth/jwt/login `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=student@alexu.edu.eg&password=securepass123"
```

**Example (JavaScript/Fetch):**
```javascript
const formData = new URLSearchParams();
formData.append('username', 'student@alexu.edu.eg');
formData.append('password', 'securepass123');

const response = await fetch('/auth/jwt/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: formData
});
const { access_token } = await response.json();
// Store token for subsequent requests
localStorage.setItem('token', access_token);
```

**Notes:**
- Save the `access_token` - you'll need it for protected endpoints
- Token should be sent in the `Authorization: Bearer <token>` header
- Tokens may have expiration times (check your server configuration)

---

### POST /auth/jwt/logout
Invalidate the current session token.

**Endpoint:** `POST /auth/jwt/logout`

**Auth Required:** Yes

**Headers:**
- `Authorization: Bearer <access_token>`

**Success Response (204 No Content):**
Empty response body.

**Error Response (401 Unauthorized):**
```json
{
  "detail": "Unauthorized"
}
```

**Example (PowerShell):**
```powershell
curl -X POST http://localhost:8000/auth/jwt/logout `
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Example (JavaScript/Fetch):**
```javascript
const token = localStorage.getItem('token');
await fetch('/auth/jwt/logout', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
localStorage.removeItem('token');
```

**Notes:**
- For stateless JWT, this is mainly for frontend cleanup
- Remove the token from local storage after logout

---

### POST /auth/request-verify-token
Request email verification token.

**Endpoint:** `POST /auth/request-verify-token`

**Auth Required:** No

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "email": "student@alexu.edu.eg"
}
```

**Success Response (202 Accepted):**
```json
{
  "message": "Verification email sent"
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "User not found or already verified"
}
```

**Example (PowerShell):**
```powershell
curl -X POST http://localhost:8000/auth/request-verify-token `
  -H "Content-Type: application/json" `
  -d '{"email":"student@alexu.edu.eg"}'
```

**Example (JavaScript/Fetch):**
```javascript
await fetch('/auth/request-verify-token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'student@alexu.edu.eg'
  })
});
```

**Notes:**
- Sends verification email to the user
- Email contains a link or token to verify the account
- Check spam folder if email doesn't arrive

---

### POST /auth/verify
Verify email with token.

**Endpoint:** `POST /auth/verify`

**Auth Required:** No

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "token": "verification-token-from-email"
}
```

**Success Response (200 OK):**
```json
{
  "id": 1,
  "email": "student@alexu.edu.eg",
  "is_active": true,
  "is_superuser": false,
  "is_verified": true,
  "full_name": "Omar Ahmed"
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "VERIFY_USER_BAD_TOKEN"
}
```

**Example (PowerShell):**
```powershell
curl -X POST http://localhost:8000/auth/verify `
  -H "Content-Type: application/json" `
  -d '{"token":"abc123..."}'
```

---

### GET /users/me
Get current authenticated user information.

**Endpoint:** `GET /users/me`

**Auth Required:** Yes

**Headers:**
- `Authorization: Bearer <access_token>`

**Success Response (200 OK):**
```json
{
  "id": 1,
  "email": "student@alexu.edu.eg",
  "is_active": true,
  "is_superuser": false,
  "is_verified": true,
  "full_name": "Omar Ahmed"
}
```

**Error Response (401 Unauthorized):**
```json
{
  "detail": "Unauthorized"
}
```

**Example (PowerShell):**
```powershell
curl http://localhost:8000/users/me `
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Example (JavaScript/Fetch):**
```javascript
const token = localStorage.getItem('token');
const response = await fetch('/users/me', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const user = await response.json();
```

---

## Upload API

### POST /api/upload
Upload a PDF document to the knowledge base and index it for RAG queries.

**Endpoint:** `POST /api/upload`

**Auth Required:** Yes (Bearer token)

**Content-Type:** `multipart/form-data`

**Request Parameters:**
- `file` (form-data, required): PDF file to upload

**Success Response (200):**
```json
{
  "status": "success",
  "message": "file uploaded correctly",
  "document_id": 1
}
```

**Error Response (500):**
```json
{
  "status": "error",
  "detail": "<error message>"
}
```

**Example (PowerShell):**
```powershell
curl -X POST http://localhost:8000/api/upload `
  -F "file=@C:\path\to\document.pdf"
```

**Example (JavaScript/Fetch):**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('/api/upload', {
  method: 'POST',
  body: formData
});
const data = await response.json();
```

**Notes:**
- Files are stored in `backend/storage/` directory
- Document is automatically indexed in the RAG system for semantic search
- Currently defaults to `space_id=1`
- Returns the database ID of the created document

---

## Chat APIs

### POST /api/chat
Send a query to the RAG system and get an AI-generated response with sources.

**Endpoint:** `POST /api/chat`

**Auth Required:** Yes (Bearer token)

**Content-Type:** `application/json`

**Query Parameters:**
- `space_id` (optional, default: 1): The workspace/space ID

**Request Body:**
```json
{
  "text": "What is the main topic of the document?",
  "user_id": 1,
  "thread_id": null
}
```

**Request Schema:**
- `text` (string, required): The user's question/query
- `user_id` (int, optional, default: 1): User ID
- `thread_id` (int, optional): If provided, continues an existing conversation thread

**Success Response (200):**
```json
{
  "answer": "The main topic is...",
  "sources": [...],
  "thread_id": 1,
  "message_id": 42
}
```

**Error Response (500):**
```json
{
  "error": "<error message>"
}
```

**Example (PowerShell):**
```powershell
curl -X POST "http://localhost:8000/api/chat?space_id=1" `
  -H "Content-Type: application/json" `
  -d '{"text":"What is machine learning?","thread_id":null}'
```

**Example (JavaScript/Fetch):**
```javascript
const response = await fetch('/api/chat?space_id=1', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'What is machine learning?',
    thread_id: null
  })
});
const data = await response.json();
```

**Notes:**
- If `thread_id` is null, a new conversation thread is created
- If `thread_id` is provided, the message is added to that thread
- The response includes the `thread_id` - save it to continue the conversation
- Always uses `user_id=1` internally (hardcoded)

---

### POST /api/threads/{thread_id}/branch
Create a branch (fork) from a specific message in a conversation thread.

**Endpoint:** `POST /api/threads/{thread_id}/branch`

**Auth Required:** Yes (Bearer token)

**Content-Type:** `application/json`

**Path Parameters:**
- `thread_id` (int, required): The thread to branch from

**Query Parameters:**
- `space_id` (optional, default: 1): The workspace/space ID

**Request Body:**
```json
{
  "content": "Can you explain this differently?",
  "parent_message_id": 42,
  "user_id": 1
}
```

**Request Schema:**
- `content` (string, required): The new message/query for the branch
- `parent_message_id` (int, required): The message ID to branch from
- `user_id` (int, optional, default: 1): User ID

**Success Response (200):**
```json
{
  "answer": "...",
  "sources": [...],
  "thread_id": 1,
  "message_id": 43
}
```

**Error Response (500):**
```json
{
  "error": "<error message>"
}
```

**Example (PowerShell):**
```powershell
curl -X POST "http://localhost:8000/api/threads/5/branch?space_id=1" `
  -H "Content-Type: application/json" `
  -d '{"content":"Explain this more simply","parent_message_id":42}'
```

**Notes:**
- Creates a new conversational branch from a specific message
- Useful for exploring alternative explanations or "what-if" scenarios
- The branch inherits context from the parent message's conversation path

---

## Document APIs

### GET /api/documents
Retrieve a list of all documents or documents for a specific space.

**Endpoint:** `GET /api/documents`

**Auth Required:** Yes (Bearer token)

**Query Parameters:**
- `space_id` (int, optional): Filter documents by space ID

**Success Response (200):**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "lecture_notes.pdf",
      "file_type": "pdf",
      "file_url": "/path/to/storage/lecture_notes.pdf",
      "uploaded_at": "2025-12-08T10:30:00"
    },
    {
      "id": 2,
      "filename": "textbook.pdf",
      "file_type": "pdf",
      "file_url": "/path/to/storage/textbook.pdf",
      "uploaded_at": "2025-12-07T14:20:00"
    }
  ]
}
```

**Error Response (500):**
```json
{
  "error": "<error message>"
}
```

**Example (PowerShell):**
```powershell
# Get all documents
curl http://localhost:8000/api/documents

# Get documents for a specific space
curl "http://localhost:8000/api/documents?space_id=1"
```

**Example (JavaScript/Fetch):**
```javascript
// Get documents for space_id=1
const response = await fetch('/api/documents?space_id=1');
const data = await response.json();
console.log(data.documents);
```

**Notes:**
- If `space_id` is not provided, returns all documents across all spaces
- If `space_id` is provided, returns only documents in that space
- Includes the `file_url` field which contains the storage path

---

### GET /api/documents/{doc_id}/content
Stream/download the PDF file content.

**Endpoint:** `GET /api/documents/{doc_id}/content`

**Auth Required:** Yes (Bearer token)

**Path Parameters:**
- `doc_id` (int, required): The document ID

**Success Response (200):**
- Returns the PDF file with `Content-Type: application/pdf`

**Error Response (404):**
```json
{
  "detail": "Document not found"
}
```
or
```json
{
  "detail": "File missing from server storage"
}
```

**Example (PowerShell):**
```powershell
# Download PDF
curl http://localhost:8000/api/documents/1/content -o document.pdf
```

**Example (HTML):**
```html
<!-- Embed in iframe -->
<iframe src="/api/documents/1/content" width="100%" height="600px"></iframe>
```

**Notes:**
- Returns the actual PDF file for viewing/downloading
- File is served from `backend/storage/` directory
- Checks database for file metadata before serving

---

### GET /api/documents/{doc_id}/threads
Get all conversation threads associated with a specific document.

**Endpoint:** `GET /api/documents/{doc_id}/threads`

**Auth Required:** Yes (Bearer token)

**Path Parameters:**
- `doc_id` (int, required): The document ID

**Success Response (200):**
```json
{
  "threads": [
    {
      "id": 1,
      "title": "Discussion about Chapter 1",
      "creator_user_id": 1,
      "created_at": "2025-12-08T09:00:00",
      "page_number": 1
    },
    {
      "id": 2,
      "title": "Questions on Section 2.3",
      "creator_user_id": 1,
      "created_at": "2025-12-08T11:30:00",
      "page_number": 15
    }
  ]
}
```

**Error Response (500):**
```json
{
  "error": "<error message>"
}
```

**Example (PowerShell):**
```powershell
curl http://localhost:8000/api/documents/1/threads
```

**Notes:**
- Returns threads linked to the document via context anchors
- Threads are ordered by page number (ascending) and creation date (descending)
- Shows which page of the document each thread is associated with

---

## Thread APIs

### GET /api/threads/{thread_id}
Retrieve a conversation thread with all its messages.

**Endpoint:** `GET /api/threads/{thread_id}`

**Auth Required:** Yes (Bearer token)

**Path Parameters:**
- `thread_id` (int, required): The thread ID

**Success Response (200):**
```json
{
  "thread": {
    "id": 1,
    "title": "Discussion about ML",
    "creator_user_id": 1,
    "is_public": true,
    "created_at": "2025-12-08T09:00:00",
    "page_number": 5,
    "messages": [
      {
        "id": 1,
        "user_id": 1,
        "role": "user",
        "content": "What is machine learning?",
        "path": "1/",
        "parent_message_id": null,
        "branch_id": null,
        "created_at": "2025-12-08T09:00:00"
      },
      {
        "id": 2,
        "user_id": 1,
        "role": "assistant",
        "content": "Machine learning is...",
        "path": "1/2/",
        "parent_message_id": 1,
        "branch_id": null,
        "created_at": "2025-12-08T09:00:05"
      }
    ]
  }
}
```

**Error Response (404):**
```json
{
  "detail": "Thread not found"
}
```

**Error Response (500):**
```json
{
  "error": "<error message>"
}
```

**Example (PowerShell):**
```powershell
curl http://localhost:8000/api/threads/1
```

**Notes:**
- Returns the complete conversation tree with all messages
- Messages include path information for branching/forking
- `path` field shows the message ancestry (e.g., "1/5/20/" means message 20 is a reply to 5, which is a reply to 1)
- `branch_id` indicates which branch the message belongs to (for forked conversations)

---

### POST /api/threads/{thread_id}/messages
Add a new message to an existing thread.

**Endpoint:** `POST /api/threads/{thread_id}/messages`

**Auth Required:** Yes (Bearer token)

**Path Parameters:**
- `thread_id` (int, required): The thread ID

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "content": "Can you elaborate on that?",
  "user_id": "Anonymous"
}
```

**Request Schema:**
- `content` (string, required): The message content
- `user_id` (string, optional, default: "Anonymous"): User identifier (note: currently a string field)

**Success Response (200):**
```json
{
  "status": "success",
  "message_id": 42
}
```

**Error Response (500):**
```json
{
  "error": "<error message>"
}
```

**Example (PowerShell):**
```powershell
curl -X POST http://localhost:8000/api/threads/1/messages `
  -H "Content-Type: application/json" `
  -d '{"content":"Thanks for the explanation!"}'
```

**Notes:**
- Adds a message to the thread as a continuation of the last message
- Uses `user_id=1` internally for database operations
- Returns the created message ID

---

## Space APIs

### POST /api/spaces
Create a new workspace/space for organizing documents and threads.

**Endpoint:** `POST /api/spaces`

**Auth Required:** Yes (Bearer token)

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "name": "CS101 - Algorithms",
  "description": "Course materials and discussions for Algorithms"
}
```

**Request Schema:**
- `name` (string, required): Display name for the space
- `description` (string, optional): Description of the space

**Success Response (200):**
```json
{
  "status": "success",
  "space_id": 1
}
```

**Error Response (500):**
```json
{
  "error": "<error message>"
}
```

**Example (PowerShell):**
```powershell
curl -X POST http://localhost:8000/api/spaces `
  -H "Content-Type: application/json" `
  -d '{"name":"CS101","description":"Algorithms course"}'
```

**Example (JavaScript/Fetch):**
```javascript
const response = await fetch('/api/spaces', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'CS101',
    description: 'Algorithms course'
  })
});
const data = await response.json();
console.log('Created space:', data.space_id);
```

**Notes:**
- Creates a new isolated workspace for organizing resources
- Returns the created `space_id` to use in other API calls
- Use spaces to separate different courses, projects, or teams

---

### GET /api/spaces
Retrieve all available spaces/workspaces.

**Endpoint:** `GET /api/spaces`

**Auth Required:** Yes (Bearer token)

**Success Response (200):**
```json
{
  "spaces": [
    {
      "id": 1,
      "name": "CS101",
      "description": "Algorithms course",
      "created_at": "2025-12-08T12:34:56"
    },
    {
      "id": 2,
      "name": "EE200",
      "description": "Circuit Analysis",
      "created_at": "2025-12-07T09:12:34"
    }
  ]
}
```

**Error Response (500):**
```json
{
  "error": "<error message>"
}
```

**Example (PowerShell):**
```powershell
curl http://localhost:8000/api/spaces
```

**Example (JavaScript/Fetch):**
```javascript
const response = await fetch('/api/spaces');
const data = await response.json();
console.log('Available spaces:', data.spaces);
```

**Notes:**
- Lists all workspaces ordered by creation date (newest first)
- Use this to populate a space selector in your UI
- Each space can contain its own documents, threads, and conversations

---

## Integration Guide

### Frontend Integration Examples

#### Uploading a Document
```javascript
async function uploadDocument(file, spaceId = 1) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}
```

#### Starting a Chat Session
```javascript
async function startChat(question, spaceId = 1) {
  const response = await fetch(`/api/chat?space_id=${spaceId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: question,
      thread_id: null  // null = new conversation
    })
  });
  
  const data = await response.json();
  // Save data.thread_id for follow-up questions
  return data;
}
```

#### Continuing a Conversation
```javascript
async function continueChat(question, threadId, spaceId = 1) {
  const response = await fetch(`/api/chat?space_id=${spaceId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: question,
      thread_id: threadId
    })
  });
  
  return await response.json();
}
```

#### Creating a Branch
```javascript
async function branchConversation(content, threadId, parentMessageId, spaceId = 1) {
  const response = await fetch(`/api/threads/${threadId}/branch?space_id=${spaceId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: content,
      parent_message_id: parentMessageId
    })
  });
  
  return await response.json();
}
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK**: Request successful
- **404 Not Found**: Resource not found (document, thread, etc.)
- **500 Internal Server Error**: Server-side error (check logs)

Error responses include an `error` or `detail` field with a description:
```json
{
  "error": "Description of what went wrong"
}
```

---

## Development Notes

- **Default Space ID**: Most endpoints default to `space_id=1` if not specified
- **User ID**: Currently hardcoded to `user_id=1` for all operations
- **Storage**: Files are stored in `backend/storage/` directory
- **CORS**: Configured for `localhost:8000`, `localhost:5173`, and `127.0.0.1` variants
- **Frontend Build**: Serve frontend from backend using `npm run build` in frontend folder

---

## Server Information

**Title**: Fluid RAG  
**Host**: `0.0.0.0`  
**Port**: `8000`  
**Start Command**: `python -m uvicorn backend.rag_server:app --reload --port 8000`

---

**Last Updated**: December 10, 2025




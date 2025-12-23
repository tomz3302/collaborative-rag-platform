# Clark RAG API Reference

Complete API documentation for the Collaborative RAG Platform backend server.

**Base URL:** `http://localhost:8000`
**Last Updated:** January 2025  
**Default Port:** 8000

---

## Authentication

All protected routes require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

Tokens are valid for 2 hours after login.

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
Upload a PDF document to Supabase storage, index it for RAG queries, and store metadata in the database.

**Endpoint:** `POST /api/upload`

**Auth Required:** Yes (Bearer token)

**Content-Type:** `multipart/form-data`

**Request Parameters:**
- `file` (form-data, required): PDF file to upload
- `space_id` (query parameter, optional): Target space ID (default: 1)

**Success Response (200):**
```json
{
  "status": "success",
  "document_id": 1,
  "url": "https://rrcvxnrtjejetktzkesz.supabase.co/storage/v1/object/public/course-materials/space_1/document.pdf"
}
```

**Error Response (500):**
```json
{
  "detail": "<error message>"
}
```

**Example (PowerShell):**
```powershell
$headers = @{ Authorization = "Bearer $token" }
curl -X POST "http://localhost:8000/api/upload?space_id=1" `
  -H "Authorization: Bearer $token" `
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
- `branch_id` (optional): If continuing within a branch, pass the branch_id for correct context isolation

**Request Body:**
```json
{
  "text": "What is the main topic of the document?",
  "thread_id": null
}
```

**Request Schema:**
- `text` (string, required): The user's question/query
- `thread_id` (int, optional): If provided, continues an existing conversation thread

**Success Response (200):**
```json
{
  "thread_id": 1,
  "response": "The main topic is...",
  "source": "document.pdf",
  "is_fork": false,
  "branch_id": null
}
```

**Response Fields:**
- `thread_id` (int): The conversation thread ID
- `response` (string): The AI-generated answer
- `source` (string|null): Source document filename if RAG was used
- `is_fork` (boolean): Whether this was a branch creation
- `branch_id` (int|null): The branch ID (set when `is_fork=true`, null for main thread)
```

**Error Response (500):**
```json
{
  "detail": "<error message>"
}
```

**Example (PowerShell):**
```powershell
$headers = @{ Authorization = "Bearer $token" }
curl -X POST "http://localhost:8000/api/chat?space_id=1" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  -d '{"text":"What is machine learning?","thread_id":null}'
```

**Example (JavaScript/Fetch):**
```javascript
const token = localStorage.getItem('token');
const response = await fetch('/api/chat?space_id=1', {
  method: 'POST',
  headers: { 
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    text: 'What is machine learning?',
    thread_id: null
  })
});
const data = await response.json();
```

**Notes:**
- If `thread_id` is null, a new conversation thread is created
- If `thread_id` is provided, the message is added to that thread with full conversation history
- The response includes the `thread_id` - save it to continue the conversation
- Uses authenticated user's ID automatically (no need to send user_id)
- History context is automatically included (last 5 messages) when continuing a thread
- **Branch Continuation:** When continuing a branch, pass `branch_id` query parameter to ensure correct message context isolation

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
  "parent_message_id": 42
}
```

**Request Schema:**
- `content` (string, required): The new message/query for the branch
- `parent_message_id` (int, required): The message ID to branch from

**Success Response (200):**
```json
{
  "thread_id": 1,
  "response": "Here's a simpler explanation...",
  "source": "document.pdf",
  "is_fork": true,
  "branch_id": 43
}
```

**Response Fields:**
- `thread_id` (int): The original thread ID
- `response` (string): The AI-generated answer
- `source` (string|null): Source document filename if RAG was used
- `is_fork` (boolean): Always `true` for branch creation
- `branch_id` (int): The new branch ID - **save this to continue the branch**
```

**Error Response (500):**
```json
{
  "detail": "<error message>"
}
```

**Example (PowerShell):**
```powershell
$headers = @{ Authorization = "Bearer $token" }
curl -X POST "http://localhost:8000/api/threads/5/branch?space_id=1" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  -d '{"content":"Explain this more simply","parent_message_id":42}'
```

**Notes:**
- Creates a new conversational branch from a specific message
- Useful for exploring alternative explanations or "what-if" scenarios
- The branch inherits context from the parent message's conversation path
- Uses authenticated user's ID automatically

---

## Document APIs

### GET /api/documents
Retrieve a list of all documents for a specific space.

**Endpoint:** `GET /api/documents`

**Auth Required:** Yes (Bearer token)

**Query Parameters:**
- `space_id` (int, optional, default: 1): Filter documents by space ID

**Success Response (200):**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "lecture_notes.pdf",
      "file_type": "pdf",
      "file_url": "https://rrcvxnrtjejetktzkesz.supabase.co/storage/v1/object/public/course-materials/space_1/lecture_notes.pdf",
      "uploaded_at": "2025-12-08T10:30:00"
    },
    {
      "id": 2,
      "filename": "textbook.pdf",
      "file_type": "pdf",
      "file_url": "https://rrcvxnrtjejetktzkesz.supabase.co/storage/v1/object/public/course-materials/space_1/textbook.pdf",
      "uploaded_at": "2025-12-07T14:20:00"
    }
  ]
}
```

**Error Response (500):**
```json
{
  "detail": "<error message>"
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

**Example (PowerShell):**
```powershell
$headers = @{ Authorization = "Bearer $token" }
curl "http://localhost:8000/api/documents?space_id=1" -H "Authorization: Bearer $token"
```

**Notes:**
- Returns all documents in the specified space (default space_id=1)
- `file_url` contains the Supabase public URL for the PDF
- Files are stored in Supabase storage bucket "course-materials"

---

### GET /api/documents/{doc_id}/content
Get the Supabase URL for viewing/downloading the PDF file.

**Endpoint:** `GET /api/documents/{doc_id}/content`

**Auth Required:** Yes (Bearer token)

**Path Parameters:**
- `doc_id` (int, required): The document ID

**Query Parameters:**
- `space_id` (int, optional, default: 1): The space ID

**Success Response (200):**
```json
{
  "url": "https://rrcvxnrtjejetktzkesz.supabase.co/storage/v1/object/public/course-materials/space_1/document.pdf",
  "type": "external",
  "filename": "document.pdf"
}
```

**Error Response (404):**
```json
{
  "detail": "Document not found"
}
```

**Example (PowerShell):**
```powershell
$headers = @{ Authorization = "Bearer $token" }
$response = curl "http://localhost:8000/api/documents/1/content?space_id=1" -H "Authorization: Bearer $token" | ConvertFrom-Json
# Use $response.url in an iframe or browser
```

**Example (HTML):**
```html
<!-- Embed in iframe -->
<iframe src="<Supabase URL from response>" width="100%" height="600px"></iframe>
```

**Notes:**
- Returns metadata with Supabase public URL, not the PDF file directly
- The URL can be used in iframes, browsers, or downloaded directly
- While the Supabase files are publicly accessible, this endpoint requires authentication to access

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
      "user": "John Doe",
      "created_at": "2025-12-08T09:00:00",
      "page_number": 1
    },
    {
      "id": 2,
      "title": "Questions on Section 2.3",
      "creator_user_id": 2,
      "user": "Jane Smith",
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
  "detail": "<error message>"
}
```

**Example (PowerShell):**
```powershell
$headers = @{ Authorization = "Bearer $token" }
curl "http://localhost:8000/api/threads/1" -H "Authorization: Bearer $token"
```

**Notes:**
- Returns the complete conversation tree with all messages
- Messages include path information for branching/forking
- `path` field shows the message ancestry (e.g., "1/5/20/" means message 20 is a reply to 5, which is a reply to 1)
- `branch_id` indicates which branch the message belongs to (for forked conversations)
- Each message now includes a `forks` array containing previews of any branches created from that message
- `forks` array structure: `[{branch_id, preview, created_at}, ...]`

---

### GET /api/branches/{branch_id}
Retrieve a complete branched conversation including its history and all branch messages.

**Endpoint:** `GET /api/branches/{branch_id}`

**Auth Required:** Yes (Bearer token)

**Path Parameters:**
- `branch_id` (int, required): The branch ID to retrieve

**Success Response (200):**
```json
{
  "branch_id": 5,
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
    },
    {
      "id": 10,
      "user_id": 1,
      "role": "user",
      "content": "Can you explain that differently?",
      "path": "1/2/10/",
      "parent_message_id": 2,
      "branch_id": 5,
      "created_at": "2025-12-08T09:05:00"
    },
    {
      "id": 11,
      "user_id": 1,
      "role": "assistant",
      "content": "Alternative explanation...",
      "path": "1/2/10/11/",
      "parent_message_id": 10,
      "branch_id": 5,
      "created_at": "2025-12-08T09:05:05"
    }
  ]
}
```

**Error Response (500):**
```json
{
  "detail": "<error message>"
}
```

**Example (PowerShell):**
```powershell
$headers = @{ Authorization = "Bearer $token" }
curl "http://localhost:8000/api/branches/5" -H "Authorization: Bearer $token"
```

**Notes:**
- Returns the full conversation context including history leading up to the branch
- All messages before the branch point are included for context
- Messages with matching `branch_id` are part of the branch conversation
- Useful for viewing alternative conversation paths in the Mind Map feature

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
$headers = @{ Authorization = "Bearer $token" }
curl -X POST "http://localhost:8000/api/threads/1/messages" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  -d '{"content":"Thanks for the explanation!"}'
```

**Notes:**
- Adds a message to the thread as a continuation of the last message
- Uses authenticated user's ID automatically
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
  "detail": "<error message>"
}
```

**Example (PowerShell):**
```powershell
$headers = @{ Authorization = "Bearer $token" }
curl -X POST "http://localhost:8000/api/spaces" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  -d '{"name":"CS101","description":"Algorithms course"}'
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




# RAG Study Chat API - Complete Documentation

## 📖 Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL & Headers](#base-url--headers)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [API Endpoints](#api-endpoints)
  - [Health & System](#health--system)
  - [Course Management](#course-management)
  - [Document Processing](#document-processing)
  - [Chat System](#chat-system)
  - [Cache Management](#cache-management)
- [Data Models](#data-models)
- [WebSocket Support](#websocket-support)
- [SDK Examples](#sdk-examples)

---

## Overview

The RAG Study Chat API is a comprehensive educational platform that combines:
- **Retrieval-Augmented Generation (RAG)** for intelligent document-based responses
- **Multi-session chat system** with persistent history
- **Automatic document processing** with PDF parsing and embedding generation
- **Redis caching** for optimal performance
- **PostgreSQL + pgvector** for high-performance similarity search

### Key Features
- ✅ **OpenAI Integration**: gpt-4o-mini for chat, text-embedding-3-small for embeddings
- ✅ **Intelligent PDF Processing**: LlamaParse for document extraction
- ✅ **Vector Search**: pgvector for semantic similarity
- ✅ **Session Management**: Multiple concurrent chat sessions per user
- ✅ **Automatic Indexing**: Background processing of new courses
- ✅ **Performance Caching**: Redis for API call optimization
- ✅ **Source Attribution**: Responses include document references

---

## Authentication

**Current Status**: No authentication required
**Production Recommendation**: Implement JWT or API key authentication

```http
# Future authentication header
Authorization: Bearer <your-jwt-token>
# OR
X-API-Key: <your-api-key>
```

---

## Base URL & Headers

### Base URL
```
Production: https://your-domain.com/api
Development: http://localhost:8000
```

### Required Headers
```http
Content-Type: application/json
Accept: application/json
```

### Optional Headers
```http
X-Request-ID: <unique-request-id>  # For request tracking
X-User-Agent: <your-app-name/version>  # For analytics
```

---

## Error Handling

### Standard Error Response Format
```json
{
  "detail": "Error message description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2025-01-17T10:30:00Z",
  "request_id": "req_123456789"
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Unprocessable Entity (validation error)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `503` - Service Unavailable

### Common Error Examples

#### Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["body", "course_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Rate Limit Error (429)
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

---

## Rate Limiting

### Current Limits
- **General API**: 10 requests/second per IP
- **Chat endpoints**: 5 requests/second per IP
- **Document processing**: 2 requests/minute per IP

### Rate Limit Headers
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642781234
```

---

# API Endpoints

## Health & System

### Health Check
Check API server status and dependencies.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "RAG Study Chat API is running",
  "version": "1.0.0",
  "timestamp": "2025-01-17T10:30:00Z",
  "dependencies": {
    "database": "connected",
    "redis": "connected",
    "openai": "available"
  }
}
```

---

## Course Management

### Get All Courses
Retrieve all available courses with their metadata.

```http
GET /courses
```

**Query Parameters:**
- `category` (optional): Filter by category (Math, Science, English, etc.)
- `grade` (optional): Filter by grade level
- `limit` (optional): Limit number of results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Example:**
```http
GET /courses?category=Math&grade=College&limit=20
```

**Response:**
```json
[
  {
    "id": 59,
    "grade": "College",
    "category": "Science",
    "subject": "Biochemistry"
  },
  {
    "id": 39,
    "grade": "High School",
    "category": "Science",
    "subject": "Anatomy and Physiology"
  }
]
```

### Get Course Documents
Retrieve all documents for a specific course.

```http
GET /courses/{course_id}/documents
```

**Path Parameters:**
- `course_id` (required): Course ID

**Response:**
```json
{
  "course_id": 59,
  "documents": [
    {
      "post_id": 8,
      "post_name": "Protein Structure Fundamentals",
      "doc_name": "biochemistry_chapter_3.pdf",
      "doc_url": "B4YBEVFEI3",
      "details": "Chapter 3: Protein folding and structure",
      "subject": "Biochemistry",
      "grade": "College"
    }
  ],
  "indexed_chunks": 15,
  "last_updated": "2025-01-17T09:15:00Z"
}
```

### Get Course Index Status
Check the indexing status of a course's documents.

```http
GET /courses/{course_id}/index-status
```

**Response:**
```json
{
  "course_id": 59,
  "status": "completed",
  "document_count": 3,
  "chunk_count": 45,
  "last_indexed": "2025-01-17T08:30:00Z",
  "error_message": null,
  "processing_time_seconds": 127
}
```

**Status Values:**
- `not_indexed` - Course hasn't been processed
- `pending` - Queued for processing
- `processing` - Currently being processed
- `completed` - Successfully processed
- `failed` - Processing failed

### Get Unindexed Courses
Retrieve courses that need document processing.

```http
GET /courses/unindexed
```

**Response:**
```json
{
  "unindexed_courses": [
    {
      "id": 72,
      "grade": "College",
      "category": "Science",
      "subject": "Organic Chemistry",
      "document_count": 2
    }
  ],
  "total_courses": 150,
  "indexed_courses": 148,
  "pending_courses": 2,
  "last_check": "2025-01-17T10:25:00Z"
}
```

---

## Document Processing

### Process Course Documents
Trigger document processing for a specific course.

```http
POST /courses/{course_id}/process-documents
```

**Path Parameters:**
- `course_id` (required): Course ID

**Response:**
```json
{
  "message": "Started processing 3 documents for course 59",
  "course_id": 59,
  "document_count": 3,
  "estimated_completion": "2025-01-17T10:45:00Z",
  "job_id": "job_abc123"
}
```

### Index All Unindexed Courses
Process all courses that haven't been indexed yet.

```http
POST /courses/index-unindexed
```

**Response:**
```json
{
  "message": "Started indexing 5 courses",
  "courses_to_index": 5,
  "courses": [
    {"id": 72, "subject": "Organic Chemistry"},
    {"id": 85, "subject": "World Literature"}
  ],
  "estimated_completion": "2025-01-17T11:30:00Z",
  "batch_job_id": "batch_xyz789"
}
```

---

## Chat System

### Create Chat Session
Create a new chat session for a user and course.

```http
POST /chat/sessions
```

**Request Body:**
```json
{
  "user_email": "student@university.edu",
  "course_id": 59,
  "session_name": "Biochemistry Study Session"
}
```

**Response:**
```json
{
  "id": 123,
  "user_email": "student@university.edu",
  "course_id": 59,
  "session_name": "Biochemistry Study Session",
  "created_at": "2025-01-17T10:30:00Z",
  "updated_at": "2025-01-17T10:30:00Z",
  "is_active": true,
  "message_count": 0
}
```

### Get User Sessions
Retrieve all active sessions for a user.

```http
GET /chat/sessions/{user_email}
```

**Path Parameters:**
- `user_email` (required): User's email address

**Query Parameters:**
- `active_only` (optional): Only return active sessions (default: true)
- `limit` (optional): Limit number of results (default: 50)

**Response:**
```json
[
  {
    "id": 123,
    "user_email": "student@university.edu",
    "course_id": 59,
    "session_name": "Biochemistry Study Session",
    "created_at": "2025-01-17T10:30:00Z",
    "updated_at": "2025-01-17T10:45:00Z",
    "is_active": true,
    "message_count": 8
  }
]
```

### Get Session Messages
Retrieve all messages in a chat session.

```http
GET /chat/sessions/{session_id}/messages
```

**Path Parameters:**
- `session_id` (required): Session ID

**Query Parameters:**
- `limit` (optional): Limit number of messages (default: 100)
- `offset` (optional): Pagination offset (default: 0)
- `order` (optional): Sort order - 'asc' or 'desc' (default: 'asc')

**Response:**
```json
[
  {
    "id": 456,
    "session_id": 123,
    "message_type": "user",
    "content": "What is protein folding?",
    "metadata": {},
    "timestamp": "2025-01-17T10:31:00Z"
  },
  {
    "id": 457,
    "session_id": 123,
    "message_type": "assistant",
    "content": "Protein folding is the process by which a protein chain acquires its native 3D structure...",
    "metadata": {
      "sources": [
        {
          "source_id": 1,
          "doc_name": "biochemistry_chapter_3.pdf",
          "post_name": "Protein Structure Fundamentals",
          "similarity_score": 0.89,
          "chunk_index": 5
        }
      ],
      "tokens_used": 245,
      "response_time_ms": 1250
    },
    "timestamp": "2025-01-17T10:31:15Z"
  }
]
```

### Send Message
Send a message and receive AI response.

```http
POST /chat/message
```

**Request Body:**
```json
{
  "session_id": 123,
  "content": "Can you explain the different types of protein structures?"
}
```

**Response:**
```json
{
  "message": "There are four levels of protein structure: primary, secondary, tertiary, and quaternary...",
  "sources": [
    {
      "source_id": 1,
      "doc_name": "biochemistry_chapter_3.pdf",
      "post_name": "Protein Structure Fundamentals",
      "similarity_score": 0.92,
      "chunk_index": 8,
      "page_number": 45
    },
    {
      "source_id": 2,
      "doc_name": "molecular_biology_notes.pdf",
      "post_name": "Molecular Structure Overview",
      "similarity_score": 0.85,
      "chunk_index": 12,
      "page_number": 23
    }
  ],
  "session_id": 123,
  "message_id": 458,
  "tokens_used": 312,
  "response_time_ms": 1450,
  "confidence_score": 0.88
}
```

### Update Session
Update session metadata.

```http
PUT /chat/sessions/{session_id}
```

**Request Body:**
```json
{
  "session_name": "Updated Session Name"
}
```

**Response:**
```json
{
  "id": 123,
  "session_name": "Updated Session Name",
  "updated_at": "2025-01-17T10:50:00Z"
}
```

### Delete Session
Deactivate a chat session.

```http
DELETE /chat/sessions/{session_id}
```

**Response:**
```json
{
  "message": "Session deleted successfully",
  "session_id": 123,
  "deleted_at": "2025-01-17T10:55:00Z"
}
```

---

## Cache Management

### Get Cache Statistics
Retrieve Redis cache performance metrics.

```http
GET /cache/stats
```

**Response:**
```json
{
  "cache_stats": {
    "enabled": true,
    "connected_clients": 3,
    "used_memory": "15.2MB",
    "used_memory_peak": "18.7MB",
    "total_commands_processed": 15847,
    "keyspace_hits": 12456,
    "keyspace_misses": 3391,
    "hit_rate": 78.6,
    "evicted_keys": 23,
    "expired_keys": 156
  },
  "cache_breakdown": {
    "embeddings": {
      "count": 1247,
      "memory_usage": "8.3MB",
      "hit_rate": 85.2
    },
    "courses": {
      "count": 89,
      "memory_usage": "2.1MB",
      "hit_rate": 72.4
    },
    "searches": {
      "count": 456,
      "memory_usage": "3.8MB",
      "hit_rate": 68.9
    }
  },
  "timestamp": "2025-01-17T10:30:00Z"
}
```

### Check Cache Health
Verify Redis cache functionality.

```http
GET /cache/health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "Redis cache is working properly",
  "operations_tested": ["set", "get", "delete", "expire"],
  "response_time_ms": 12,
  "last_check": "2025-01-17T10:30:00Z"
}
```

### Invalidate Course Cache
Clear all cache entries for a specific course.

```http
POST /cache/invalidate/course/{course_id}
```

**Response:**
```json
{
  "message": "Invalidated cache for course 59",
  "deleted_entries": 23,
  "course_id": 59,
  "cache_types_cleared": ["course_info", "documents", "search_results"],
  "timestamp": "2025-01-17T10:30:00Z"
}
```

### Invalidate All Cache
Clear all cache entries (admin operation).

```http
POST /cache/invalidate/all
```

**Request Body (optional):**
```json
{
  "confirm": true,
  "reason": "System maintenance"
}
```

**Response:**
```json
{
  "message": "Invalidated all cache entries",
  "deleted_entries": 2847,
  "memory_freed": "15.2MB",
  "timestamp": "2025-01-17T10:30:00Z"
}
```

### Get Cache Keys
List cache keys by pattern (admin operation).

```http
GET /cache/keys?pattern=course:*&limit=100
```

**Response:**
```json
{
  "keys": [
    "course:59",
    "course:72",
    "course_docs:59"
  ],
  "total_count": 156,
  "pattern": "course:*",
  "limit": 100
}
```

---

## Data Models

### Course Model
```json
{
  "id": 59,
  "grade": "College",
  "category": "Science",
  "subject": "Biochemistry"
}
```

### Document Model
```json
{
  "post_id": 8,
  "post_name": "Protein Structure Fundamentals",
  "doc_name": "biochemistry_chapter_3.pdf",
  "doc_url": "B4YBEVFEI3",
  "details": "Chapter 3: Protein folding and structure",
  "subject": "Biochemistry",
  "grade": "College"
}
```

### Chat Session Model
```json
{
  "id": 123,
  "user_email": "student@university.edu",
  "course_id": 59,
  "session_name": "Biochemistry Study Session",
  "created_at": "2025-01-17T10:30:00Z",
  "updated_at": "2025-01-17T10:45:00Z",
  "is_active": true,
  "message_count": 8
}
```

### Chat Message Model
```json
{
  "id": 456,
  "session_id": 123,
  "message_type": "user|assistant",
  "content": "Message content",
  "metadata": {
    "sources": [...],
    "tokens_used": 245,
    "response_time_ms": 1250
  },
  "timestamp": "2025-01-17T10:31:00Z"
}
```

### Source Reference Model
```json
{
  "source_id": 1,
  "doc_name": "biochemistry_chapter_3.pdf",
  "post_name": "Protein Structure Fundamentals",
  "similarity_score": 0.89,
  "chunk_index": 5,
  "page_number": 45
}
```

---

## WebSocket Support

### Real-time Chat (Future Feature)
```javascript
// WebSocket connection for real-time chat
const ws = new WebSocket('ws://localhost:8000/ws/chat/123');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  if (data.type === 'message') {
    // Handle new message
  } else if (data.type === 'typing') {
    // Handle typing indicator
  }
};

// Send message
ws.send(JSON.stringify({
  type: 'message',
  content: 'What is protein folding?'
}));
```

---

## SDK Examples

### Python SDK Example
```python
import requests

class RAGChatClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def create_chat_session(self, user_email, course_id, session_name):
        response = self.session.post(f"{self.base_url}/chat/sessions", json={
            "user_email": user_email,
            "course_id": course_id,
            "session_name": session_name
        })
        return response.json()
    
    def send_message(self, session_id, message):
        response = self.session.post(f"{self.base_url}/chat/message", json={
            "session_id": session_id,
            "content": message
        })
        return response.json()

# Usage
client = RAGChatClient()
session = client.create_chat_session("student@edu.com", 59, "Study Session")
response = client.send_message(session["id"], "What is protein folding?")
print(response["message"])
```

### JavaScript SDK Example
```javascript
class RAGChatClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async createChatSession(userEmail, courseId, sessionName) {
    const response = await fetch(`${this.baseUrl}/chat/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_email: userEmail,
        course_id: courseId,
        session_name: sessionName
      })
    });
    return response.json();
  }

  async sendMessage(sessionId, message) {
    const response = await fetch(`${this.baseUrl}/chat/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        content: message
      })
    });
    return response.json();
  }
}

// Usage
const client = new RAGChatClient();
const session = await client.createChatSession('student@edu.com', 59, 'Study Session');
const response = await client.sendMessage(session.id, 'What is protein folding?');
console.log(response.message);
```

### cURL Examples

#### Create Chat Session
```bash
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "student@university.edu",
    "course_id": 59,
    "session_name": "Biochemistry Study Session"
  }'
```

#### Send Message
```bash
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 123,
    "content": "What is protein folding?"
  }'
```

#### Get Cache Stats
```bash
curl -X GET http://localhost:8000/cache/stats \
  -H "Accept: application/json"
```

---

## Performance Guidelines

### Best Practices
1. **Use appropriate TTL values** for different data types
2. **Implement client-side caching** for frequently accessed data
3. **Batch requests** when possible to reduce API calls
4. **Monitor cache hit rates** and adjust caching strategy
5. **Use pagination** for large result sets

### Rate Limiting Guidelines
- **Respect rate limits** and implement exponential backoff
- **Cache responses** on the client side when appropriate
- **Use WebSocket connections** for real-time features (when available)

### Error Handling Best Practices
- **Always check HTTP status codes**
- **Implement retry logic** with exponential backoff
- **Handle network timeouts** gracefully
- **Log errors** for debugging and monitoring

---

## Support & Resources

### Documentation
- [API Documentation](API_DOCUMENTATION.md)
- [Deployment Guide](DOCKER_DEPLOYMENT.md)
- [README](README.md)

### Testing
- Use `test_client.py` for comprehensive API testing
- Use `example_client.py` for basic usage examples

### Monitoring
- Monitor cache hit rates via `/cache/stats`
- Check system health via `/health`
- Track API usage and performance metrics

---

*Last Updated: January 17, 2025*
*API Version: 1.0.0*
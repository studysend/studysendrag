
## Chat System

### Getting Started: Document-Based Conversations

To start a conversation with any document, follow this workflow:

1. **Find Available Documents**: Use `/courses` to discover courses and their documents
2. **Select a Document**: Choose a `post_id` from the course documents
3. **Create Session**: Create a chat session using the `post_id`
4. **Start Chatting**: Send messages to analyze the document content

### Step 1: Discover Available Documents

First, get all courses to see available documents:

```http
GET /courses
```

Then get documents for a specific course:

```http
GET /courses/{course_id}/documents
```

**Example Response:**
```json
{
  "course_id": 178,
  "documents": [
    {
      "post_id": 9,
      "post_name": "RAG applications and its workings",
      "doc_name": "2312.pdf",
      "doc_url": "icWKallq8o",
      "details": "This is the new document",
      "subject": "AP Computer Science A",
      "grade": "High School - AP"
    },
    {
      "post_id": 24,
      "post_name": "Dynamic ABC algorithm",
      "doc_name": "Dynamic_Power_System_Security_Analysis_U.pdf",
      "doc_url": "4k56hPIi3y",
      "details": "a novel hybrid particle swarm optimization and artificial physics optimization (HPSO-APO) algorithm",
      "subject": "AP Computer Science A",
      "grade": "High School - AP"
    }
  ],
  "indexed_chunks": 414
}
```

### Step 2: Create Chat Session
Create a new chat session for a specific document using its `post_id`. The system supports universal document analysis for ANY type of content.

```http
POST /chat/sessions
```

**Request Body:**
```json
{
  "user_email": "student@university.edu",
  "post_id": 9,
  "session_name": "RAG Research Analysis"
}
```

**Path Parameters:**
- `post_id` (required): The ID of the document/post you want to analyze

**Required Fields:**
- `user_email`: User identifier for session tracking
- `post_id`: Document identifier (obtained from `/courses/{course_id}/documents`)
- `session_name`: Descriptive name for the conversation

**Response:**
```json
{
  "id": 152,
  "user_email": "student@university.edu",
  "course_id": 178,
  "post_id": 9,
  "session_name": "RAG Research Analysis",
  "created_at": "2025-08-18T21:27:26.948511",
  "updated_at": "2025-08-18T21:27:26.948521",
  "is_active": true
}
```

**Note:** The `course_id` is automatically determined from the `post_id` during session creation.
```

### Step 3: Send Messages
Send messages to analyze the document content. The system now provides comprehensive analysis for ANY type of PDF without subject restrictions.

```http
POST /chat/message
```

**Request Body:**
```json
{
  "session_id": 152,
  "content": "What is this document about? Can you analyze this PDF for me?"
}
```

**Required Fields:**
- `session_id`: The session ID returned from session creation
- `content`: Your question or request about the document

**Response Format:**
```json
{
  "message": "Based on the document content, this is a comprehensive research paper about Retrieval-Augmented Generation (RAG) techniques...",
  "sources": [
    {
      "source_id": 1,
      "doc_name": "2312.pdf",
      "post_name": "RAG applications and its workings",
      "post_id": 9,
      "similarity_score": 0.6524331349779869
    },
    {
      "source_id": 2,
      "doc_name": "2312.pdf", 
      "post_name": "RAG applications and its workings",
      "post_id": 9,
      "similarity_score": 0.6524180381049
    }
  ],
  "session_id": 152,
  "message_id": 278
}
```

**Key Features:**
- **Universal Content Support**: Analyzes ANY type of PDF content
- **Source Attribution**: Returns specific document chunks that informed the response
- **Similarity Scores**: Shows how relevant each source is to your query
- **Comprehensive Analysis**: Provides detailed explanations regardless of document type

### Complete Workflow Example

Here's a complete example of starting a conversation and analyzing a document:

```bash
# Step 1: Get available courses
curl -X GET http://localhost:8000/courses

# Step 2: Get documents for a specific course
curl -X GET http://localhost:8000/courses/178/documents

# Step 3: Create a chat session with a specific document
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "analyst@company.com",
    "post_id": 9,
    "session_name": "RAG Research Analysis"
  }'

# Step 4: Send your first message
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 152,
    "content": "What is retrieval-augmented generation and how does it work?"
  }'

# Step 5: Continue the conversation
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 152, 
    "content": "What are the main benefits and applications mentioned in this paper?"
  }'
```

### Document Analysis Capabilities

The system can analyze and provide insights for:

| Document Type | Example Questions | Response Quality |
|---------------|-------------------|------------------|
| **Research Papers** | "What are the key findings?", "Explain the methodology" | Detailed analysis of research contributions, methods, and conclusions |
| **Technical Reports** | "What are the technical specifications?", "Explain the implementation" | Clear breakdown of technical concepts and requirements |
| **Resumes/CVs** | "What are the key qualifications?", "Summarize the experience" | Structured analysis of skills, experience, and achievements |
| **Business Documents** | "What are the main recommendations?", "Summarize the strategy" | Executive-level insights and strategic analysis |
| **Academic Materials** | "Explain the key concepts", "What should I focus on?" | Educational explanations appropriate for the target audience |
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
    "id": 152,
    "user_email": "student@university.edu",
    "course_id": 178,
    "post_id": 9,
    "session_name": "RAG Research Analysis",
    "created_at": "2025-08-18T21:27:26.948511",
    "updated_at": "2025-08-18T21:30:00.000000",
    "is_active": true
  },
  {
    "id": 153,
    "user_email": "student@university.edu", 
    "course_id": 59,
    "post_id": 8,
    "session_name": "Resume Analysis",
    "created_at": "2025-08-18T21:30:07.991196",
    "updated_at": "2025-08-18T21:35:00.000000",
    "is_active": true
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

### Send Message (Chat with Documents)
Send a message to analyze and discuss the document content. The system provides comprehensive responses with source attribution for ANY type of document.

```http
POST /chat/message
```

**Request Body:**
```json
{
  "session_id": 152,
  "content": "What is retrieval-augmented generation and how does it work?"
}
```

**Required Fields:**
- `session_id` (integer): The session ID from session creation
- `content` (string): Your question or message about the document

**Response:**
```json
{
  "message": "**Retrieval-Augmented Generation (RAG): Overview and Mechanism**\n\n**Definition:**\nRetrieval-Augmented Generation (RAG) is a hybrid approach that combines two major components: information retrieval and text generation. It enhances the capabilities of large language models (LLMs) by allowing them to access external knowledge sources when generating responses...",
  "sources": [
    {
      "source_id": 1,
      "doc_name": "2312.pdf",
      "post_name": "RAG applications and its workings",
      "post_id": 9,
      "similarity_score": 0.6524331349779869
    },
    {
      "source_id": 2,
      "doc_name": "2312.pdf",
      "post_name": "RAG applications and its workings", 
      "post_id": 9,
      "similarity_score": 0.6524180381049
    },
    {
      "source_id": 3,
      "doc_name": "2312.pdf",
      "post_name": "RAG applications and its workings",
      "post_id": 9,
      "similarity_score": 0.642144658693354
    }
  ],
  "session_id": 152,
  "message_id": 278
}
```

**Response Fields:**
- `message`: The AI's comprehensive response about the document
- `sources`: Array of document chunks that informed the response
- `session_id`: The session ID for continued conversation
- `message_id`: Unique identifier for this response

**Source Object Fields:**
- `source_id`: Sequential ID for this source in the response
- `doc_name`: Name of the PDF file
- `post_name`: Title/name of the document post
- `post_id`: Document identifier
- `similarity_score`: Relevance score (0.0 to 1.0, higher = more relevant)
```

### Send Streaming Message (Real-time Chat)
Send a message and receive a streaming response for real-time chat experience. The response is delivered in chunks as it's generated.

```http
POST /chat/message/stream
```

**Request Body:**
```json
{
  "session_id": 152,
  "content": "What is retrieval-augmented generation and how does it work?"
}
```

**Response Format:**
The response is delivered as Server-Sent Events (SSE) with `Content-Type: text/event-stream`. Each chunk is prefixed with `data: ` and contains a JSON object.

**Streaming Response Chunks:**
```
data: {"content": "**Retrieval", "sources": [...], "session_id": 152, "done": false}

data: {"content": "-Augmented Generation", "sources": [...], "session_id": 152, "done": false}

data: {"content": " (RAG):** is a", "sources": [...], "session_id": 152, "done": false}

data: {"content": "", "message": "Complete response text...", "sources": [...], "session_id": 152, "message_id": 279, "done": true}
```

**Chunk Object Fields:**
- `content`: Partial text content for this chunk (empty in final chunk)
- `message`: Complete response text (only in final chunk when `done: true`)
- `sources`: Array of document chunks that informed the response
- `session_id`: The session ID for continued conversation
- `message_id`: Unique identifier for this response (only in final chunk)
- `done`: Boolean indicating if this is the final chunk

**JavaScript Example:**
```javascript
async function streamChat(sessionId, message) {
  const response = await fetch('/chat/message/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      content: message
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let fullResponse = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.content) {
          fullResponse += data.content;
          console.log('Streaming:', data.content);
        }
        
        if (data.done) {
          console.log('Complete response:', data.message);
          console.log('Sources:', data.sources);
          return data;
        }
      }
    }
  }
}
```

**curl Example:**
```bash
curl -X POST http://localhost:8000/chat/message/stream \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 152,
    "content": "What is retrieval-augmented generation?"
  }' \
  --no-buffer
```

### Document Summary Feature
The system automatically detects summary requests and provides comprehensive document analysis for ANY type of PDF content.

#### Trigger Keywords
The following phrases will trigger automatic document summary generation:
- "summary", "summarize", "summarise", "overview"
- "what is this document about", "document summary"
- "tell me about the document", "what does this document say"
- "main points", "key points", "document overview"
- "brief", "explain the document"
- "give me an overview", "what are the main points"
- "key concepts", "important points"
- "document content", "what's in this document"
- "describe the document"

#### Summary Request Example

**Request:**
```json
{
  "session_id": 123,
  "content": "Can you provide a comprehensive summary of this document?"
}
```

**Response:**
```json
{
  "message": "\n\n==================================================**Document: research_paper.pdf**\n\nThis document provides a comprehensive overview of Retrieval-Augmented Generation (RAG) techniques...\n\n**Key Concepts:**\n1. Main topic and purpose\n2. Key findings and conclusions\n3. Practical applications\n4. Technical methodologies\n\n**Important Findings:**\n- Detailed analysis of the document's core concepts\n- Significance of the research or content\n- Practical implications and applications\n\n**Conclusions:**\n- Summary of main takeaways\n- Recommendations or future directions\n- Overall impact and relevance",
  "sources": [],
  "session_id": 123,
  "message_id": 459,
  "type": "summary"
}
```

#### Supported Document Types
The system now handles ANY type of PDF content without subject restrictions:

- **Academic Papers**: Research papers, journals, conference proceedings
- **Technical Documents**: Reports, specifications, manuals
- **Business Documents**: Resumes, CVs, proposals, presentations  
- **Educational Content**: Textbooks, study materials, lecture notes
- **Legal Documents**: Contracts, policies, regulations
- **Financial Reports**: Annual reports, financial statements
- **Medical Documents**: Research papers, clinical studies
- **Engineering Documents**: Design specifications, technical guides
- **Any Other PDF**: The system will analyze and summarize any PDF content
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

### Troubleshooting Chat Issues

#### Empty Sources Array
If you're getting responses but the `sources` array is empty:

1. **Check Document Indexing**: Verify the document has been processed
   ```bash
   curl -X GET http://localhost:8000/courses/{course_id}/documents
   ```
   Look for `indexed_chunks > 0`

2. **Verify Post ID**: Ensure you're using a `post_id` that has indexed chunks
   ```bash
   # Check which posts have chunks in the database
   curl -X GET http://localhost:8000/courses/{course_id}/index-status
   ```

3. **Check Similarity Threshold**: The system filters chunks by similarity score (>0.3). Very generic questions might not find relevant chunks.

#### No Response from Documents
If the AI isn't using document content:

1. **Verify Session Creation**: Ensure the session was created with a valid `post_id`
2. **Check Document Processing**: Some documents may not be fully processed yet
3. **Try Specific Questions**: Ask about specific topics mentioned in the document

#### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Wrong Post ID** | Generic responses, no sources | Use `/courses/{course_id}/documents` to find valid post IDs |
| **Unprocessed Document** | `indexed_chunks: 0` | Wait for processing or trigger `/courses/{course_id}/process-documents` |
| **Generic Questions** | No sources found | Ask specific questions about document content |
| **Session Mix-up** | Wrong document context | Verify session was created with correct `post_id` |

#### Example: Finding Documents with Content

```bash
# 1. Get all courses
curl -X GET http://localhost:8000/courses

# 2. Check documents for a course  
curl -X GET http://localhost:8000/courses/178/documents

# 3. Look for posts with indexed_chunks > 0
# Example response:
{
  "course_id": 178,
  "documents": [
    {
      "post_id": 9,
      "post_name": "RAG applications and its workings",
      "doc_name": "2312.pdf"
    }
  ],
  "indexed_chunks": 414  // This indicates successful processing
}

# 4. Create session with a post_id that has chunks
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "test@example.com",
    "post_id": 9,
    "session_name": "Document Analysis"
  }'
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
    
    def create_chat_session(self, user_email, post_id, session_name):
        response = self.session.post(f"{self.base_url}/chat/sessions", json={
            "user_email": user_email,
            "post_id": post_id,
            "session_name": session_name
        })
        return response.json()
    
    def send_message(self, session_id, message):
        response = self.session.post(f"{self.base_url}/chat/message", json={
            "session_id": session_id,
            "content": message
        })
        return response.json()
    
    def request_document_summary(self, session_id):
        """Request a comprehensive document summary"""
        return self.send_message(session_id, "Can you provide a comprehensive summary of this document?")

### Python SDK Example
```python
import requests

class RAGChatClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_courses(self):
        """Get all available courses"""
        response = self.session.get(f"{self.base_url}/courses")
        return response.json()
    
    def get_course_documents(self, course_id):
        """Get documents for a specific course"""
        response = self.session.get(f"{self.base_url}/courses/{course_id}/documents")
        return response.json()
    
    def create_chat_session(self, user_email, post_id, session_name):
        """Create a new chat session for a specific document"""
        response = self.session.post(f"{self.base_url}/chat/sessions", json={
            "user_email": user_email,
            "post_id": post_id,
            "session_name": session_name
        })
        return response.json()
    
    def send_message(self, session_id, message):
        """Send a message and get AI response with sources"""
        response = self.session.post(f"{self.base_url}/chat/message", json={
            "session_id": session_id,
            "content": message
        })
        return response.json()
    
    def request_document_summary(self, session_id):
        """Request a comprehensive document summary"""
        return self.send_message(session_id, "Can you provide a comprehensive summary of this document?")
    
    def find_documents_with_content(self):
        """Find courses and documents that have been processed and have content"""
        courses = self.get_courses()
        available_docs = []
        
        for course in courses:
            docs = self.get_course_documents(course['id'])
            if docs.get('indexed_chunks', 0) > 0:
                available_docs.append({
                    'course_id': course['id'],
                    'course_subject': course['subject'],
                    'documents': docs['documents'],
                    'indexed_chunks': docs['indexed_chunks']
                })
        
        return available_docs

# Complete Workflow Examples

client = RAGChatClient()

# 1. Discover available documents
print("Finding documents with content...")
available_docs = client.find_documents_with_content()
for course_info in available_docs:
    print(f"Course: {course_info['course_subject']} ({course_info['indexed_chunks']} chunks)")
    for doc in course_info['documents']:
        print(f"  - Post {doc['post_id']}: {doc['post_name']} ({doc['doc_name']})")

# 2. Analyze a specific document (using post_id 9 from our testing)
print("\n--- Analyzing RAG Research Paper ---")
session = client.create_chat_session("researcher@university.edu", 9, "RAG Research Analysis")
print(f"Created session {session['id']} for post {session['post_id']}")

# Get document summary
summary = client.request_document_summary(session["id"])
print("Document Summary:")
print(summary["message"])
print(f"Sources used: {len(summary.get('sources', []))}")

# Ask specific questions
rag_question = client.send_message(session["id"], "What is retrieval-augmented generation and how does it work?")
print("\nRAG Explanation:")
print(rag_question["message"])
print(f"Sources: {len(rag_question.get('sources', []))}")

# 3. Analyze a resume (using post_id 8 from our testing)
print("\n--- Analyzing Resume ---")
resume_session = client.create_chat_session("hr@company.com", 8, "Resume Review")
qualifications = client.send_message(resume_session["id"], "What are the key qualifications and experience in this resume?")
print("Key Qualifications:")
print(qualifications["message"])
print(f"Sources: {len(qualifications.get('sources', []))}")

# 4. Technical document analysis
print("\n--- Technical Analysis ---")
tech_session = client.create_chat_session("engineer@company.com", 24, "Technical Analysis")
concepts = client.send_message(tech_session["id"], "Explain the main technical concepts in this document")
print("Technical Concepts:")
print(concepts["message"])
```
```

### JavaScript SDK Example
```javascript
class RAGChatClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async createChatSession(userEmail, postId, sessionName) {
    const response = await fetch(`${this.baseUrl}/chat/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_email: userEmail,
        post_id: postId,
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

  async requestDocumentSummary(sessionId) {
    return this.sendMessage(sessionId, 'Can you provide a comprehensive summary of this document?');
  }
}

// Usage Examples

// 1. Universal document analysis
const client = new RAGChatClient();

// Analyze any type of document
const session = await client.createChatSession('analyst@company.com', 7, 'Document Analysis');

// Get comprehensive summary
const summary = await client.requestDocumentSummary(session.id);
console.log('Document Summary:', summary.message);

// Ask specific questions
const details = await client.sendMessage(session.id, 'What are the key findings and recommendations?');
console.log('Key Details:', details.message);

// 2. Resume analysis workflow
const resumeSession = await client.createChatSession('hr@company.com', 8, 'Resume Review');
const qualifications = await client.sendMessage(resumeSession.id, 'What are the candidate\'s key qualifications?');
const experience = await client.sendMessage(resumeSession.id, 'Summarize their work experience');
console.log('Qualifications:', qualifications.message);
console.log('Experience:', experience.message);
```
```

### cURL Examples

#### Complete Document Analysis Workflow

```bash
# Step 1: Discover available courses
curl -X GET http://localhost:8000/courses

# Step 2: Get documents for a specific course (e.g., course 178)
curl -X GET http://localhost:8000/courses/178/documents

# Example response:
# {
#   "course_id": 178,
#   "documents": [
#     {
#       "post_id": 9,
#       "post_name": "RAG applications and its workings", 
#       "doc_name": "2312.pdf",
#       "doc_url": "icWKallq8o"
#     }
#   ],
#   "indexed_chunks": 414
# }

# Step 3: Create chat session with a post_id that has indexed chunks
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "analyst@company.com",
    "post_id": 9,
    "session_name": "RAG Research Analysis"
  }'

# Response will include session_id (e.g., 152)

# Step 4: Request comprehensive document summary
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 152,
    "content": "Can you provide a comprehensive summary of this document?"
  }'

# Step 5: Ask specific questions about the document
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 152,
    "content": "What is retrieval-augmented generation and how does it work?"
  }'
```

#### Analyze Different Document Types

```bash
# Resume/CV Analysis (using post_id 8)
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "hr@company.com",
    "post_id": 8,
    "session_name": "Resume Review"
  }'

curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 153,
    "content": "What are the key qualifications and experience mentioned in this resume?"
  }'

# Technical Document Analysis
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 152,
    "content": "Explain the technical specifications and main concepts in this document"
  }'

# Business Report Analysis
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 152,
    "content": "What are the main business insights and recommendations in this document?"
  }'
```

#### Session Management

```bash
# Get all sessions for a user
curl -X GET http://localhost:8000/chat/sessions/analyst@company.com

# Get all messages in a session
curl -X GET http://localhost:8000/chat/sessions/152/messages

# Update session name
curl -X PUT http://localhost:8000/chat/sessions/152 \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "Updated Session Name"
  }'

# Delete session
curl -X DELETE http://localhost:8000/chat/sessions/152
```

#### System Health and Monitoring

```bash
# Check API health
curl -X GET http://localhost:8000/health

# Get cache statistics
curl -X GET http://localhost:8000/cache/stats

# Check cache health
curl -X GET http://localhost:8000/cache/health

# Get course index status
curl -X GET http://localhost:8000/courses/178/index-status
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

## Recent Updates & Features

### 🆕 Universal Document Support & Source Attribution Fix (Latest - August 2025)
**Major Enhancement**: The API now supports comprehensive analysis of ANY type of PDF content with proper source attribution.

#### What Changed:
- ✅ **Removed Subject Filtering**: No longer restricted to specific academic subjects
- ✅ **Fixed Source Attribution**: Resolved issue where sources array was empty despite relevant content
- ✅ **Universal Content Analysis**: Handles academic papers, resumes, technical docs, business reports, etc.
- ✅ **Enhanced Document Summaries**: Automatic comprehensive summaries for any document type  
- ✅ **Post-Based Sessions**: Sessions now use `post_id` instead of `course_id` for better document association
- ✅ **Intelligent Content Recognition**: Adapts responses based on document type and content
- ✅ **Improved Filtering Logic**: Removed restrictive content filtering that was blocking relevant research terms

#### Key Bug Fixes:
- **Empty Sources Issue**: Fixed filtering logic that was excluding chunks containing research-related terms
- **Zero Indexed Chunks**: Added troubleshooting guide to identify documents with processed content
- **Content Filtering**: Removed subject-based restrictions that were blocking analysis of certain document types
- **Post ID Validation**: Added guidance on finding valid post IDs with indexed content

#### Technical Improvements:
- **Similarity Threshold**: Simplified filtering to use only similarity scores (>0.3) without content restrictions
- **Source Response Format**: Standardized source object format with `similarity_score`, `post_id`, and metadata
- **Error Diagnosis**: Added troubleshooting steps for common issues (empty sources, unprocessed documents)

#### Key Benefits:
- **Broader Use Cases**: Analyze any PDF content without restrictions
- **Better User Experience**: No more content refusals based on subject matter
- **Reliable Source Attribution**: Consistent source references in responses
- **Enhanced Flexibility**: Same API works for academic, business, technical, and personal documents
- **Improved Accuracy**: More relevant responses for diverse content types

#### Working Examples:
Successfully tested with:
- **Research Papers**: RAG survey paper analysis with 5 sources (similarity scores 0.62-0.65)
- **Resume Analysis**: Comprehensive CV analysis with 4 sources (similarity scores 0.30-0.32)  
- **Technical Documents**: Power system optimization papers
- **Any PDF Content**: Universal support confirmed across document types

#### Migration Guide:
If you're using the previous version:
1. **Session Creation**: Use `post_id` instead of `course_id` in session creation requests
2. **Document Discovery**: Use `/courses/{course_id}/documents` to find valid post IDs with `indexed_chunks > 0`
3. **Content Expectations**: Expect comprehensive analysis for any document type with proper source attribution
4. **Summary Requests**: Use trigger keywords to get automatic document summaries
5. **Response Handling**: Responses now consistently include source references when available

#### Example Comparison:

**Before** (Subject-Restricted/No Sources):
```json
{
  "message": "I'm sorry, but I cannot provide a summary of this document as it doesn't relate to [specific subject]...",
  "sources": []
}
```

**After** (Universal Support with Sources):
```json
{
  "message": "**Retrieval-Augmented Generation (RAG): Overview and Mechanism**\n\n**Definition:**\nRetrieval-Augmented Generation (RAG) is a hybrid approach that combines information retrieval and text generation...",
  "sources": [
    {
      "source_id": 1,
      "doc_name": "2312.pdf",
      "post_name": "RAG applications and its workings",
      "post_id": 9,
      "similarity_score": 0.6524331349779869
    }
  ]
}
```

---

## Document Indexing API

The system provides both course-level and post-level indexing capabilities for processing documents into searchable chunks.

### Post-Level Indexing

Process and index individual documents using their post ID for more granular control.

#### Process Single Document

```http
POST /posts/{post_id}/process-document
```

Processes and indexes a specific document for the given post ID.

**Example Request:**
```bash
curl -X POST http://localhost:8000/posts/9/process-document
```

**Example Response:**
```json
{
  "message": "Successfully processed document for post 9",
  "post_id": 9,
  "post_name": "RAG applications and its workings",
  "doc_name": "2312.pdf",
  "chunks_created": 52,
  "status": "completed"
}
```

**Error Responses:**
- `404`: Post not found
- `400`: Post has no document to process
- `500`: Processing failed

#### Check Post Index Status

```http
GET /posts/{post_id}/index-status
```

Get the indexing status and information for a specific post.

**Example Request:**
```bash
curl -X GET http://localhost:8000/posts/9/index-status
```

**Example Response:**
```json
{
  "post_id": 9,
  "post_name": "RAG applications and its workings",
  "doc_name": "2312.pdf",
  "doc_url": "icWKallq8o",
  "course_id": 178,
  "subject": "AP Computer Science A",
  "status": "indexed",
  "chunks_count": 52,
  "is_indexed": true,
  "has_document": true
}
```

**Status Values:**
- `indexed`: Document is processed and available for search
- `not_indexed`: Document exists but hasn't been processed
- `no_document`: Post has no associated document

### Course-Level Indexing

Process all documents in a course at once.

#### Process Course Documents

```http
POST /courses/{course_id}/process-documents
```

#### Check Course Index Status

```http
GET /courses/{course_id}/index-status
```

### Indexing Workflow Examples

#### Index a Specific Document

```bash
# 1. Check if document needs indexing
curl -X GET http://localhost:8000/posts/9/index-status

# 2. Process the document if not indexed
curl -X POST http://localhost:8000/posts/9/process-document

# 3. Verify indexing completed
curl -X GET http://localhost:8000/posts/9/index-status
```

#### Index Multiple Documents

```bash
# Option 1: Index entire course
curl -X POST http://localhost:8000/courses/178/process-documents

# Option 2: Index specific posts
curl -X POST http://localhost:8000/posts/9/process-document
curl -X POST http://localhost:8000/posts/24/process-document
curl -X POST http://localhost:8000/posts/8/process-document
```

### Integration with Chat System

The indexing system integrates seamlessly with the chat functionality:

```bash
# 1. Index a document
curl -X POST http://localhost:8000/posts/9/process-document

# 2. Verify indexing
curl -X GET http://localhost:8000/posts/9/index-status

# 3. Create chat session with the indexed document
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "test@example.com",
    "post_id": 9,
    "session_name": "Discuss RAG Implementation"
  }'

# 4. Start chatting about the document
curl -X POST http://localhost:8000/chat/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What are the key components of RAG?"
  }'
```

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

*Last Updated: August 29, 2025*
*API Version: 1.1.0*
# RAG Study Chat API

A comprehensive **Retrieval-Augmented Generation (RAG)** system for educational content with intelligent chat support, session management, and automatic document indexing.

## 🎯 **What This System Does**

Transform your educational documents into an **intelligent tutoring system** that:
- 📚 **Processes PDF course materials** automatically using LlamaParse
- 🧠 **Generates embeddings** with OpenAI's text-embedding-3-small
- 💬 **Provides contextual answers** using gpt-4o-mini with document context
- 🔍 **Performs semantic search** through course materials using pgvector
- ⚡ **Caches intelligently** with Redis for optimal performance
- 📊 **Tracks conversations** with persistent session management

## 🚀 **Quick Demo**

```bash
# 1. Start the system
./deploy.sh prod

# 2. Create a chat session
curl -X POST http://localhost:8000/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_email": "student@edu.com", "course_id": 59, "session_name": "Study Session"}'

# 3. Ask questions about course materials
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "content": "Explain protein folding from the course materials"}'

# Get intelligent responses with source citations! 🎉
```

## 🏗️ Architecture Overview

### Core Components
- **FastAPI Backend** - RESTful API with async support
- **PostgreSQL + pgvector** - Vector database for embeddings
- **OpenAI Integration** - text-embedding-3-small for embeddings, GPT-4o-mini for chat
- **LlamaParse** - Intelligent PDF processing
- **AWS S3** - Document storage
- **Automatic Indexing** - Periodic course document processing

### Key Features
- ✅ **Session-based Chat System** - Multiple chat sessions per user/course
- ✅ **RAG Implementation** - Context-aware responses using course documents
- ✅ **Automatic Document Processing** - PDF parsing and embedding generation
- ✅ **Periodic Indexing** - Every 5 minutes check for new courses
- ✅ **pgvector Integration** - High-performance similarity search
- ✅ **Source Attribution** - Responses include document sources

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL with pgvector extension
- OpenAI API key
- LlamaParse API key
- AWS S3 credentials

### Installation

1. **Clone and install dependencies:**
```bash
git clone <repository>
cd rag_study_chat
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

3. **Run the server:**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## 📋 API Documentation

### 📖 Complete API Reference
For detailed API documentation with examples, data models, and advanced features, see:
**[📚 Complete API Documentation](API_DOCUMENTATION.md)**

### Base URL
```
Production: https://your-domain.com/api
Development: http://localhost:8000
```

### Authentication
Currently no authentication required (add as needed for production)

---

## 🎯 Core Endpoints (Quick Reference)

### Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "message": "RAG Study Chat API is running"
}
```

---

## 📚 Course Management

### Get All Courses
```http
GET /courses
```
**Response:**
```json
[
  {
    "id": 1,
    "grade": "High School",
    "category": "Math",
    "subject": "Algebra II"
  }
]
```

### Get Course Documents
```http
GET /courses/{course_id}/documents
```
**Response:**
```json
{
  "course_id": 59,
  "documents": [
    {
      "post_id": 8,
      "post_name": "Test",
      "doc_name": "resume updated.pdf",
      "doc_url": "B4YBEVFEI3",
      "details": "Course material",
      "subject": "Biochemistry",
      "grade": "College"
    }
  ],
  "indexed_chunks": 15
}
```

### Get Unindexed Courses
```http
GET /courses/unindexed
```
**Response:**
```json
{
  "unindexed_courses": [
    {
      "id": 59,
      "grade": "College",
      "category": "Science",
      "subject": "Biochemistry",
      "document_count": 1
    }
  ],
  "total_courses": 10,
  "indexed_courses": 9,
  "pending_courses": 1
}
```

### Get Course Index Status
```http
GET /courses/{course_id}/index-status
```
**Response:**
```json
{
  "course_id": 59,
  "status": "completed",
  "document_count": 1,
  "chunk_count": 15,
  "last_indexed": "2025-01-17T10:30:00Z",
  "error_message": null
}
```

### Process Course Documents
```http
POST /courses/{course_id}/process-documents
```
**Response:**
```json
{
  "message": "Started processing 1 documents for course 59",
  "course_id": 59,
  "document_count": 1
}
```

### Index Unindexed Courses
```http
POST /courses/index-unindexed
```
**Response:**
```json
{
  "message": "Started indexing 3 courses",
  "courses_to_index": 3,
  "courses": [
    {"id": 59, "subject": "Biochemistry"},
    {"id": 39, "subject": "Anatomy and Physiology"}
  ]
}
```

---

## 💬 Chat System

### Create Chat Session
```http
POST /chat/sessions
Content-Type: application/json

{
  "user_email": "student@example.com",
  "course_id": 59,
  "session_name": "Biochemistry Study Session"
}
```
**Response:**
```json
{
  "id": 1,
  "user_email": "student@example.com",
  "course_id": 59,
  "session_name": "Biochemistry Study Session",
  "created_at": "2025-01-17T10:30:00Z",
  "updated_at": "2025-01-17T10:30:00Z",
  "is_active": true
}
```

### Get User Sessions
```http
GET /chat/sessions/{user_email}
```
**Response:**
```json
[
  {
    "id": 1,
    "user_email": "student@example.com",
    "course_id": 59,
    "session_name": "Biochemistry Study Session",
    "created_at": "2025-01-17T10:30:00Z",
    "updated_at": "2025-01-17T10:30:00Z",
    "is_active": true
  }
]
```

### Get Session Messages
```http
GET /chat/sessions/{session_id}/messages
```
**Response:**
```json
[
  {
    "id": 1,
    "session_id": 1,
    "message_type": "user",
    "content": "What is protein folding?",
    "metadata": {},
    "timestamp": "2025-01-17T10:30:00Z"
  },
  {
    "id": 2,
    "session_id": 1,
    "message_type": "assistant",
    "content": "Protein folding is the process by which...",
    "metadata": {
      "sources": [
        {
          "source_id": 1,
          "doc_name": "biochemistry_notes.pdf",
          "post_name": "Protein Structure",
          "similarity_score": 0.89
        }
      ],
      "tokens_used": 150
    },
    "timestamp": "2025-01-17T10:30:15Z"
  }
]
```

### Send Message
```http
POST /chat/message
Content-Type: application/json

{
  "session_id": 1,
  "content": "Explain protein folding based on the course materials"
}
```
**Response:**
```json
{
  "message": "Protein folding is the process by which a protein chain acquires its native 3D structure...",
  "sources": [
    {
      "source_id": 1,
      "doc_name": "biochemistry_notes.pdf",
      "post_name": "Protein Structure",
      "similarity_score": 0.89
    }
  ],
  "session_id": 1,
  "message_id": 2,
  "tokens_used": 150
}
```

### Delete Session
```http
DELETE /chat/sessions/{session_id}
```
**Response:**
```json
{
  "message": "Session deleted successfully"
}
```

---

## 🔄 Redis Cache Management

### Get Cache Statistics
```http
GET /cache/stats
```
**Response:**
```json
{
  "cache_stats": {
    "enabled": true,
    "connected_clients": 2,
    "used_memory": "2.1MB",
    "total_commands_processed": 1547,
    "keyspace_hits": 892,
    "keyspace_misses": 234,
    "hit_rate": 79.2
  },
  "timestamp": "2025-01-17T10:30:00Z"
}
```

### Check Cache Health
```http
GET /cache/health
```
**Response:**
```json
{
  "status": "healthy",
  "message": "Redis cache is working properly",
  "operations_tested": ["set", "get", "delete"]
}
```

### Invalidate Course Cache
```http
POST /cache/invalidate/course/{course_id}
```
**Response:**
```json
{
  "message": "Invalidated cache for course 59",
  "deleted_entries": 15,
  "course_id": 59
}
```

### Invalidate All Cache
```http
POST /cache/invalidate/all
```
**Response:**
```json
{
  "message": "Invalidated all cache entries",
  "deleted_entries": 247
}
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_BUCKET_NAME=your_bucket_name
AWS_REGION=us-east-1

# LlamaParse
LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key
LLAMA_PROJECT_ID=your_project_id

# OpenAI
OPENAI_API_KEY=your_openai_api_key
```

---

## 🗄️ Database Schema

### New Tables Created

#### chat_sessions
```sql
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR NOT NULL,
    course_id INTEGER NOT NULL,
    session_name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

#### chat_messages
```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id),
    message_type VARCHAR NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    metadata JSON,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

#### document_chunks
```sql
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    doc_name VARCHAR NOT NULL,
    post_name VARCHAR,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    embedding VECTOR(1536), -- OpenAI text-embedding-3-small
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### course_index_status
```sql
CREATE TABLE course_index_status (
    id SERIAL PRIMARY KEY,
    course_id INTEGER UNIQUE NOT NULL,
    last_indexed TIMESTAMP,
    document_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔄 Automatic Processing

### Periodic Course Indexing
- **Frequency**: Every 5 minutes
- **Process**: Checks for new courses with documents
- **Action**: Automatically processes and indexes new content
- **Status Tracking**: Updates course_index_status table

### Document Processing Pipeline
1. **Download**: Fetch PDF from S3 using doc_url
2. **Parse**: Use LlamaParse for intelligent text extraction
3. **Chunk**: Split text into overlapping chunks (1000 chars, 200 overlap)
4. **Embed**: Generate embeddings using OpenAI text-embedding-3-small
5. **Store**: Save chunks and embeddings to pgvector database

---

## 🎯 RAG Implementation

### Similarity Search
```sql
SELECT chunk_text, doc_name, post_name,
       1 - (embedding <=> :query_embedding) as similarity_score
FROM document_chunks 
WHERE course_id = :course_id
ORDER BY embedding <=> :query_embedding
LIMIT 5;
```

### Context Building
1. **Query Embedding**: Generate embedding for user question
2. **Similarity Search**: Find top 3-5 most relevant chunks
3. **Context Assembly**: Combine relevant chunks with source attribution
4. **Response Generation**: Use gpt-4o-mini with context and chat history

---

## 🚨 Error Handling

### Common Error Responses

#### 404 - Not Found
```json
{
  "detail": "Session not found"
}
```

#### 500 - Internal Server Error
```json
{
  "detail": "Failed to process message"
}
```

#### 422 - Validation Error
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

---

## 📊 Performance Considerations

### Embedding Costs
- **text-embedding-3-small**: $0.00002 per 1K tokens
- **Batch Processing**: Multiple chunks processed in single API call
- **Estimated Cost**: ~$0.01 per average PDF document

### Database Performance
- **pgvector Indexes**: Automatic HNSW indexing for fast similarity search
- **Connection Pooling**: SQLAlchemy connection management
- **Query Optimization**: Efficient similarity search with course filtering

---

## 🔒 Security Notes

### Production Recommendations
1. **Add Authentication**: Implement JWT or session-based auth
2. **Rate Limiting**: Add request rate limiting
3. **Input Validation**: Sanitize all user inputs
4. **CORS Configuration**: Restrict allowed origins
5. **API Key Security**: Use environment variables, never commit keys
6. **Database Security**: Use connection pooling and prepared statements

---

## 🐛 Troubleshooting

### Common Issues

#### pgvector Extension Not Found
```bash
# Install pgvector extension in PostgreSQL
CREATE EXTENSION IF NOT EXISTS vector;
```

#### OpenAI API Errors
- Check API key validity
- Verify sufficient credits
- Monitor rate limits

#### Document Processing Failures
- Verify S3 credentials and bucket access
- Check LlamaParse API key and project ID
- Ensure PDF files are accessible

#### Embedding Dimension Mismatch
- Ensure database uses Vector(1536) for text-embedding-3-small
- Drop and recreate tables if dimension changed

---

## 📈 Monitoring

### Key Metrics to Track
- **API Response Times**: Monitor endpoint performance
- **Embedding Costs**: Track OpenAI API usage
- **Document Processing Success Rate**: Monitor indexing failures
- **Chat Session Activity**: Track user engagement
- **Database Performance**: Monitor query execution times

---

## 🔄 Development Workflow

### Adding New Features
1. Update database models in `models.py`
2. Add database migrations if needed
3. Implement business logic in service classes
4. Add API endpoints in `main.py`
5. Update documentation and tests

### Testing

#### 🧪 **Advanced Test Client**
The system includes a comprehensive test client with multiple testing modes:

```bash
# Basic functionality testing
python test_client.py --mode=basic

# Comprehensive testing (recommended)
python test_client.py --mode=comprehensive

# Performance benchmarking
python test_client.py --mode=performance

# Stress testing
python test_client.py --mode=stress
```

#### **Test Features:**
- ✅ **Complete API Coverage** - Tests all endpoints systematically
- ✅ **Performance Benchmarking** - Response time analysis and optimization
- ✅ **Cache Efficiency Testing** - Redis hit rate validation
- ✅ **Concurrent Request Testing** - Multi-threaded load testing
- ✅ **Error Handling Validation** - Edge case and error scenario testing
- ✅ **Data Validation Testing** - Input validation and security testing
- ✅ **Chat Flow Testing** - Complete conversation context validation
- ✅ **Stress Testing** - High-load performance validation

#### **Test Reports:**
- Detailed JSON reports with metrics
- Performance benchmarks and recommendations
- Cache efficiency analysis
- Error rate monitoring
- Production readiness assessment

#### **Example Test Output:**
```
🚀 Starting RAG Study Chat API Advanced Test Suite
============================================================
Mode: COMPREHENSIVE
============================================================

✅ PASS Health Check: Status: RAG Study Chat API is running
✅ PASS Get All Courses: Found 150 courses
✅ PASS Performance /courses: Avg: 45.2ms, Min: 32.1ms, Max: 78.9ms
✅ PASS Cache Efficiency: Cache hits increased by 12, misses by 3
✅ PASS Chat Conversation Flow: 5/5 messages successful, Avg response: 1250ms

📊 COMPREHENSIVE TEST SUMMARY
============================================================
Total Tests: 25
✅ Passed: 24
❌ Failed: 1
Success Rate: 96.0%

🚀 System ready for production deployment!
```

---

## 🚀 **Production Deployment**

### **Docker Deployment (Recommended)**
```bash
# Quick production deployment
./deploy.sh prod

# Development with hot reload
./deploy.sh dev

# Check deployment status
./deploy.sh status

# View logs
./deploy.sh logs api
```

### **Manual Deployment**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Initialize database
python -c "from database import create_tables; create_tables()"

# 4. Start the server
python main.py
```

### **Production Checklist**
- [ ] Configure environment variables
- [ ] Set up PostgreSQL with pgvector
- [ ] Configure Redis for caching
- [ ] Set up SSL/HTTPS
- [ ] Configure rate limiting
- [ ] Set up monitoring and logging
- [ ] Run comprehensive tests
- [ ] Configure backup procedures

---

## 📞 **Support & Resources**

### **Documentation**
- 📚 [Complete API Documentation](API_DOCUMENTATION.md) - Detailed endpoint reference
- 🐳 [Docker Deployment Guide](DOCKER_DEPLOYMENT.md) - Production deployment
- 🧪 [Testing Guide](test_client.py) - Comprehensive testing suite

### **Quick Links**
- **Health Check**: `GET /health`
- **API Stats**: `GET /cache/stats`
- **Test Suite**: `python test_client.py --mode=comprehensive`
- **Interactive Demo**: `python example_client.py`

### **Getting Help**
1. Check the [API Documentation](API_DOCUMENTATION.md) for detailed examples
2. Run the test suite to identify issues: `python test_client.py`
3. Check system health: `curl http://localhost:8000/health`
4. Review logs for detailed error messages
5. Verify configuration in `.env` file

### **Performance Optimization**
- Monitor cache hit rates via `/cache/stats`
- Use Redis caching for optimal performance
- Implement proper database indexing
- Monitor OpenAI API usage and costs
- Use connection pooling for database access

---

## 🎉 **Ready to Get Started?**

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd rag_study_chat

# 2. Quick setup and validation
python setup.py

# 3. Deploy with Docker
./deploy.sh prod

# 4. Run comprehensive tests
python test_client.py --mode=comprehensive

# 5. Start building your intelligent tutoring system! 🚀
```

**Your RAG-powered educational platform is ready to transform learning experiences!** 🎓✨

---

*Last Updated: January 17, 2025 | Version: 1.0.0*

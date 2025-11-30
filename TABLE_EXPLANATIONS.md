# RAG Database Tables Explanation

## Overview
Your RAG system uses several PostgreSQL tables to manage document indexing, embeddings, and chat functionality. Here's what each table does:

---

## 1. `course_index_status` Table

### Purpose
**Tracks the indexing status of entire courses** to manage bulk document processing.

### Schema
```python
class CourseIndexStatus(Base):
    id                  # Primary key
    course_id           # Foreign key to courses table (UNIQUE)
    last_indexed        # DateTime when last indexed
    document_count      # Number of documents processed
    chunk_count         # Total chunks created
    status              # "pending", "processing", "completed", "failed"
    error_message       # Error details if failed
    created_at          # When record was created
    updated_at          # Last update timestamp
```

### Use Cases

#### 1. **Bulk Course Indexing**
When you have a course with many PDF documents (e.g., 50 lecture slides), this table tracks:
- How many documents were processed
- How many chunks were created
- Whether indexing succeeded or failed
- When it was last indexed

#### 2. **Admin Dashboard**
- Show which courses are indexed and ready for AI chat
- Display indexing progress
- Identify failed courses that need attention

#### 3. **API Endpoints**

**Get unindexed courses:**
```bash
GET /courses/unindexed
```
Returns courses that haven't been indexed yet.

**Check course status:**
```bash
GET /courses/{course_id}/index-status
```
Returns:
```json
{
  "course_id": 123,
  "status": "completed",
  "document_count": 45,
  "chunk_count": 1234,
  "last_indexed": "2025-11-30T10:00:00Z"
}
```

**Trigger bulk indexing:**
```bash
POST /courses/index-unindexed
```
Processes all unindexed courses in the background.

**Process specific course:**
```bash
POST /courses/{course_id}/process-documents
```
Indexes all documents for a specific course.

### Example Workflow

```
1. New course created with 20 PDF documents
   → course_index_status: status="pending"

2. Admin triggers indexing: POST /courses/123/process-documents
   → status="processing"

3. Background job processes all 20 PDFs
   → Parses, chunks, generates embeddings
   → Updates: document_count=20, chunk_count=450

4. All documents successfully processed
   → status="completed", last_indexed=NOW()
   → AI chat is now available for this course!

5. If error occurs during processing:
   → status="failed", error_message="LlamaParse timeout on doc 15"
```

---

## 2. `document_index` Table

### Purpose
**Tracks individual document processing status** within courses or posts.

### Schema
```python
class DocumentIndex(Base):
    id                  # Primary key
    post_id             # Foreign key to post table
    course_id           # Foreign key to courses table
    doc_name            # Original filename (e.g., "lecture_05.pdf")
    doc_url             # S3 URL or file path
    s3_key              # S3 bucket key (optional)
    parsed_content      # Full text extracted from PDF (can be very large)
    embedding_status    # "pending", "processing", "completed", "failed"
    processed_at        # When processing completed
    chunk_count         # Number of chunks created from this document
```

### Use Cases

#### 1. **Individual Document Tracking**
Unlike `course_index_status` which tracks entire courses, this tracks **each individual PDF**:
- Stores the full parsed text content
- Tracks whether embeddings were generated
- Stores metadata for debugging

#### 2. **Status Monitoring**
Check if a specific document was successfully processed:
```sql
SELECT doc_name, embedding_status, chunk_count
FROM document_index
WHERE post_id = 456;
```

#### 3. **Content Caching**
The `parsed_content` field stores the full extracted text, which can be used for:
- Re-indexing without re-parsing (saves API calls to LlamaParse)
- Quick full-text search
- Document summaries

#### 4. **Debugging Failed Documents**
When a document fails to process:
```sql
SELECT doc_name, embedding_status, processed_at
FROM document_index
WHERE embedding_status = 'failed';
```

### Current Status in Your Codebase

⚠️ **IMPORTANT FINDING:** Based on my search, this table is **defined but NOT actively used** in the current codebase!

**Evidence:**
- Model exists in `models.py`
- No queries found using this table
- No INSERT/UPDATE operations in the code
- Status tracking is done through other mechanisms

**This table appears to be:**
1. **Legacy code** from an earlier version
2. **Planned feature** not yet implemented
3. **Redundant** - functionality covered by `document_chunks` and `course_index_status`

---

## How Document Processing Actually Works (Current System)

Based on the code, here's the actual flow:

### For Individual Posts (Current Implementation)

```
1. User uploads PDF → Post created in database

2. AI Chat opened → Check indexing status:
   GET /posts/{post_id}/index-status
   → Queries document_chunks table directly
   → Returns: indexed=true if chunks exist

3. If not indexed → Start background processing:
   POST /posts/{post_id}/process-background

4. Background processor:
   ✓ Downloads PDF from S3
   ✓ Parses with LlamaParse (extracts text + page numbers)
   ✓ Chunks text (1000 chars, 200 overlap)
   ✓ Generates embeddings (OpenAI text-embedding-3-small)
   ✓ Stores in document_chunks table
   ✓ Generates document summary → document_summaries table

5. User asks questions → RAG system:
   ✓ Query document_chunks for relevant chunks
   ✓ Use chunks as context for GPT-4o-mini
   ✓ Return answer with page references
```

### For Courses (Bulk Processing)

```
1. Admin checks unindexed courses:
   GET /courses/unindexed
   → Returns list of courses needing indexing

2. Trigger bulk indexing:
   POST /courses/index-unindexed

3. Background task processes each course:
   ✓ Get all documents for course
   ✓ Process each document (same as post flow)
   ✓ Update course_index_status table:
     - document_count += 1
     - chunk_count += N
     - status = "processing" → "completed"

4. Course indexing complete:
   → course_index_status.status = "completed"
   → All documents searchable via RAG
```

---

## Core Tables Actually Used for RAG

### 1. `document_chunks` (Primary RAG Table)
- Stores text chunks with embeddings
- Used for similarity search
- Contains page numbers (after your recent update)
- **This is the heart of the RAG system**

### 2. `document_summaries`
- Stores AI-generated summaries of each document
- Used for query optimization
- Helps LLM understand document context

### 3. `course_index_status`
- Tracks course-level indexing progress
- **Actively used** for bulk operations

### 4. `chat_sessions` & `chat_messages`
- Stores chat conversations
- Links messages to sessions
- Preserves chat history

### 5. `document_index`
- **NOT actively used in current code**
- Could be removed or implemented properly

---

## Recommendations

### Option 1: Remove `document_index` Table (Simplify)
Since it's not being used, you could:
1. Drop the table
2. Remove the model from `models.py`
3. Rely on `document_chunks` for tracking (it already has post_id, course_id, doc_name)

### Option 2: Implement `document_index` Properly (Feature Complete)
If you want granular document tracking:
1. Add INSERT operations when processing documents
2. Update `embedding_status` during processing
3. Use it for retry logic (failed documents)
4. Add API endpoint: `GET /documents/{doc_id}/status`

### Option 3: Keep As-Is (No Action)
Leave it for potential future use. No harm in having an empty table.

---

## Summary

**`course_index_status`**: ✅ **ACTIVE** - Tracks bulk course indexing
- Used by admin endpoints
- Manages large-scale processing
- Shows indexing progress

**`document_index`**: ⚠️ **INACTIVE** - Defined but not used
- Model exists
- No active queries
- Could be legacy or planned feature

**Actual document tracking happens through:**
- `document_chunks` (has post_id, course_id, doc_name)
- Direct chunk count queries
- Background processor status tracking

The system works fine without `document_index` - it's currently redundant with the information already in `document_chunks`.

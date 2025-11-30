import os
from openai import OpenAI
from typing import List, Dict, Any, Optional
from vector_store import VectorStore
from database import get_db, get_course_documents, SessionLocal
from models import ChatSession, ChatMessage, ChatMessageResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from dotenv import load_dotenv
from prompt_optimizer import PromptOptimizer

load_dotenv()

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.vector_store = VectorStore()
        self.model = "gpt-4o-mini"
        self.prompt_optimizer = PromptOptimizer(os.getenv('OPENAI_API_KEY'))
        
    def create_chat_session(self, user_email: str, post_id: int, session_name: str, db: Session) -> ChatSession:
        """Create a new chat session for a specific post"""
        # Get course_id from post_id for backward compatibility
        with db:
            result = db.execute(text("SELECT course_id FROM post WHERE id = :post_id"), {"post_id": post_id})
            course_row = result.fetchone()
            if not course_row:
                raise ValueError(f"Post {post_id} not found")
            course_id = course_row[0]
        
        session = ChatSession(
            user_email=user_email,
            course_id=course_id,  # Keep for backward compatibility
            post_id=post_id,
            session_name=session_name
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    def get_user_sessions(self, user_email: str, db: Session) -> List[ChatSession]:
        """Get all active sessions for a user"""
        return db.query(ChatSession).filter(
            ChatSession.user_email == user_email,
            ChatSession.is_active == True
        ).order_by(ChatSession.updated_at.desc()).all()
    
    def get_session_messages(self, session_id: int, db: Session) -> List[ChatMessage]:
        """Get all messages for a session"""
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp.asc()).all()
    
    def save_message(self, session_id: int, message_type: str, content: str,
                    metadata: Optional[Dict] = None, db: Session = None) -> ChatMessage:
        """Save a message to the database"""
        logger.info(f"💾 save_message called: session_id={session_id}, message_type={message_type}, content_length={len(content)}")

        # Create a new database session if none provided
        if db is None:
            logger.info("📂 Creating new DB session for save_message")
            db = SessionLocal()
            close_db = True
        else:
            logger.info("📂 Using existing DB session for save_message")
            close_db = False

        try:
            # Ensure metadata is clean and JSON-serializable
            clean_metadata = {}
            if metadata:
                for key, value in metadata.items():
                    # Only keep JSON-serializable values
                    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        clean_metadata[key] = value
                    else:
                        clean_metadata[key] = str(value)

            message = ChatMessage(
                session_id=session_id,
                message_type=message_type,
                content=content,
                message_metadata=clean_metadata
            )
            db.add(message)
            logger.info("➕ Message added to session, committing...")
            db.commit()
            logger.info("✅ Message committed successfully")
            db.refresh(message)
            logger.info(f"🎉 Message saved with ID: {message.id}")
            return message
        except Exception as e:
            logger.error(f"❌ Error saving message: {e}")
            db.rollback()
            raise
        finally:
            if close_db:
                logger.info("🔒 Closing DB session")
                db.close()
    
    def get_relevant_context(self, query: str, post_id: int, max_chunks: int = 5,
                            subject: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get relevant document chunks for the query with content filtering.
        Now supports subject-enhanced search for better educational content retrieval.
        """
        # Get more chunks initially to allow for filtering
        initial_results = self.vector_store.search_similar_chunks(
            query=query,
            post_id=post_id,
            n_results=max_chunks * 3,  # Get more to find better matches
            subject=subject  # Pass subject for enhanced search
        )

        # Filter results based on similarity score with higher threshold for better relevance
        filtered_results = []
        for chunk in initial_results:
            similarity = chunk.get('similarity_score', 0)

            # Use higher threshold for better context relevance
            # This ensures we only get chunks that are truly relevant to the query
            if similarity > 0.4:  # Increased from 0.3 to 0.4
                filtered_results.append(chunk)

        # If we have too few high-quality results, lower threshold slightly
        if len(filtered_results) < 2:
            for chunk in initial_results:
                similarity = chunk.get('similarity_score', 0)
                if similarity > 0.3 and chunk not in filtered_results:
                    filtered_results.append(chunk)

        # Return the best chunks up to max_chunks
        return filtered_results[:max_chunks]
    
    def build_system_prompt(self, post_id: int, post_info: Dict[str, Any], action_type: Optional[str] = None) -> str:
        """Build enhanced system prompt for tutor-like behavior or specific quick actions"""
        subject = post_info.get('subject', 'General Knowledge')
        grade = post_info.get('grade', 'students')
        category = post_info.get('category', 'Educational Content')
        post_name = post_info.get('post_name', 'the document')

        logger.info(f"Building system prompt with action_type: '{action_type}'")

        # Handle quick action-specific prompts
        if action_type == "generate-questions":
            return f"""You are an expert exam question generator for {subject} at the {grade} level.

**YOUR TASK**: Generate 5-7 high-quality exam questions based on the provided page content from "{post_name}".

**QUESTION REQUIREMENTS**:
1. **Mix of Question Types**:
   - 2-3 Multiple Choice Questions (MCQs) with 4 options each
   - 2-3 Short Answer Questions (2-3 sentences expected)
   - 1-2 Conceptual/Application Questions

2. **Quality Standards**:
   - Questions must test understanding, not just memorization
   - Cover different concepts from the page
   - Be clear and unambiguous
   - Appropriate for {grade} level

3. **Format**:
   ```
   ## Exam Questions

   ### Multiple Choice Questions

   **Q1.** [Question text]
   - A) [Option A]
   - B) [Option B]
   - C) [Option C]
   - D) [Option D]
   *Correct Answer: [Letter]*

   ### Short Answer Questions

   **Q[N].** [Question text]

   ### Conceptual Questions

   **Q[N].** [Question text]
   ```

**CRITICAL**: Generate ONLY questions. Do NOT provide explanations, summaries, or study advice."""

        elif action_type == "explain-page":
            return f"""You are a clear and patient {subject} tutor explaining content from "{post_name}" to {grade} students.

**YOUR TASK**: Provide a comprehensive, easy-to-understand explanation of the page content provided.

**EXPLANATION APPROACH**:
1. **Start with an Overview**: Brief introduction to what this page covers (1-2 sentences)

2. **Break Down Key Concepts**: For each main concept:
   - **Define** the concept clearly
   - **Explain** how it works with examples
   - **Connect** it to practical applications or real-world scenarios

3. **Use Clear Structure**:
   - Use ## headings for main concepts
   - Use **bold** for important terms
   - Use bullet points for lists
   - Add examples in *italics* where helpful

4. **Make it Understandable**:
   - Explain complex ideas step-by-step
   - Use analogies when helpful
   - Relate to what students already know

**CRITICAL**: Focus on helping students UNDERSTAND the material deeply, not just summarizing it."""

        elif action_type == "important-points":
            return f"""You are a study guide creator for {subject} students at the {grade} level working with "{post_name}".

**YOUR TASK**: Identify and explain the most important points from the provided page content.

**FORMAT**:
```
## Key Points from This Page

### 🔑 Main Concepts
[List 2-4 core concepts with brief explanations]

### 📌 Important Definitions
[List key terms and their definitions]

### ⚡ Critical Information
[Highlight must-know facts, formulas, or principles]

### 💡 Key Takeaways
[Summarize what students must remember]
```

**GUIDELINES**:
- Prioritize information that's likely to appear on exams
- Explain WHY each point is important
- Keep explanations concise but complete
- Use **bold** for emphasis

**CRITICAL**: Focus on what students need to REMEMBER, not everything on the page."""

        elif action_type == "summarize-page":
            return f"""You are creating a concise page summary for {grade} students studying "{post_name}".

**YOUR TASK**: Provide a clear, focused summary of the provided page content.

**SUMMARY STRUCTURE**:
1. **Main Topic** (1 sentence): What is this page about?

2. **Key Points** (3-5 bullet points): What are the essential ideas?

3. **Important Details** (2-3 sentences): What specific information is critical?

4. **Connection** (1 sentence): How does this relate to the broader topic?

**GUIDELINES**:
- Keep it concise - aim for 150-200 words total
- Focus on the MAIN ideas, skip minor details
- Use clear, straightforward language
- Make it easy to review quickly

**CRITICAL**: This should be scannable and quick to read - a study aid, not a detailed explanation."""

        # Default tutor prompt for normal chat
        return f"""You are Study Send Pal, a knowledgeable and friendly AI tutor specializing in {subject} for {grade} students.

YOUR ROLE:
You help students understand concepts and learn from their study materials. When students ask questions, you provide clear, educational responses that connect general knowledge with specific content from their readings.

HOW TO RESPOND:

1. **Answer the Question Directly**:
   - Start with a clear, direct answer to what they asked
   - Provide a concise explanation (2-4 sentences)
   - Define key terms and concepts

2. **Connect to Their Study Material**:
   - Review the provided sources [Source 1], [Source 2], etc.
   - If the topic appears in the sources, naturally weave in relevant information
   - Reference specific concepts, examples, or details from the sources
   - Make connections between the general concept and what they're studying

3. **Be Conversational and Natural**:
   - Write like you're explaining to a friend or classmate
   - Don't explicitly mention "the document", "your material", or document names
   - Just naturally incorporate information from sources as if it's part of your explanation
   - Example: Instead of "Looking at your document...", say "For instance..." or "In the context of..."

RESPONSE PATTERNS:

**When sources contain relevant info:**
"**[Concept]** is [direct explanation].

[Naturally incorporate source material without calling it out explicitly]. For instance, [detail from source]... This relates to [another detail from source]..."

**When sources don't contain the topic:**
"**[Concept]** is [direct explanation].

Based on what you're studying, you might be more interested in [related topics from subject area]. These concepts come up frequently in {subject} and are important for understanding [broader theme]."

CRITICAL RULES:
✓ Answer questions directly and clearly first
✓ Check provided sources and incorporate relevant information naturally
✓ Never explicitly mention "the document", document names, or "your material"
✓ Be conversational - write like a knowledgeable tutor, not a document assistant
✓ Stay educational and focused on helping students learn
✓ Use markdown formatting for clarity, but keep it natural

FORMATTING RULES:
- Use **bold** for key terms and important concepts
- Use *italics* for emphasis or examples
- Use bullet points for lists of features or characteristics
- Use numbered lists only for sequential steps or processes
- Keep paragraphs concise and readable
- NO separator lines (====== or ------)
- NO document metadata or references
- Be friendly, clear, and educational"""
    
    def generate_response(self, query: str, session_id: int, post_id: Optional[int] = None, 
                         course_id: Optional[int] = None, post_info: Optional[Dict[str, Any]] = None,
                         course_info: Optional[Dict[str, Any]] = None, chat_history: List[Dict[str, str]] = None, 
                         db: Session = None) -> Dict[str, Any]:
        """Generate AI response with RAG context for a specific post or course (backward compatibility)"""
        # Handle backward compatibility
        if post_id and post_info:
            return self._generate_post_response(query, session_id, post_id, post_info, chat_history or [], db)
        elif course_id and course_info:
            return self._generate_course_response(query, session_id, course_id, course_info, chat_history or [], db)
        else:
            raise ValueError("Either post_id with post_info or course_id with course_info must be provided")
    
    def _generate_post_response(self, query: str, session_id: int, post_id: int, 
                         post_info: Dict[str, Any], chat_history: List[Dict[str, str]], 
                         db: Session) -> Dict[str, Any]:
        """Generate AI response with RAG context for a specific post"""
        try:
            # Check if user is requesting a document summary
            if self.is_summary_request(query):
                logger.info(f"Document summary requested for post {post_id}")
                
                # Save user message
                user_msg = self.save_message(
                    session_id=session_id,
                    message_type="user",
                    content=query,
                    db=db
                )
                
                # Generate document summary
                summary = self.generate_document_summary(post_id, post_info, db)
                
                # Save assistant response
                response_msg = self.save_message(
                    session_id=session_id,
                    message_type="assistant", 
                    content=summary,
                    metadata={"type": "document_summary", "post_id": post_id},
                    db=db
                )
                
                return {
                    "message": summary,
                    "sources": [],
                    "session_id": session_id,
                    "message_id": response_msg.id,
                    "type": "summary"
                }
            
            # Get document summary for better context in query optimization
            document_summary = self.vector_store.get_document_summary(post_id)
            
            # Optimize the user query for better retrieval
            logger.info(f"Optimizing query: '{query}'")
            document_context = {
                'doc_name': post_info.get('doc_name', 'Unknown'),
                'post_name': post_info.get('post_name', 'Unknown'),
                'subject': post_info.get('subject', 'Unknown'),
                'course_id': post_info.get('course_id', 'Unknown')
            }
            
            # Add document summary if available
            if document_summary:
                document_context['document_summary'] = document_summary
                logger.info(f"Using document summary for query optimization (post_id: {post_id})")
            
            optimized_query = self.prompt_optimizer.optimize_query(
                user_query=query,
                document_context=document_context,
                chat_history=chat_history
            )
            
            # Use the enhanced query for retrieval
            enhanced_search_query = self.prompt_optimizer.enhance_retrieval_query(optimized_query)
            
            # Get relevant document chunks using the optimized query with subject context
            subject = post_info.get('subject')
            relevant_chunks = self.get_relevant_context(enhanced_search_query, post_id, subject=subject)

            logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks for post {post_id}")
            if relevant_chunks:
                logger.info(f"Top similarity scores: {[chunk.get('similarity_score', 0) for chunk in relevant_chunks[:3]]}")

            # Build context from relevant chunks
            context_text = ""
            sources = []

            if relevant_chunks:
                # Check if we have any relevant content
                valid_chunks = [chunk for chunk in relevant_chunks if chunk.get('similarity_score', 0) > 0.3]
                
                if valid_chunks:
                    context_text = "\n\nRelevant content:\n"
                    for i, chunk in enumerate(valid_chunks, 1):
                        page_num = chunk['metadata'].get('page_number')
                        page_ref = f" (Page {page_num})" if page_num else ""
                        context_text += f"\n[Source {i}{page_ref}]: {chunk['content']}\n"

                        # Create a concise preview of the chunk content (first 100 chars)
                        content_preview = chunk['content'][:100].strip()
                        if len(chunk['content']) > 100:
                            content_preview += "..."

                        sources.append({
                            "source_id": i,
                            "doc_name": chunk['metadata'].get('doc_name', 'Unknown'),
                            "post_name": chunk['metadata'].get('post_name', 'Unknown'),
                            "post_id": chunk['metadata'].get('post_id'),
                            "page_number": chunk['metadata'].get('page_number'),
                            "similarity_score": chunk['similarity_score'],
                            "content_preview": content_preview  # Add preview for display
                        })
                else:
                    # No good matches found, add a note about this
                    context_text = f"\n\nNote: The document '{post_info.get('post_name', 'Unknown')}' may not contain information directly relevant to this question about {post_info.get('subject', 'the subject')}. Please provide a helpful response based on standard {post_info.get('subject', 'curriculum')} knowledge.\n"
            
            # Build messages for OpenAI
            messages = [
                {"role": "system", "content": self.build_system_prompt(post_id, post_info, action_type)}
            ]

            # Add chat history (last 10 messages to stay within token limits)
            for msg in chat_history[-10:]:
                messages.append(msg)

            # Add current query with context - provide sources for tutor to check
            doc_name = post_info.get('post_name', 'Unknown Document')
            if context_text and "Relevant content from" in context_text:
                user_message = f"""Question: {query}

Document context from "{doc_name}":
{context_text}

Please check the sources above and answer accordingly."""
            else:
                user_message = f"""Question: {query}

Note: No directly relevant content was found in the document "{doc_name}" for this specific question. Please provide a brief helpful explanation of the concept, then explain what the document does cover."""

            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Save user message
            user_msg = self.save_message(
                session_id=session_id,
                message_type="user",
                content=query,
                db=db
            )
            
            # Save AI response
            ai_msg = self.save_message(
                session_id=session_id,
                message_type="assistant",
                content=ai_response,
                metadata={"sources": sources, "tokens_used": response.usage.total_tokens},
                db=db
            )
            
            return {
                "message": ai_response,
                "sources": sources,
                "session_id": session_id,
                "message_id": ai_msg.id,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            
            # Save user message even if AI response fails
            self.save_message(
                session_id=session_id,
                message_type="user",
                content=query,
                db=db
            )
            
            # Save error response
            error_msg = self.save_message(
                session_id=session_id,
                message_type="assistant",
                content="I apologize, but I'm having trouble generating a response right now. Please try again.",
                metadata={"error": str(e)},
                db=db
            )
            
            return {
                "message": "I apologize, but I'm having trouble generating a response right now. Please try again.",
                "sources": [],
                "session_id": session_id,
                "message_id": error_msg.id,
                "error": str(e)
            }
    
    def _generate_course_response(self, query: str, session_id: int, course_id: int, 
                         course_info: Dict[str, Any], chat_history: List[Dict[str, str]], 
                         db: Session) -> Dict[str, Any]:
        """Generate AI response with RAG context for a course (backward compatibility)"""
        try:
            # Get relevant document chunks from the course
            initial_results = self.vector_store.search_similar_chunks(
                query=query,
                course_id=course_id,
                n_results=10
            )
            
            # Filter results based on relevance and quality (same logic as before)
            filtered_results = []
            for chunk in initial_results:
                content = chunk.get('content', '').lower()
                similarity = chunk.get('similarity_score', 0)
                
                # Skip chunks that are clearly off-topic (contain too many RAG research terms)
                rag_terms = ['retrieval-augmented generation', 'embedding model', 'vector database', 
                            'llm evaluation', 'benchmark dataset', 'research paper']
                rag_term_count = sum(1 for term in rag_terms if term in content)
                
                # Only include chunks with good similarity and not too many research terms
                if similarity > 0.3 and rag_term_count < 2:
                    filtered_results.append(chunk)
                elif similarity > 0.5:  # Include high similarity chunks even if they have some research terms
                    filtered_results.append(chunk)
            
            relevant_chunks = filtered_results[:5]
            
            # Build context from relevant chunks
            context_text = ""
            sources = []
            
            if relevant_chunks:
                # Check if we have any relevant content
                valid_chunks = [chunk for chunk in relevant_chunks if chunk.get('similarity_score', 0) > 0.3]
                
                if valid_chunks:
                    context_text = f"\n\nRelevant {course_info.get('subject', 'Course')} Material:\n"
                    for i, chunk in enumerate(valid_chunks, 1):
                        context_text += f"\n[Source {i}]: {chunk['content']}\n"
                        sources.append({
                            "source_id": i,
                            "doc_name": chunk['metadata'].get('doc_name', 'Unknown'),
                            "post_name": chunk['metadata'].get('post_name', 'Unknown'),
                            "similarity_score": chunk['similarity_score']
                        })
                else:
                    # No good matches found, add a note about this
                    context_text = f"\n\nNote: The available course documents may not contain information directly relevant to this question about {course_info.get('subject', 'the subject')}. Please provide a helpful response based on standard {course_info.get('subject', 'curriculum')} knowledge.\n"
            
            # Build messages for OpenAI (using course-based system prompt)
            course_prompt = f"""You are an expert AI tutor specializing in {course_info.get('subject', 'the subject')} for {course_info.get('grade', 'students')} students. 
Your role is to help students learn and understand {course_info.get('subject', 'the subject')} concepts, solve problems, and prepare for exams.

Course Context:
- Subject: {course_info.get('subject', 'the subject')}
- Grade Level: {course_info.get('grade', 'students')}
- Category: {course_info.get('category', 'the category')}

IMPORTANT INSTRUCTIONS:
1. Focus ONLY on {course_info.get('subject', 'the subject')} content that is relevant to {course_info.get('grade', 'students')} level
2. If the provided document context contains research papers or technical content about AI/RAG systems, IGNORE it
3. If the context is not relevant to {course_info.get('subject', 'the subject')}, draw from your knowledge of {course_info.get('subject', 'the subject')} curriculum instead
4. Provide clear, educational explanations appropriate for {course_info.get('grade', 'students')} students
5. Use examples and analogies that help students understand concepts
6. If you cannot find relevant course material, say so clearly and provide general {course_info.get('subject', 'the subject')} help

Teaching Guidelines:
- Be encouraging and supportive
- Break down complex concepts into simpler parts
- Provide step-by-step explanations when appropriate
- Use practical examples and real-world applications
- Encourage critical thinking and problem-solving"""
            
            messages = [
                {"role": "system", "content": course_prompt}
            ]
            
            # Add chat history (last 10 messages to stay within token limits)
            for msg in chat_history[-10:]:
                messages.append(msg)
            
            # Add current query with context
            user_message = f"{query}{context_text}"
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Save user message
            user_msg = self.save_message(
                session_id=session_id,
                message_type="user",
                content=query,
                db=db
            )
            
            # Save AI response
            ai_msg = self.save_message(
                session_id=session_id,
                message_type="assistant",
                content=ai_response,
                metadata={"sources": sources, "tokens_used": response.usage.total_tokens},
                db=db
            )
            
            return {
                "message": ai_response,
                "sources": sources,
                "session_id": session_id,
                "message_id": ai_msg.id,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            
            # Save user message even if AI response fails
            self.save_message(
                session_id=session_id,
                message_type="user",
                content=query,
                db=db
            )
            
            # Save error response
            error_msg = self.save_message(
                session_id=session_id,
                message_type="assistant",
                content="I apologize, but I'm having trouble generating a response right now. Please try again.",
                metadata={"error": str(e)},
                db=db
            )
            
            return {
                "message": "I apologize, but I'm having trouble generating a response right now. Please try again.",
                "sources": [],
                "session_id": session_id,
                "message_id": error_msg.id,
                "error": str(e)
            }
    def generate_document_summary(self, post_id: int, post_info: dict, db: Session) -> str:
        """Generate a comprehensive summary of all documents for a post"""
        try:
            # Get all document chunks for this post
            chunks = db.execute(text("""
                SELECT doc_name, chunk_text, chunk_index, total_chunks
                FROM document_chunks 
                WHERE post_id = :post_id 
                ORDER BY doc_name, chunk_index
            """), {"post_id": post_id}).fetchall()
            
            if not chunks:
                return "No documents found for this post."
            
            # Group chunks by document
            documents = {}
            for chunk in chunks:
                doc_name = chunk[0]
                if doc_name not in documents:
                    documents[doc_name] = []
                documents[doc_name].append(chunk[1])
            
            # Generate summary for each document
            summaries = []
            for doc_name, doc_chunks in documents.items():
                # Take a representative sample of chunks for summary
                sample_size = min(10, len(doc_chunks))
                sample_chunks = doc_chunks[:sample_size]
                combined_text = "\n\n".join(sample_chunks)
                
                # Limit text to avoid token limits
                if len(combined_text) > 8000:
                    combined_text = combined_text[:8000] + "..."
                
                summary_prompt = f"""
                Please provide a comprehensive summary of this document. Focus on:
                1. Main topic and purpose
                2. Key concepts and ideas
                3. Important findings or conclusions
                4. Practical applications or implications

                Document: {doc_name}
                Content:
                {combined_text}
                
                Provide a clear, structured summary in 3-4 paragraphs.
                """
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=1000,
                    temperature=0.3
                )
                
                doc_summary = response.choices[0].message.content
                summaries.append(f"**Document: {doc_name}**\n\n{doc_summary}")
            
            # Combine all document summaries (removed separator lines)
            final_summary = "\n\n".join(summaries)

            return final_summary
            
        except Exception as e:
            logger.error(f"Error generating document summary: {e}")
            return f"Error generating document summary: {str(e)}"
    
    def is_summary_request(self, query: str) -> bool:
        """Check if the user is requesting a document summary - must be explicit and complete"""
        query_lower = query.lower().strip()

        # More strict matching - only trigger on explicit document summary requests
        # These patterns focus on the entire document, not specific questions
        explicit_summary_patterns = [
            "summarize this document",
            "summarize the document",
            "summarise this document",
            "summarise the document",
            "give me a summary",
            "document summary",
            "what is this document about",
            "tell me about this document",
            "what does this document say",
            "document overview",
            "give me an overview",
            "overview of the document",
            "overview of this document",
            "what's in this document",
            "describe this document",
            "describe the document",
            "explain this document",
            "explain the document"
        ]

        # Check for exact phrase matches (more precise)
        for pattern in explicit_summary_patterns:
            if pattern in query_lower:
                # Additional check: make sure it's not part of a more specific question
                # If the query is significantly longer than the pattern, it's likely a specific question
                if len(query_lower) > len(pattern) + 20:
                    continue
                return True

        return False

    def generate_streaming_response(self, query: str, session_id: int, post_id: Optional[int] = None,
                                   course_id: Optional[int] = None, post_info: Optional[Dict[str, Any]] = None,
                                   course_info: Optional[Dict[str, Any]] = None, chat_history: Optional[List[Dict[str, str]]] = None,
                                   db: Optional[Session] = None, action_type: Optional[str] = None):
        """Generate streaming AI response with RAG context for a specific post or course"""
        # Handle backward compatibility
        if post_id and post_info:
            yield from self._generate_streaming_post_response(query, session_id, post_id, post_info, chat_history or [], db, action_type)
        elif course_id and course_info:
            yield from self._generate_streaming_course_response(query, session_id, course_id, course_info, chat_history or [], db)
        else:
            raise ValueError("Either post_id with post_info or course_id with course_info must be provided")

    def _handle_quick_action(self, action_type: str, content: str, post_info: Dict[str, Any]) -> str:
        """Generate direct prompt for quick actions without RAG complexity"""
        subject = post_info.get('subject', 'General Knowledge')
        post_name = post_info.get('post_name', 'the document')

        if action_type == "generate-questions":
            return f"""You are an exam question generator for {subject}.

Generate EXACTLY 5-7 exam questions from this content:

{content}

Use this format:
## Exam Questions

### Multiple Choice Questions
**Q1.** [question]
- A) [option]
- B) [option]
- C) [option]
- D) [option]
*Answer: [letter]*

### Short Answer Questions
**Q[N].** [question]

### Conceptual Questions
**Q[N].** [question]

Generate the questions now."""

        elif action_type == "important-points":
            return f"""Extract and organize the key points from this content.

Content from {post_name}:
{content}

You MUST respond using EXACTLY this structure:

## Key Points from This Page

### 🔑 Main Concepts
- **[Concept Name]**: [Brief explanation]
- **[Concept Name]**: [Brief explanation]

### 📌 Important Definitions
- **[Term]**: [Definition]
- **[Term]**: [Definition]

### ⚡ Critical Information
- [Important fact or formula]
- [Important fact or formula]

### 💡 Key Takeaways
- [What students must remember]
- [What students must remember]

Begin with "## Key Points from This Page" and follow the format above."""

        elif action_type == "explain-page":
            return f"""Provide a comprehensive explanation of this content from {post_name}.

Content:
{content}

Structure your explanation:
1. Start with an overview paragraph
2. Break down each key concept
3. Use examples where helpful
4. Make it easy to understand

Begin your explanation now."""

        elif action_type == "summarize-page":
            # For summarize, we want the entire document, not just a page
            return f"""Provide a comprehensive summary of the entire document "{post_name}".

Based on all the content in the document, create a summary that includes:

## Document Summary

### Overview
- Main topic and purpose of the document

### Key Themes
- 3-5 major themes or topics covered

### Important Concepts
- Critical concepts, formulas, or principles

### Practical Applications
- How this information can be applied

### Conclusion
- Main takeaways from the document

Create a well-organized summary (250-350 words) covering the entire document."""

        return content

    def _generate_streaming_post_response(self, query: str, session_id: int, post_id: int,
                                         post_info: Dict[str, Any], chat_history: List[Dict[str, str]],
                                         db: Optional[Session], action_type: Optional[str] = None):
        """Generate streaming AI response with RAG context for a specific post"""
        logger.info(f"Generating streaming response with action_type: {action_type}")
        try:
            # Handle page-based quick actions separately - bypass RAG and use simple direct prompts
            # Note: summarize-page is NOT in this list as it needs RAG to access entire document
            if action_type in ["generate-questions", "important-points", "explain-page"]:
                logger.info(f"Handling quick action: {action_type}")

                # Create a simple system message
                simple_system = "You are a helpful AI assistant. Follow the instructions exactly as given."

                # Get the specialized prompt for this action
                user_prompt = self._handle_quick_action(action_type, query, post_info)

                messages = [
                    {"role": "system", "content": simple_system},
                    {"role": "user", "content": user_prompt}
                ]

                # Save user message
                user_msg = self.save_message(
                    session_id=session_id,
                    message_type="user",
                    content=query,
                    db=db
                )

                # Generate streaming response
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=1500,
                    temperature=0.7,
                    stream=True
                )

                full_response = ""

                # Stream the response
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_response += content

                        yield {
                            "content": content,
                            "sources": [],
                            "session_id": session_id,
                            "done": False
                        }

                # Save the complete AI response
                ai_msg = self.save_message(
                    session_id=session_id,
                    message_type="assistant",
                    content=full_response,
                    metadata={"action_type": action_type},
                    db=db
                )

                # Send final message with complete info
                yield {
                    "content": "",
                    "message": full_response,
                    "sources": [],
                    "session_id": session_id,
                    "message_id": ai_msg.id,
                    "done": True
                }
                return

            # Handle summarize-page action - use RAG to get entire document context
            if action_type == "summarize-page":
                logger.info(f"Handling summarize-page action with RAG for entire document")
                # Let it fall through to the summary request handling below
                # which will use generate_document_summary with RAG

            # Check if user is requesting a document summary
            if action_type == "summarize-page" or self.is_summary_request(query):
                logger.info(f"Document summary requested for streaming, post {post_id}")
                
                # Save user message
                user_msg = self.save_message(
                    session_id=session_id,
                    message_type="user",
                    content=query,
                    db=db
                )
                
                # Generate document summary
                # Create temporary DB session if needed for summary generation
                if db is None:
                    temp_db = SessionLocal()
                    try:
                        summary = self.generate_document_summary(post_id, post_info, temp_db)
                    finally:
                        temp_db.close()
                else:
                    summary = self.generate_document_summary(post_id, post_info, db)
                
                # Stream the summary word by word
                words = summary.split()
                full_response = ""
                
                for i, word in enumerate(words):
                    if i == 0:
                        full_response = word
                        current_chunk = word
                    else:
                        current_chunk = " " + word
                        full_response += current_chunk
                    
                    # Yield each word as a streaming chunk
                    yield {
                        "content": current_chunk,
                        "message": full_response,
                        "sources": [],
                        "session_id": session_id,
                        "type": "summary",
                        "done": False
                    }
                
                # Save assistant response with complete summary
                response_msg = self.save_message(
                    session_id=session_id,
                    message_type="assistant",
                    content=summary,
                    metadata={"type": "document_summary", "post_id": post_id},
                    db=db
                )
                
                # Send final chunk with complete information
                yield {
                    "content": "",
                    "message": full_response,
                    "sources": [],
                    "session_id": session_id,
                    "message_id": response_msg.id,
                    "type": "summary",
                    "done": True
                }
                return
            
            # Get document summary for better context in query optimization
            document_summary = self.vector_store.get_document_summary(post_id)
            
            # Optimize the user query for better retrieval
            logger.info(f"Optimizing query for streaming: '{query}'")
            document_context = {
                'doc_name': post_info.get('doc_name', 'Unknown'),
                'post_name': post_info.get('post_name', 'Unknown'),
                'subject': post_info.get('subject', 'Unknown'),
                'course_id': post_info.get('course_id', 'Unknown')
            }
            
            # Add document summary if available
            if document_summary:
                document_context['document_summary'] = document_summary
                logger.info(f"Using document summary for streaming query optimization (post_id: {post_id})")
            
            optimized_query = self.prompt_optimizer.optimize_query(
                user_query=query,
                document_context=document_context,
                chat_history=chat_history
            )
            
            # Use the enhanced query for retrieval
            retrieval_query = self.prompt_optimizer.enhance_retrieval_query(optimized_query)
            
            # Get relevant document chunks from the specific post with subject context
            subject = post_info.get('subject')
            relevant_chunks = self.get_relevant_context(retrieval_query, post_id, subject=subject)
            
            # Build context from relevant chunks
            context_text = ""
            sources = []
            
            if relevant_chunks:
                # Check if we have any relevant content
                valid_chunks = [chunk for chunk in relevant_chunks if chunk.get('similarity_score', 0) > 0.3]
                
                if valid_chunks:
                    context_text = "\n\nRelevant content:\n"
                    for i, chunk in enumerate(valid_chunks, 1):
                        page_num = chunk.get('metadata', {}).get('page_number')
                        page_ref = f" (Page {page_num})" if page_num else ""
                        context_text += f"\n[Source {i}{page_ref}]: {chunk['content']}\n"

                        # Create a concise preview of the chunk content (first 100 chars)
                        content_preview = chunk['content'][:100].strip()
                        if len(chunk['content']) > 100:
                            content_preview += "..."

                        sources.append({
                            "source_id": i,
                            "doc_name": chunk.get('metadata', {}).get('doc_name', 'Unknown'),
                            "post_name": chunk.get('metadata', {}).get('post_name', 'Unknown'),
                            "post_id": chunk.get('metadata', {}).get('post_id', post_id),
                            "page_number": chunk.get('metadata', {}).get('page_number'),
                            "similarity_score": chunk.get('similarity_score', 0),
                            "content_preview": content_preview  # Add preview for display
                        })
            
            # Prepare conversation messages with strict context enforcement
            doc_name = post_info.get('post_name', 'Unknown Document')
            subject = post_info.get('subject', 'Unknown Subject')

            messages = [
                {"role": "system", "content": self.build_system_prompt(post_id, post_info, action_type)}
            ]

            # Add chat history
            for msg in chat_history:
                messages.append(msg)

            # Add current query with context - provide sources for tutor to check
            if action_type:
                # For quick actions, reinforce the task in the user message
                task_reminder = ""
                if action_type == "generate-questions":
                    task_reminder = "Generate 5-7 exam questions (MCQs, short answer, and conceptual) based on this content:"
                elif action_type == "explain-page":
                    task_reminder = "Provide a comprehensive explanation of this content:"
                elif action_type == "important-points":
                    task_reminder = """You MUST use this exact format:

## Key Points from This Page

### 🔑 Main Concepts
[List 2-4 core concepts]

### 📌 Important Definitions
[List key terms]

### ⚡ Critical Information
[Highlight must-know facts]

### 💡 Key Takeaways
[Summarize what to remember]

Now identify and list the key points from this content:"""
                elif action_type == "summarize-page":
                    task_reminder = "Provide a concise summary of this content:"

                if context_text:
                    user_message = f"""{task_reminder}

{context_text}"""
                else:
                    user_message = f"{task_reminder}\n\n{query}"
            else:
                # For normal chat, provide context with instructions
                if context_text:
                    user_message = f"""Question: {query}

Relevant context for this topic:
{context_text}

Use the sources above to provide a comprehensive answer that connects the concept to the specific content provided."""
                else:
                    user_message = f"""Question: {query}

Note: No directly relevant content was found in the study material for this specific question. Please provide a clear explanation of the concept based on your knowledge of {subject}."""

            messages.append({"role": "user", "content": user_message})

            # Save user message
            user_msg = self.save_message(
                session_id=session_id,
                message_type="user",
                content=query,
                db=db
            )
            
            # Generate streaming response
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            
            # Stream the response
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    yield {
                        "content": content,
                        "sources": sources,
                        "session_id": session_id,
                        "done": False
                    }
            
            # Save the complete AI response
            ai_msg = self.save_message(
                session_id=session_id,
                message_type="assistant",
                content=full_response,
                metadata={"sources": sources},
                db=db
            )
            
            # Send final message with complete info
            yield {
                "content": "",
                "message": full_response,
                "sources": sources,
                "session_id": session_id,
                "message_id": ai_msg.id,
                "done": True
            }
            
        except Exception as e:
            logger.error(f"Error generating streaming response: {e}")
            yield {
                "error": f"Error generating response: {str(e)}",
                "session_id": session_id,
                "done": True
            }

    def _generate_streaming_course_response(self, query: str, session_id: int, course_id: int, 
                                           course_info: Dict[str, Any], chat_history: List[Dict[str, str]], 
                                           db: Session):
        """Generate streaming AI response with RAG context for a course (backward compatibility)"""
        try:
            # Get relevant document chunks
            relevant_chunks = self.vector_store.search_similar_chunks(
                query=query, 
                course_id=course_id, 
                n_results=5
            )
            
            # Build context from relevant chunks
            context_text = ""
            sources = []
            
            if relevant_chunks:
                context_text = f"\n\nRelevant content from {course_info.get('course_subject', 'the course')}:\n"
                for i, chunk in enumerate(relevant_chunks, 1):
                    context_text += f"\n[Source {i}]: {chunk['content']}\n"
                    sources.append({
                        "source_id": i,
                        "doc_name": chunk.get('doc_name', 'Unknown'),
                        "post_name": chunk.get('post_name', 'Unknown'),
                        "post_id": chunk.get('post_id'),
                        "similarity_score": chunk.get('similarity_score', 0)
                    })
            
            # Prepare conversation messages
            messages = [
                {"role": "system", "content": f"""You are a helpful assistant for the course "{course_info.get('course_subject', 'Unknown Course')}". 
                Answer questions based on the course materials provided. Be helpful and educational."""}
            ]
            
            # Add chat history
            for msg in chat_history:
                messages.append(msg)
            
            # Add current query with context
            user_message = f"{query}{context_text}"
            messages.append({"role": "user", "content": user_message})
            
            # Save user message
            user_msg = self.save_message(
                session_id=session_id,
                message_type="user",
                content=query,
                db=db
            )
            
            # Generate streaming response
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                stream=True
            )
            
            full_response = ""
            
            # Stream the response
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    yield {
                        "content": content,
                        "sources": sources,
                        "session_id": session_id,
                        "done": False
                    }
            
            # Save the complete AI response
            ai_msg = self.save_message(
                session_id=session_id,
                message_type="assistant",
                content=full_response,
                metadata={"sources": sources},
                db=db
            )
            
            # Send final message with complete info
            yield {
                "content": "",
                "message": full_response,
                "sources": sources,
                "session_id": session_id,
                "message_id": ai_msg.id,
                "done": True
            }
            
        except Exception as e:
            logger.error(f"Error generating streaming course response: {e}")
            yield {
                "error": f"Error generating response: {str(e)}",
                "session_id": session_id,
                "done": True
            }

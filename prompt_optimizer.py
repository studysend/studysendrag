"""
Prompt Optimization Service for enhancing user queries before RAG retrieval
"""
import logging
from typing import Dict, List, Optional
import openai
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OptimizedQuery:
    original_query: str
    optimized_query: str
    keywords: List[str]
    context_type: str
    confidence: float

class PromptOptimizer:
    """
    Optimizes user queries using OpenAI to improve RAG retrieval and response quality
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided or set in OPENAI_API_KEY environment variable")
        self.client = openai.OpenAI(api_key=self.api_key)
        
    def optimize_query(self, 
                      user_query: str, 
                      document_context: Optional[Dict] = None,
                      chat_history: Optional[List[Dict]] = None) -> OptimizedQuery:
        """
        Optimize the user query for better RAG retrieval
        
        Args:
            user_query: Original user query
            document_context: Information about the document (name, type, subject)
            chat_history: Recent conversation history for context
            
        Returns:
            OptimizedQuery with enhanced query and metadata
        """
        try:
            # Build context for optimization
            optimization_prompt = self._build_optimization_prompt(
                user_query, document_context, chat_history
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a query optimization expert. Your job is to enhance user queries to improve document retrieval and answer quality.

TASK: Optimize the user's query to make it more specific, comprehensive, and suitable for document search.

GUIDELINES:
1. Expand abbreviations and clarify ambiguous terms
2. Add relevant context keywords that might appear in documents
3. Rephrase vague queries to be more specific
4. Include synonyms and related terms
5. Consider the document type and subject area
6. Maintain the user's original intent

RESPONSE FORMAT (JSON):
{
    "optimized_query": "Enhanced version of the query with better keywords and context",
    "keywords": ["key1", "key2", "key3"],
    "context_type": "explanation|summary|analysis|question|instruction",
    "confidence": 0.85,
    "reasoning": "Brief explanation of optimizations made"
}"""
                    },
                    {
                        "role": "user", 
                        "content": optimization_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse the response
            response_content = response.choices[0].message.content or ""
            result = self._parse_optimization_response(
                response_content, user_query
            )
            
            logger.info(f"Query optimized: '{user_query}' -> '{result.optimized_query}'")
            return result
            
        except Exception as e:
            logger.error(f"Query optimization failed: {str(e)}")
            # Fallback to original query
            return OptimizedQuery(
                original_query=user_query,
                optimized_query=user_query,
                keywords=self._extract_simple_keywords(user_query),
                context_type="question",
                confidence=0.5
            )
    
    def _build_optimization_prompt(self, 
                                 user_query: str,
                                 document_context: Optional[Dict],
                                 chat_history: Optional[List[Dict]]) -> str:
        """Build the optimization prompt with context"""
        
        prompt_parts = [f"ORIGINAL QUERY: '{user_query}'"]
        
        # Add document context
        if document_context:
            context_info = f"""
DOCUMENT CONTEXT:
- Document Name: {document_context.get('doc_name', 'Unknown')}
- Post Name: {document_context.get('post_name', 'Unknown')}
- Subject: {document_context.get('subject', 'Unknown')}
- Course: {document_context.get('course_id', 'Unknown')}"""
            
            # Add document summary if available
            if document_context.get('document_summary'):
                context_info += f"""
- Document Summary: {document_context['document_summary']}"""
            
            prompt_parts.append(context_info)
        
        # Add conversation history
        if chat_history and len(chat_history) > 0:
            recent_messages = chat_history[-3:]  # Last 3 messages
            history_text = []
            for msg in recent_messages:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:100]  # Truncate long messages
                history_text.append(f"{role}: {content}")
            
            prompt_parts.append(f"""
RECENT CONVERSATION:
{chr(10).join(history_text)}""")
        
        prompt_parts.append("""
OPTIMIZE the query to improve document retrieval and answer quality. Consider:
- What specific information is the user seeking?
- What terms might appear in the document?
- How can we make the search more precise?
- What context from the conversation is relevant?""")
        
        return "\n".join(prompt_parts)
    
    def _parse_optimization_response(self, response_text: str, original_query: str) -> OptimizedQuery:
        """Parse the OpenAI response and extract optimization data"""
        try:
            import json
            
            # Try to extract JSON from the response
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                data = json.loads(json_str)
                
                return OptimizedQuery(
                    original_query=original_query,
                    optimized_query=data.get('optimized_query', original_query),
                    keywords=data.get('keywords', []),
                    context_type=data.get('context_type', 'question'),
                    confidence=float(data.get('confidence', 0.7))
                )
            else:
                # Fallback: treat entire response as optimized query
                return OptimizedQuery(
                    original_query=original_query,
                    optimized_query=response_text.strip(),
                    keywords=self._extract_simple_keywords(response_text),
                    context_type="question",
                    confidence=0.6
                )
                
        except Exception as e:
            logger.error(f"Failed to parse optimization response: {str(e)}")
            return OptimizedQuery(
                original_query=original_query,
                optimized_query=original_query,
                keywords=self._extract_simple_keywords(original_query),
                context_type="question",
                confidence=0.5
            )
    
    def _extract_simple_keywords(self, text: str) -> List[str]:
        """Extract simple keywords as fallback"""
        import re
        
        # Remove common stop words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what', 'how', 'when', 'where', 'why', 'who'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return keywords[:10]  # Return top 10 keywords
    
    def enhance_retrieval_query(self, 
                              optimized_query: OptimizedQuery, 
                              max_keywords: int = 5) -> str:
        """
        Create an enhanced query string for vector search
        """
        # Combine optimized query with top keywords
        query_parts = [optimized_query.optimized_query]
        
        # Add relevant keywords
        if optimized_query.keywords:
            top_keywords = optimized_query.keywords[:max_keywords]
            query_parts.extend(top_keywords)
        
        enhanced_query = " ".join(query_parts)
        
        logger.info(f"Enhanced retrieval query: {enhanced_query}")
        return enhanced_query
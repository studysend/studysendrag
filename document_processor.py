import os
import boto3
from typing import List, Dict, Any, Optional
import tempfile
from llama_cloud_services import LlamaParse
from dotenv import load_dotenv
import logging
import openai

load_dotenv()

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-2')
        )
        self.bucket_name = os.getenv('BUCKET_NAME')
        self.llama_parser = None
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def _init_llama_parser(self, file_name: str):
        """Initialize LlamaParse with specific file configuration"""
        return LlamaParse(
            api_key=os.getenv('LLAMA_CLOUD_API_KEY'),
            result_type="text",
            verbose=True
        )
    
    def download_from_s3(self, doc_url: str, local_path: str) -> bool:
        """Download document from S3 using doc_url as key or full URL"""
        try:
            # Extract S3 key from full URL or use as-is if it's just a key
            s3_key = doc_url

            # If it's a full URL, extract the key
            if doc_url.startswith('http://') or doc_url.startswith('https://'):
                # Parse URL to extract key
                # Format: https://bucket-name.s3.region.amazonaws.com/key
                # or: https://s3.region.amazonaws.com/bucket-name/key
                from urllib.parse import urlparse
                parsed = urlparse(doc_url)
                path = parsed.path

                # Remove leading slash
                if path.startswith('/'):
                    path = path[1:]

                # If the bucket name is in the path (s3.region.amazonaws.com/bucket/key)
                # we need to remove it
                if self.bucket_name and path.startswith(self.bucket_name + '/'):
                    path = path[len(self.bucket_name) + 1:]

                s3_key = path
                logger.info(f"Extracted S3 key from URL: {s3_key}")

            # Construct the S3 key by adding .pdf extension if not present
            if not s3_key.endswith('.pdf'):
                s3_key = f"{s3_key}.pdf"

            logger.info(f"Downloading from S3: bucket={self.bucket_name}, key={s3_key}")
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Successfully downloaded {s3_key} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {doc_url} (key: {s3_key if 's3_key' in locals() else doc_url}): {str(e)}")
            return False
    
    def parse_pdf_with_llama(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """Parse PDF using LlamaParse and extract page information"""
        try:
            parser = self._init_llama_parser(file_name)

            # Parse the PDF file using the file path
            logger.info(f"Parsing PDF with LlamaParse: {file_name}")
            parsed_result = parser.load_data(file_path)

            # Extract text content from parsed result with page tracking
            text_content = ""
            page_map = []  # List of (start_char, end_char, page_number)
            current_position = 0

            if isinstance(parsed_result, list) and len(parsed_result) > 0:
                # LlamaParse typically returns a list of Document objects, one per page
                for page_idx, doc in enumerate(parsed_result):
                    page_num = page_idx + 1  # Page numbers start at 1
                    page_text = ""

                    if hasattr(doc, 'text'):
                        page_text = doc.text
                    elif hasattr(doc, 'get_content'):
                        page_text = doc.get_content()
                    else:
                        page_text = str(doc)

                    # Add page separator for better chunking
                    if page_text:
                        start_pos = current_position
                        text_content += page_text + "\n"
                        end_pos = current_position + len(page_text)

                        # Track which characters belong to which page
                        page_map.append({
                            'start': start_pos,
                            'end': end_pos,
                            'page': page_num
                        })

                        current_position = end_pos + 1  # +1 for the newline

                return {
                    'text': text_content.strip(),
                    'page_map': page_map
                }
            elif isinstance(parsed_result, str):
                # If we just get a string, we can't determine pages
                return {
                    'text': parsed_result,
                    'page_map': []
                }
            else:
                # Handle other response formats
                return {
                    'text': str(parsed_result),
                    'page_map': []
                }

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_name}: {str(e)}")
            raise
    
    def process_document(self, doc_url: str, doc_name: str) -> Dict[str, Any]:
        """Complete document processing pipeline"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                # Download from S3
                if not self.download_from_s3(doc_url, temp_path):
                    return {"success": False, "error": "Failed to download from S3"}

                # Parse with LlamaParse (now returns dict with text and page_map)
                parse_result = self.parse_pdf_with_llama(temp_path, doc_name)

                return {
                    "success": True,
                    "parsed_content": parse_result['text'],
                    "page_map": parse_result['page_map'],
                    "doc_name": doc_name,
                    "doc_url": doc_url
                }

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Document processing failed for {doc_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def chunk_text(self, text: str, chunk_size: int = 600, overlap: int = 150) -> List[str]:
        """
        Split text into overlapping chunks optimized for educational content.

        Smaller chunks (600 chars vs 1000) provide better precision for educational Q&A:
        - Educational content has focused concepts per paragraph
        - Students ask specific questions that need specific answers
        - Reduces "noise" from unrelated content in same chunk
        - 25% overlap maintains context between chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary for better semantic coherence
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size - 100:
                    end = sentence_end + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    def chunk_text_with_pages(self, text: str, page_map: List[Dict[str, Any]],
                              chunk_size: int = 600, overlap: int = 150) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks with page number tracking.
        Optimized for educational content with smaller chunks for better precision.
        """
        if len(text) <= chunk_size:
            # Single chunk - find its page number
            page_num = self._find_page_for_position(0, page_map)
            return [{
                'text': text,
                'page_number': page_num,
                'start_pos': 0,
                'end_pos': len(text)
            }]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size - 100:
                    end = sentence_end + 1

            chunk_text = text[start:end].strip()
            if chunk_text:
                # Find the page number for this chunk (use start position)
                page_num = self._find_page_for_position(start, page_map)

                chunks.append({
                    'text': chunk_text,
                    'page_number': page_num,
                    'start_pos': start,
                    'end_pos': end
                })

            start = end - overlap

        return chunks

    def _find_page_for_position(self, position: int, page_map: List[Dict[str, Any]]) -> Optional[int]:
        """Find which page a text position belongs to"""
        if not page_map:
            return None

        for page_info in page_map:
            if page_info['start'] <= position <= page_info['end']:
                return page_info['page']

        # If not found, return the last page (position might be at the very end)
        return page_map[-1]['page'] if page_map else None
    
    def generate_document_summary(self, content: str, doc_name: str, post_name: str) -> str:
        """Generate a comprehensive summary of the document using OpenAI"""
        try:
            # Truncate content if too long for API
            max_content_length = 12000  # Leave room for prompt
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            
            prompt = f"""
            Please provide a comprehensive summary of this document titled '{doc_name}' (Post: '{post_name}').
            
            Include the following in your summary:
            1. Main topic and purpose of the document
            2. Key concepts, themes, or subject areas covered
            3. Important details, data, or findings
            4. Target audience or context
            5. Any specific terminology or technical concepts
            
            Document content:
            {content}
            
            Provide a detailed summary that would help someone understand the document's content and context:
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.1
            )
            
            summary = response.choices[0].message.content
            if summary:
                summary = summary.strip()
            else:
                summary = f"Summary generation failed for {doc_name}"
            logger.info(f"Generated summary for {doc_name}: {len(summary)} characters")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary for {doc_name}: {str(e)}")
            # Return a basic summary as fallback
            return f"Document: {doc_name} (Post: {post_name}). Content preview: {content[:500]}..."
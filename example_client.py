#!/usr/bin/env python3
"""
RAG Study Chat API Example Client

This is a simple example showing how to use the RAG Study Chat API
for common use cases like creating chat sessions and asking questions.

Usage:
    python example_client.py
"""

import requests
import json
from typing import Dict, List, Optional

class RAGChatClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def get_courses(self) -> List[Dict]:
        """Get all available courses"""
        response = self.session.get(f"{self.base_url}/courses")
        response.raise_for_status()
        return response.json()
    
    def get_course_documents(self, course_id: int) -> Dict:
        """Get documents for a specific course"""
        response = self.session.get(f"{self.base_url}/courses/{course_id}/documents")
        response.raise_for_status()
        return response.json()
    
    def create_chat_session(self, user_email: str, course_id: int, session_name: str) -> Dict:
        """Create a new chat session"""
        payload = {
            "user_email": user_email,
            "course_id": course_id,
            "session_name": session_name
        }
        response = self.session.post(f"{self.base_url}/chat/sessions", json=payload)
        response.raise_for_status()
        return response.json()
    
    def send_message(self, session_id: int, message: str) -> Dict:
        """Send a message and get AI response"""
        payload = {
            "session_id": session_id,
            "content": message
        }
        response = self.session.post(f"{self.base_url}/chat/message", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_session_messages(self, session_id: int) -> List[Dict]:
        """Get all messages in a session"""
        response = self.session.get(f"{self.base_url}/chat/sessions/{session_id}/messages")
        response.raise_for_status()
        return response.json()
    
    def get_user_sessions(self, user_email: str) -> List[Dict]:
        """Get all sessions for a user"""
        response = self.session.get(f"{self.base_url}/chat/sessions/{user_email}")
        response.raise_for_status()
        return response.json()

def example_usage():
    """Example usage of the RAG Chat API"""
    
    # Initialize client
    client = RAGChatClient()
    
    print("🚀 RAG Study Chat API Example")
    print("=" * 40)
    
    try:
        # 1. Get available courses
        print("\n📚 Getting available courses...")
        courses = client.get_courses()
        print(f"Found {len(courses)} courses")
        
        if not courses:
            print("❌ No courses available")
            return
        
        # Display first few courses
        for i, course in enumerate(courses[:5]):
            print(f"  {i+1}. {course['subject']} ({course['grade']}) - ID: {course['id']}")
        
        # 2. Select a course (use first one for demo)
        selected_course = courses[0]
        course_id = selected_course['id']
        
        print(f"\n🎯 Selected course: {selected_course['subject']} (ID: {course_id})")
        
        # 3. Check course documents
        print("\n📄 Checking course documents...")
        docs_info = client.get_course_documents(course_id)
        doc_count = len(docs_info.get('documents', []))
        indexed_chunks = docs_info.get('indexed_chunks', 0)
        
        print(f"Documents: {doc_count}, Indexed chunks: {indexed_chunks}")
        
        if indexed_chunks == 0:
            print("⚠️  No indexed content found. You may need to process documents first.")
            print("   Use: POST /courses/{course_id}/process-documents")
        
        # 4. Create a chat session
        print("\n💬 Creating chat session...")
        user_email = "demo@example.com"
        session_name = f"Demo Session - {selected_course['subject']}"
        
        session = client.create_chat_session(user_email, course_id, session_name)
        session_id = session['id']
        
        print(f"Created session: {session_name} (ID: {session_id})")
        
        # 5. Send some example messages
        example_questions = [
            "Hello! Can you help me understand this course?",
            "What are the main topics covered in the course materials?",
            "Can you summarize the key concepts from the documents?",
            "What should I focus on when studying this subject?"
        ]
        
        print("\n🤖 Starting conversation...")
        
        for i, question in enumerate(example_questions, 1):
            print(f"\n👤 Question {i}: {question}")
            
            try:
                response = client.send_message(session_id, question)
                
                ai_message = response['message']
                sources = response.get('sources', [])
                
                # Display AI response (truncated for readability)
                if len(ai_message) > 200:
                    display_message = ai_message[:200] + "..."
                else:
                    display_message = ai_message
                
                print(f"🤖 AI Response: {display_message}")
                
                if sources:
                    print(f"📚 Sources: {[s['doc_name'] for s in sources]}")
                
            except requests.exceptions.HTTPError as e:
                print(f"❌ Error sending message: {e}")
                if e.response.status_code == 500:
                    print("   This might be due to missing OpenAI API key or unprocessed documents")
        
        # 6. Get conversation history
        print(f"\n📜 Getting conversation history...")
        messages = client.get_session_messages(session_id)
        
        user_messages = [m for m in messages if m['message_type'] == 'user']
        ai_messages = [m for m in messages if m['message_type'] == 'assistant']
        
        print(f"Total messages: {len(messages)} ({len(user_messages)} user, {len(ai_messages)} AI)")
        
        # 7. Show user's all sessions
        print(f"\n👤 All sessions for {user_email}:")
        user_sessions = client.get_user_sessions(user_email)
        
        for session in user_sessions:
            print(f"  - {session['session_name']} (ID: {session['id']}) - {session['created_at']}")
        
        print("\n✅ Example completed successfully!")
        print("\n💡 Tips:")
        print("   - Make sure documents are processed for better responses")
        print("   - Use specific questions related to your course content")
        print("   - Check the sources in AI responses for reference")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on http://localhost:8000")
    except requests.exceptions.HTTPError as e:
        print(f"❌ API Error: {e}")
        if e.response:
            try:
                error_detail = e.response.json()
                print(f"   Details: {error_detail}")
            except:
                print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def interactive_chat():
    """Interactive chat session"""
    client = RAGChatClient()
    
    print("\n🎮 Interactive Chat Mode")
    print("=" * 30)
    
    try:
        # Get courses
        courses = client.get_courses()
        if not courses:
            print("❌ No courses available")
            return
        
        # Let user select course
        print("\nAvailable courses:")
        for i, course in enumerate(courses):
            print(f"  {i+1}. {course['subject']} ({course['grade']}) - ID: {course['id']}")
        
        while True:
            try:
                choice = int(input(f"\nSelect course (1-{len(courses)}): ")) - 1
                if 0 <= choice < len(courses):
                    selected_course = courses[choice]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Create session
        user_email = input("Enter your email: ").strip()
        if not user_email:
            user_email = "interactive@example.com"
        
        session_name = f"Interactive - {selected_course['subject']}"
        session = client.create_chat_session(user_email, selected_course['id'], session_name)
        session_id = session['id']
        
        print(f"\n✅ Created session: {session_name}")
        print("💬 Start chatting! (type 'quit' to exit)")
        print("-" * 40)
        
        # Interactive chat loop
        while True:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            try:
                print("🤖 AI is thinking...")
                response = client.send_message(session_id, user_input)
                
                print(f"🤖 AI: {response['message']}")
                
                sources = response.get('sources', [])
                if sources:
                    print(f"📚 Sources: {', '.join([s['doc_name'] for s in sources])}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main function"""
    print("RAG Study Chat API Example Client")
    print("=" * 40)
    
    mode = input("Choose mode:\n1. Example usage\n2. Interactive chat\nEnter choice (1 or 2): ").strip()
    
    if mode == "2":
        interactive_chat()
    else:
        example_usage()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Content investigation script to understand what's in course 178
"""

import requests
import json

def investigate_content():
    base_url = "http://localhost:8000"
    course_id = 178
    
    print("🔍 INVESTIGATING COURSE 178 CONTENT")
    print("=" * 50)
    
    # 1. Get course info
    print("\n1. Course Information:")
    response = requests.get(f"{base_url}/courses?limit=1")
    if response.status_code == 200:
        courses = [c for c in response.json() if c['id'] == course_id]
        if courses:
            course = courses[0]
            print(f"   Subject: {course['subject']}")
            print(f"   Grade: {course['grade']}")
            print(f"   Category: {course['category']}")
    
    # 2. Test with a specific AP CS question
    print("\n2. Testing with AP Computer Science specific question:")
    
    # Create a test session
    session_data = {
        "user_email": "debug@test.com",
        "course_id": course_id,
        "session_name": "Content Debug Session"
    }
    
    response = requests.post(f"{base_url}/chat/sessions", json=session_data)
    if response.status_code == 200:
        session_id = response.json()['id']
        print(f"   ✅ Created session: {session_id}")
        
        # Test with AP CS specific questions
        test_questions = [
            "What is object-oriented programming?",
            "Explain inheritance in Java",
            "What are arrays and how do you use them?",
            "What is a for loop?",
            "Explain methods and parameters in Java"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n   Question {i}: {question}")
            
            message_data = {
                "session_id": session_id,
                "content": question
            }
            
            response = requests.post(f"{base_url}/chat/message", json=message_data)
            if response.status_code == 200:
                chat_response = response.json()
                message = chat_response['message']
                sources = chat_response['sources']
                
                print(f"   Response length: {len(message)} chars")
                print(f"   Sources: {len(sources)}")
                
                # Check if response contains AP CS content
                cs_keywords = ['java', 'programming', 'object', 'class', 'method', 'variable', 'array', 'loop']
                rag_keywords = ['retrieval', 'augmented', 'generation', 'embeddings', 'vector']
                
                message_lower = message.lower()
                cs_count = sum(1 for keyword in cs_keywords if keyword in message_lower)
                rag_count = sum(1 for keyword in rag_keywords if keyword in message_lower)
                
                print(f"   CS keywords found: {cs_count}")
                print(f"   RAG keywords found: {rag_count}")
                
                if rag_count > cs_count:
                    print("   ⚠️  Response seems to be about RAG, not Computer Science!")
                
                # Show first 200 chars
                print(f"   Preview: {message[:200]}...")
                
                if sources:
                    print("   Source details:")
                    for source in sources:
                        print(f"     - Doc: {source['doc_name']}")
                        print(f"       Similarity: {source.get('similarity_score', 'N/A')}")
            else:
                print(f"   ❌ Failed to get response: {response.status_code}")
            
            print()
        
        # Clean up
        requests.delete(f"{base_url}/chat/sessions/{session_id}")
        print(f"   🧹 Cleaned up session {session_id}")
    
    print("\n" + "=" * 50)
    print("🎯 INVESTIGATION COMPLETE")

if __name__ == "__main__":
    investigate_content()

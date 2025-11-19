#!/usr/bin/env python3
"""
Quick test to verify RAG improvements
"""
import requests
import json

def quick_test():
    base_url = "http://localhost:8000"
    
    print("🧪 QUICK RAG TEST")
    print("=" * 40)
    
    # Create session
    session_data = {
        "user_email": "quicktest@test.com",
        "course_id": 178,
        "session_name": "Quick Test"
    }
    
    response = requests.post(f"{base_url}/chat/sessions", json=session_data)
    if response.status_code == 200:
        session_id = response.json()['id']
        print(f"✅ Created session: {session_id}")
        
        # Test question
        question = "What is object-oriented programming in Java?"
        message_data = {
            "session_id": session_id,
            "content": question
        }
        
        print(f"\n📝 Question: {question}")
        response = requests.post(f"{base_url}/chat/message", json=message_data)
        if response.status_code == 200:
            chat_response = response.json()
            message = chat_response['message']
            sources = chat_response['sources']
            
            print(f"✅ Response received ({len(message)} chars)")
            print(f"📚 Sources: {len(sources)}")
            
            # Check content quality
            message_lower = message.lower()
            good_keywords = ['java', 'object', 'class', 'programming', 'encapsulation', 'inheritance']
            bad_keywords = ['retrieval', 'augmented', 'embedding', 'vector database']
            
            good_count = sum(1 for word in good_keywords if word in message_lower)
            bad_count = sum(1 for word in bad_keywords if word in message_lower)
            
            print(f"✅ CS keywords: {good_count}")
            print(f"⚠️  RAG keywords: {bad_count}")
            
            print(f"\n📖 Response preview:")
            print(f"   {message[:300]}...")
            
            if good_count > bad_count:
                print("\n🎉 SUCCESS: Response appears to be about Computer Science!")
            else:
                print("\n⚠️  WARNING: Response may still contain irrelevant content")
        
        # Cleanup
        requests.delete(f"{base_url}/chat/sessions/{session_id}")
        print(f"\n🧹 Session {session_id} cleaned up")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    quick_test()

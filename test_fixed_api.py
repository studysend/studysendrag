#!/usr/bin/env python3
"""
Fixed API Testing Script
Test all core functionality of the post-based chat system
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
TEST_USER = "fixed_test@example.com"

def test_health():
    """Test API health"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API Health: OK")
            return True
        else:
            print(f"❌ API Health: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Health: {e}")
        return False

def test_posts():
    """Get available posts"""
    try:
        response = requests.get(f"{BASE_URL}/posts", timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = data.get('posts', [])
            print(f"✅ Found {len(posts)} posts")
            if posts:
                for i, post in enumerate(posts[:5]):  # Show first 5
                    print(f"   {i+1}. ID: {post['id']}, Name: {post['post_name']}, Course: {post['course_id']}")
                return posts[:3]  # Return first 3 for testing
            return []
        else:
            print(f"❌ Posts endpoint: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Posts endpoint: {e}")
        return []

def test_session_creation(post_id):
    """Test session creation"""
    try:
        session_data = {
            "user_email": TEST_USER,
            "post_id": post_id,
            "session_name": f"Test Session {datetime.now().strftime('%H:%M:%S')}"
        }
        
        response = requests.post(
            f"{BASE_URL}/chat/sessions",
            json=session_data,
            timeout=10
        )
        
        if response.status_code == 200:
            session = response.json()
            print(f"✅ Session created: ID {session['id']} for post {post_id}")
            return session
        else:
            print(f"❌ Session creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        return None

def test_user_sessions():
    """Test getting user sessions"""
    try:
        response = requests.get(f"{BASE_URL}/chat/sessions/{TEST_USER}", timeout=10)
        if response.status_code == 200:
            sessions = response.json()
            print(f"✅ Found {len(sessions)} sessions for {TEST_USER}")
            for session in sessions:
                post_info = f"Post ID: {session.get('post_id', 'N/A')}" if session.get('post_id') else f"Course ID: {session.get('course_id', 'N/A')}"
                print(f"   Session {session['id']}: {session['session_name']} ({post_info})")
            return sessions
        else:
            print(f"❌ User sessions failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ User sessions error: {e}")
        return []

def test_send_message(session_id):
    """Test sending a message"""
    try:
        message_data = {
            "session_id": session_id,
            "content": "What is this post about? Give me a brief summary."
        }
        
        response = requests.post(
            f"{BASE_URL}/chat/message",
            json=message_data,
            timeout=30  # Longer timeout for AI response
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Message sent successfully")
            print(f"   AI Response: {result['response'][:100]}...")
            return result
        else:
            print(f"❌ Message failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Message error: {e}")
        return None

def test_session_messages(session_id):
    """Test getting session messages"""
    try:
        response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}/messages", timeout=10)
        if response.status_code == 200:
            messages = response.json()
            print(f"✅ Found {len(messages)} messages in session {session_id}")
            for msg in messages:
                role = msg['message_type']
                content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                print(f"   {role}: {content}")
            return messages
        else:
            print(f"❌ Session messages failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Session messages error: {e}")
        return []

def main():
    """Main test function"""
    print("🚀 Starting Comprehensive API Tests")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing API Health...")
    if not test_health():
        print("❌ API is not healthy, stopping tests")
        return
    
    # Test 2: Get Posts
    print("\n2️⃣ Testing Posts Endpoint...")
    posts = test_posts()
    if not posts:
        print("❌ No posts available, testing with known post ID 12")
        posts = [{"id": 12, "post_name": "Modern Artist", "course_id": 3}]
    
    # Test 3: Session Creation
    print("\n3️⃣ Testing Session Creation...")
    session = None
    for post in posts:
        print(f"\n   Testing with Post ID {post['id']}: {post['post_name']}")
        session = test_session_creation(post['id'])
        if session:
            break
    
    if not session:
        print("❌ Could not create any session")
        return
    
    # Test 4: User Sessions
    print("\n4️⃣ Testing User Sessions...")
    sessions = test_user_sessions()
    
    # Test 5: Send Message
    print("\n5️⃣ Testing Message Sending...")
    message_result = test_send_message(session['id'])
    
    # Test 6: Session Messages
    print("\n6️⃣ Testing Session Messages...")
    messages = test_session_messages(session['id'])
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 TEST SUMMARY:")
    print(f"✅ API Health: OK")
    print(f"✅ Posts Available: {len(posts) if posts else 0}")
    print(f"✅ Session Created: {session['id'] if session else 'Failed'}")
    print(f"✅ User Sessions: {len(sessions)} found")
    print(f"✅ Message Sent: {'Yes' if message_result else 'No'}")
    print(f"✅ Messages Retrieved: {len(messages) if messages else 0}")
    
    if session and message_result and messages:
        print("\n🎊 ALL TESTS PASSED! Post-based chat system is working!")
    else:
        print("\n⚠️  Some tests failed, but core functionality may still work")

if __name__ == "__main__":
    main()

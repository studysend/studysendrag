#!/usr/bin/env python3
"""
Simple chat history test with better error handling
"""

import requests
import json
from datetime import datetime

def test_chat_history_simple():
    """Simple test for chat history functionality"""
    
    BASE_URL = "http://localhost:8000"
    
    print("🔍 Testing Chat History - Simple Version")
    print("=" * 40)
    
    try:
        # Test 1: Check health first
        print("1️⃣ Checking API health...")
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ API is healthy")
        else:
            print(f"   ❌ API health check failed: {response.status_code}")
            return
            
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return
    
    try:
        # Test 2: Get sessions with timeout
        print("2️⃣ Getting user sessions...")
        response = requests.get(f"{BASE_URL}/chat/sessions/test@example.com", timeout=10)
        
        if response.status_code == 200:
            sessions = response.json()
            print(f"   ✅ Found {len(sessions)} sessions")
            
            # Show first few sessions
            for i, session in enumerate(sessions[:2]):
                print(f"   Session {session['id']}: {session['session_name']}")
                print(f"   - Course: {session['course_id']}, Post: {session.get('post_id', 'None')}")
            
            # Test 3: Try to get messages for the first session
            if sessions:
                session_id = sessions[0]['id']
                print(f"\n3️⃣ Getting messages for session {session_id}...")
                
                try:
                    msg_response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}/messages", timeout=15)
                    
                    if msg_response.status_code == 200:
                        messages = msg_response.json()
                        print(f"   ✅ Found {len(messages)} messages")
                        
                        # Show first few messages
                        for i, msg in enumerate(messages[:2]):
                            content_preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                            print(f"   Message {i+1} ({msg['message_type']}): {content_preview}")
                            
                    elif msg_response.status_code == 404:
                        print(f"   ❌ Session not found")
                    else:
                        print(f"   ❌ Error getting messages: {msg_response.status_code}")
                        print(f"   Response: {msg_response.text[:100]}")
                        
                except requests.exceptions.Timeout:
                    print("   ⏰ Request timed out")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        else:
            print(f"   ❌ Failed to get sessions: {response.status_code}")
            print(f"   Response: {response.text[:100]}")
            
    except requests.exceptions.Timeout:
        print("   ⏰ Session request timed out")
    except Exception as e:
        print(f"   ❌ Error getting sessions: {e}")
    
    print("\n✅ Simple test completed!")

if __name__ == "__main__":
    test_chat_history_simple()

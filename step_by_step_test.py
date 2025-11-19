#!/usr/bin/env python3
"""
Step-by-step test of post-based chat functionality
"""

import subprocess
import json
import time

def run_curl(url, method='GET', data=None, timeout=30):
    """Run curl command and return response"""
    cmd = ['curl', '-s']
    if method == 'POST':
        cmd.extend(['-X', 'POST', '-H', 'Content-Type: application/json'])
        if data:
            cmd.extend(['-d', json.dumps(data)])
    cmd.extend(['--max-time', str(timeout), url])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
        return result.stdout
    except subprocess.TimeoutExpired:
        return None

def test_posts_step_by_step():
    """Test post-based functionality step by step"""
    
    BASE_URL = "http://localhost:8000"
    
    print("🧪 Step-by-Step Post Testing")
    print("=" * 40)
    
    # Step 1: Check API health
    print("1️⃣ Checking API health...")
    health_response = run_curl(f"{BASE_URL}/health", timeout=5)
    if health_response and "healthy" in health_response:
        print("   ✅ API is healthy")
    else:
        print("   ❌ API health check failed")
        return
    
    # Step 2: Test with known post IDs
    test_posts = [
        {"id": 12, "name": "Modern Artist"},
        {"id": 17, "name": "Test1"}
    ]
    
    for post in test_posts:
        post_id = post["id"]
        post_name = post["name"]
        
        print(f"\n2️⃣ Testing Post {post_id}: '{post_name}'")
        print("-" * 30)
        
        # Create session
        session_data = {
            "user_email": "test@example.com",
            "post_id": post_id,
            "session_name": f"Test {post_name} Summary"
        }
        
        print("   Creating session...")
        session_response = run_curl(f"{BASE_URL}/chat/sessions", 'POST', session_data, 30)
        
        if session_response:
            try:
                session_json = json.loads(session_response)
                session_id = session_json.get('id')
                
                if session_id:
                    print(f"   ✅ Session created: ID {session_id}")
                    
                    # Send a message
                    message_data = {
                        "session_id": session_id,
                        "content": f"Please summarize what this post '{post_name}' is about. What are the main topics?"
                    }
                    
                    print("   Sending message...")
                    chat_response = run_curl(f"{BASE_URL}/chat/message", 'POST', message_data, 60)
                    
                    if chat_response:
                        try:
                            chat_json = json.loads(chat_response)
                            message = chat_json.get('message', '')
                            sources = chat_json.get('sources', [])
                            
                            if message:
                                # Show first 150 characters of response
                                summary = message[:150] + "..." if len(message) > 150 else message
                                print(f"   ✅ AI Response: {summary}")
                                print(f"   📚 Sources found: {len(sources)}")
                            else:
                                print("   ❌ No message in response")
                                
                        except json.JSONDecodeError:
                            print("   ❌ Invalid JSON response from chat")
                    else:
                        print("   ⏰ Chat request timed out")
                        
                    # Check chat history
                    print("   Checking history...")
                    history_response = run_curl(f"{BASE_URL}/chat/sessions/{session_id}/messages", timeout=10)
                    
                    if history_response:
                        try:
                            history_json = json.loads(history_response)
                            if isinstance(history_json, list):
                                print(f"   ✅ History retrieved: {len(history_json)} messages")
                            else:
                                print("   ❌ Invalid history format")
                        except json.JSONDecodeError:
                            print("   ❌ Invalid JSON in history response")
                    else:
                        print("   ⏰ History request timed out")
                        
                else:
                    print("   ❌ No session ID in response")
                    
            except json.JSONDecodeError:
                print("   ❌ Invalid JSON response from session creation")
                
        else:
            print("   ⏰ Session creation timed out")
        
        time.sleep(2)  # Small delay between tests
    
    print(f"\n🎉 Testing completed!")

if __name__ == "__main__":
    test_posts_step_by_step()

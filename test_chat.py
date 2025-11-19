#!/usr/bin/env python3
"""
Test script for chat functionality
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_create_session():
    """Test creating a new session first"""
    print("Testing session creation...")
    
    try:
        session_data = {
            "user_email": "test@example.com",
            "post_id": 7,
            "session_name": "Test Chat Session"
        }
        
        response = requests.post(f"{BASE_URL}/chat/sessions", json=session_data, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session created successfully! Session ID: {data['id']}")
            return data['id']
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_messages_endpoint(session_id=None):
    """Test the messages endpoint that was failing"""
    print("Testing chat messages endpoint...")
    
    try:
        # Use provided session_id or create a new one
        if not session_id:
            session_id = test_create_session()
            if not session_id:
                return False, None
                
        # Test getting messages for the session
        response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}/messages", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Handle both old format (direct array) and new format (object with messages)
            if isinstance(data, list):
                messages = data
            else:
                messages = data.get('messages', [])
            
            print(f"✅ Messages endpoint working! Found {len(messages)} messages")
            if messages:
                print("Sample message:")
                print(json.dumps(messages[0], indent=2))
            return True, session_id
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False, session_id
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, session_id

def test_send_message(session_id):
    """Test sending a new message"""
    print("\nTesting message sending...")
    
    try:
        message_data = {
            "session_id": session_id,
            "content": "Test message - can you help me with Python?"
        }
        
        response = requests.post(
            f"{BASE_URL}/chat/message",
            json=message_data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Message sent successfully!")
            print(f"Response: {data.get('message', '')[:100]}...")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_document_summary(session_id):
    """Test requesting a document summary"""
    print("\nTesting document summary feature...")
    
    try:
        # Test different summary request phrases
        summary_phrases = [
            "Can you provide a summary of this document?",
            "Give me an overview of the main points",
            "What are the key concepts in this document?"
        ]
        
        for i, phrase in enumerate(summary_phrases):
            print(f"\n  Testing phrase {i+1}: '{phrase}'")
            
            message_data = {
                "session_id": session_id,
                "content": phrase
            }
            
            response = requests.post(
                f"{BASE_URL}/chat/message",
                json=message_data,
                timeout=60  # Longer timeout for summary generation
            )
            
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                message_preview = data.get('message', '')[:150]
                print(f"  ✅ Response: {message_preview}...")
                
                # Check if it's a summary response
                if data.get('type') == 'summary' or 'document' in message_preview.lower():
                    print(f"  ✅ Summary detected for phrase {i+1}")
                    return True
            else:
                print(f"  ❌ Error: {response.status_code} - {response.text}")
        
        return True
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("🚀 Starting chat functionality tests...")
    
    # Test 1: Messages endpoint (will create a session)
    messages_ok, session_id = test_messages_endpoint()
    
    # Test 2: Send regular message to the same session
    if messages_ok and session_id:
        send_ok = test_send_message(session_id)
        
        # Test 3: Test document summary feature
        if send_ok:
            print("\nTesting document summary feature...")
            summary_ok = test_document_summary(session_id)
            
            # Test 4: Get messages again to see both messages
            if summary_ok:
                print("\nTesting messages endpoint again after summary...")
                test_messages_endpoint(session_id)
    
    print("\n✨ Tests completed!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script to generate document summaries for all available PDFs
and store results in JSON format
"""

import requests
import json
import time
from datetime import datetime
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8000"

def get_available_posts():
    """Get all posts with documents from the database"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        cur.execute('''
            SELECT id, post_name, doc_name, course_id 
            FROM post 
            WHERE doc_name IS NOT NULL 
            ORDER BY id
        ''')
        posts = cur.fetchall()
        cur.close()
        conn.close()
        
        return [
            {
                'post_id': post[0],
                'post_name': post[1],
                'doc_name': post[2],
                'course_id': post[3]
            }
            for post in posts
        ]
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return []

def create_session(post_id, post_name):
    """Create a new chat session for the given post"""
    try:
        session_data = {
            "user_email": "summary_test@example.com",
            "post_id": post_id,
            "session_name": f"Summary Test - {post_name}"
        }
        
        response = requests.post(f"{BASE_URL}/chat/sessions", json=session_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session created for post {post_id}: Session ID {data['id']}")
            return data['id']
        else:
            print(f"❌ Failed to create session for post {post_id}: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception creating session for post {post_id}: {e}")
        return None

def request_document_summary(session_id, post_id):
    """Request a document summary for the given session"""
    try:
        # Test different summary request phrases
        summary_phrases = [
            "Can you provide a comprehensive summary of this document?",
            "Give me a detailed overview of the main points in this document",
            "What are the key concepts and findings in this document?",
            "Summarize the document content for me",
            "Provide a summary of the document"
        ]
        
        # Use the first phrase for consistent results
        message_data = {
            "session_id": session_id,
            "content": summary_phrases[0]
        }
        
        print(f"  Requesting summary for post {post_id}...")
        response = requests.post(
            f"{BASE_URL}/chat/message",
            json=message_data,
            timeout=120  # Longer timeout for summary generation
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Summary generated successfully")
            return {
                'success': True,
                'summary_content': data.get('message', ''),
                'response_type': data.get('type', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'request_phrase': summary_phrases[0]
            }
        else:
            print(f"  ❌ Error generating summary: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text}",
                'timestamp': datetime.now().isoformat(),
                'request_phrase': summary_phrases[0]
            }
            
    except Exception as e:
        print(f"  ❌ Exception requesting summary for post {post_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'request_phrase': summary_phrases[0] if 'summary_phrases' in locals() else 'Unknown'
        }

def test_all_document_summaries():
    """Test document summaries for all available PDFs"""
    print("🚀 Starting comprehensive document summary testing...")
    
    # Get all available posts
    posts = get_available_posts()
    if not posts:
        print("❌ No posts found with documents")
        return
    
    print(f"Found {len(posts)} posts with documents to test")
    
    results = {
        'test_metadata': {
            'start_time': datetime.now().isoformat(),
            'total_documents': len(posts),
            'base_url': BASE_URL
        },
        'summary_results': []
    }
    
    successful_summaries = 0
    failed_summaries = 0
    
    for i, post in enumerate(posts, 1):
        print(f"\n--- Testing {i}/{len(posts)}: Post ID {post['post_id']} ---")
        print(f"Document: {post['doc_name']}")
        print(f"Post Name: {post['post_name']}")
        
        # Create session for this post
        session_id = create_session(post['post_id'], post['post_name'])
        
        if not session_id:
            result = {
                'post_id': post['post_id'],
                'post_name': post['post_name'],
                'doc_name': post['doc_name'],
                'course_id': post['course_id'],
                'session_id': None,
                'summary_result': {
                    'success': False,
                    'error': 'Failed to create session',
                    'timestamp': datetime.now().isoformat()
                }
            }
            results['summary_results'].append(result)
            failed_summaries += 1
            continue
        
        # Request document summary
        summary_result = request_document_summary(session_id, post['post_id'])
        
        # Store complete result
        result = {
            'post_id': post['post_id'],
            'post_name': post['post_name'],
            'doc_name': post['doc_name'],
            'course_id': post['course_id'],
            'session_id': session_id,
            'summary_result': summary_result
        }
        
        results['summary_results'].append(result)
        
        if summary_result['success']:
            successful_summaries += 1
            print(f"  ✅ Summary preview: {summary_result['summary_content'][:100]}...")
        else:
            failed_summaries += 1
        
        # Small delay between requests to avoid overwhelming the API
        if i < len(posts):
            print("  Waiting before next request...")
            time.sleep(2)
    
    # Add final metadata
    results['test_metadata'].update({
        'end_time': datetime.now().isoformat(),
        'successful_summaries': successful_summaries,
        'failed_summaries': failed_summaries,
        'success_rate': f"{(successful_summaries / len(posts) * 100):.1f}%" if posts else "0%"
    })
    
    # Save results to JSON file
    output_file = f"document_summaries_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Testing completed!")
        print(f"📊 Results Summary:")
        print(f"  • Total documents tested: {len(posts)}")
        print(f"  • Successful summaries: {successful_summaries}")
        print(f"  • Failed summaries: {failed_summaries}")
        print(f"  • Success rate: {results['test_metadata']['success_rate']}")
        print(f"  • Results saved to: {output_file}")
        
        # Show sample of successful summaries
        successful_results = [r for r in results['summary_results'] if r['summary_result']['success']]
        if successful_results:
            print(f"\n📝 Sample successful summaries:")
            for result in successful_results[:3]:  # Show first 3
                summary_preview = result['summary_result']['summary_content'][:150]
                print(f"  • {result['doc_name']}: {summary_preview}...")
        
        return results
        
    except Exception as e:
        print(f"❌ Error saving results to JSON: {e}")
        return results

def analyze_results(results):
    """Analyze the summary results and provide insights"""
    if not results or not results.get('summary_results'):
        print("No results to analyze")
        return
    
    print(f"\n📈 Detailed Analysis:")
    
    # Group by document type
    doc_types = {}
    for result in results['summary_results']:
        doc_name = result['doc_name']
        if doc_name:
            ext = doc_name.split('.')[-1].lower()
            if ext not in doc_types:
                doc_types[ext] = {'total': 0, 'successful': 0}
            doc_types[ext]['total'] += 1
            if result['summary_result']['success']:
                doc_types[ext]['successful'] += 1
    
    print(f"  📄 Results by document type:")
    for ext, stats in doc_types.items():
        success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"    • .{ext}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
    
    # Show error patterns
    errors = [r['summary_result'].get('error', '') for r in results['summary_results'] 
              if not r['summary_result']['success'] and r['summary_result'].get('error')]
    
    if errors:
        print(f"  ❌ Common error patterns:")
        error_counts = {}
        for error in errors:
            error_type = error.split(':')[0] if ':' in error else error[:50]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    • {error_type}: {count} occurrences")

if __name__ == "__main__":
    # Run the comprehensive test
    results = test_all_document_summaries()
    
    if results:
        # Analyze the results
        analyze_results(results)
        
        # Option to view specific results
        print(f"\n💡 Tip: Check the generated JSON file for complete summary content and metadata!")

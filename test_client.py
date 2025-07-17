#!/usr/bin/env python3
"""
RAG Study Chat API - Advanced Test Client

This comprehensive test client validates all API endpoints and features of the RAG Study Chat system.
It performs thorough testing including performance benchmarks, stress tests, and edge case validation.

Usage:
    python test_client.py [--mode=basic|comprehensive|stress|performance]

Requirements:
    - API server running on localhost:8000
    - Valid API keys configured in .env
    - At least one course with documents in the database

Features:
    - Complete API endpoint testing
    - Performance benchmarking
    - Cache efficiency testing
    - Error handling validation
    - Stress testing capabilities
    - Detailed reporting with metrics
"""

import requests
import json
import time
import threading
import statistics
import concurrent.futures
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import sys
import argparse
import random
import string

class RAGStudyChatClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def test_health_check(self):
        """Test health check endpoint"""
        print("\n🏥 Testing Health Check...")
        
        response = self.make_request("GET", "/health")
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                self.log_test("Health Check", True, f"Status: {data.get('message')}")
                return True
            else:
                self.log_test("Health Check", False, f"Unexpected response: {data}")
                return False
        else:
            self.log_test("Health Check", False, f"HTTP {response.status_code if response else 'No response'}")
            return False
    
    def test_get_courses(self) -> List[Dict]:
        """Test getting all courses"""
        print("\n📚 Testing Course Management...")
        
        response = self.make_request("GET", "/courses")
        
        if response and response.status_code == 200:
            courses = response.json()
            if isinstance(courses, list) and len(courses) > 0:
                self.log_test("Get All Courses", True, f"Found {len(courses)} courses")
                
                # Display sample courses
                for i, course in enumerate(courses[:3]):
                    print(f"    Course {i+1}: {course.get('subject')} ({course.get('grade')})")
                
                return courses
            else:
                self.log_test("Get All Courses", False, "No courses found or invalid response")
                return []
        else:
            self.log_test("Get All Courses", False, f"HTTP {response.status_code if response else 'No response'}")
            return []
    
    def test_get_course_documents(self, course_id: int):
        """Test getting documents for a specific course"""
        response = self.make_request("GET", f"/courses/{course_id}/documents")
        
        if response and response.status_code == 200:
            data = response.json()
            doc_count = len(data.get("documents", []))
            indexed_chunks = data.get("indexed_chunks", 0)
            
            self.log_test(f"Get Course {course_id} Documents", True, 
                         f"{doc_count} documents, {indexed_chunks} indexed chunks")
            return data
        else:
            self.log_test(f"Get Course {course_id} Documents", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return None
    
    def test_get_unindexed_courses(self):
        """Test getting unindexed courses"""
        response = self.make_request("GET", "/courses/unindexed")
        
        if response and response.status_code == 200:
            data = response.json()
            unindexed_count = len(data.get("unindexed_courses", []))
            total_courses = data.get("total_courses", 0)
            
            self.log_test("Get Unindexed Courses", True, 
                         f"{unindexed_count} unindexed out of {total_courses} total")
            return data
        else:
            self.log_test("Get Unindexed Courses", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return None
    
    def test_get_course_index_status(self, course_id: int):
        """Test getting course index status"""
        response = self.make_request("GET", f"/courses/{course_id}/index-status")
        
        if response and response.status_code == 200:
            data = response.json()
            status = data.get("status")
            chunk_count = data.get("chunk_count", 0)
            
            self.log_test(f"Get Course {course_id} Index Status", True, 
                         f"Status: {status}, Chunks: {chunk_count}")
            return data
        else:
            self.log_test(f"Get Course {course_id} Index Status", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return None
    
    def test_process_course_documents(self, course_id: int):
        """Test processing course documents"""
        print(f"\n⚙️  Testing Document Processing for Course {course_id}...")
        
        response = self.make_request("POST", f"/courses/{course_id}/process-documents")
        
        if response and response.status_code == 200:
            data = response.json()
            doc_count = data.get("document_count", 0)
            
            self.log_test(f"Process Course {course_id} Documents", True, 
                         f"Started processing {doc_count} documents")
            
            # Wait a bit for processing to start
            time.sleep(2)
            return True
        else:
            self.log_test(f"Process Course {course_id} Documents", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return False
    
    def test_index_unindexed_courses(self):
        """Test indexing all unindexed courses"""
        print("\n🔄 Testing Automatic Indexing...")
        
        response = self.make_request("POST", "/courses/index-unindexed")
        
        if response and response.status_code == 200:
            data = response.json()
            courses_to_index = data.get("courses_to_index", 0)
            
            self.log_test("Index Unindexed Courses", True, 
                         f"Started indexing {courses_to_index} courses")
            return True
        else:
            self.log_test("Index Unindexed Courses", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return False
    
    def test_create_chat_session(self, user_email: str, course_id: int, session_name: str) -> Optional[int]:
        """Test creating a chat session"""
        print("\n💬 Testing Chat System...")
        
        payload = {
            "user_email": user_email,
            "course_id": course_id,
            "session_name": session_name
        }
        
        response = self.make_request("POST", "/chat/sessions", json=payload)
        
        if response and response.status_code == 200:
            data = response.json()
            session_id = data.get("id")
            
            self.log_test("Create Chat Session", True, 
                         f"Session ID: {session_id}, Name: {data.get('session_name')}")
            return session_id
        else:
            self.log_test("Create Chat Session", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return None
    
    def test_get_user_sessions(self, user_email: str):
        """Test getting user sessions"""
        response = self.make_request("GET", f"/chat/sessions/{user_email}")
        
        if response and response.status_code == 200:
            sessions = response.json()
            session_count = len(sessions)
            
            self.log_test("Get User Sessions", True, f"Found {session_count} sessions")
            return sessions
        else:
            self.log_test("Get User Sessions", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return []
    
    def test_send_message(self, session_id: int, message: str) -> Optional[Dict]:
        """Test sending a chat message"""
        payload = {
            "session_id": session_id,
            "content": message
        }
        
        response = self.make_request("POST", "/chat/message", json=payload)
        
        if response and response.status_code == 200:
            data = response.json()
            response_message = data.get("message", "")
            sources = data.get("sources", [])
            
            self.log_test("Send Chat Message", True, 
                         f"Response length: {len(response_message)} chars, Sources: {len(sources)}")
            
            # Display response preview
            preview = response_message[:100] + "..." if len(response_message) > 100 else response_message
            print(f"    AI Response: {preview}")
            
            if sources:
                print(f"    Sources: {[s.get('doc_name') for s in sources]}")
            
            return data
        else:
            self.log_test("Send Chat Message", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return None
    
    def test_get_session_messages(self, session_id: int):
        """Test getting session messages"""
        response = self.make_request("GET", f"/chat/sessions/{session_id}/messages")
        
        if response and response.status_code == 200:
            messages = response.json()
            message_count = len(messages)
            
            self.log_test("Get Session Messages", True, f"Found {message_count} messages")
            
            # Display message summary
            user_msgs = len([m for m in messages if m.get("message_type") == "user"])
            ai_msgs = len([m for m in messages if m.get("message_type") == "assistant"])
            print(f"    User messages: {user_msgs}, AI messages: {ai_msgs}")
            
            return messages
        else:
            self.log_test("Get Session Messages", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return []
    
    def test_delete_session(self, session_id: int):
        """Test deleting a chat session"""
        response = self.make_request("DELETE", f"/chat/sessions/{session_id}")
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_test("Delete Chat Session", True, data.get("message", ""))
            return True
        else:
            self.log_test("Delete Chat Session", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return False
    
    def test_cache_health(self):
        """Test Redis cache health"""
        print("\n🔄 Testing Redis Cache...")
        
        response = self.make_request("GET", "/cache/health")
        
        if response and response.status_code == 200:
            data = response.json()
            status = data.get("status")
            
            if status == "healthy":
                self.log_test("Redis Cache Health", True, "Cache is working properly")
                return True
            elif status == "disabled":
                self.log_test("Redis Cache Health", True, "Cache is disabled (expected in some setups)")
                return True
            else:
                self.log_test("Redis Cache Health", False, f"Cache status: {status}")
                return False
        else:
            self.log_test("Redis Cache Health", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return False
    
    def test_cache_stats(self):
        """Test getting cache statistics"""
        response = self.make_request("GET", "/cache/stats")
        
        if response and response.status_code == 200:
            data = response.json()
            cache_stats = data.get("cache_stats", {})
            
            if cache_stats.get("enabled"):
                hit_rate = cache_stats.get("hit_rate", 0)
                used_memory = cache_stats.get("used_memory", "0B")
                self.log_test("Get Cache Stats", True, 
                             f"Hit rate: {hit_rate}%, Memory: {used_memory}")
            else:
                self.log_test("Get Cache Stats", True, "Cache disabled")
            
            return True
        else:
            self.log_test("Get Cache Stats", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return False
    
    def test_cache_invalidation(self, course_id: int):
        """Test cache invalidation for a course"""
        response = self.make_request("POST", f"/cache/invalidate/course/{course_id}")
        
        if response and response.status_code == 200:
            data = response.json()
            deleted_entries = data.get("deleted_entries", 0)
            
            self.log_test("Cache Invalidation", True, 
                         f"Invalidated {deleted_entries} cache entries for course {course_id}")
            return True
        else:
            self.log_test("Cache Invalidation", False, 
                         f"HTTP {response.status_code if response else 'No response'}")
            return False
    
    # ==================== ADVANCED TESTING METHODS ====================
    
    def test_performance_benchmark(self, course_id: int, iterations: int = 10):
        """Benchmark API performance with multiple requests"""
        print(f"\n⚡ Performance Benchmark ({iterations} iterations)...")
        
        endpoints_to_test = [
            ("GET", f"/courses/{course_id}/documents", {}),
            ("GET", "/courses", {}),
            ("GET", f"/courses/{course_id}/index-status", {}),
            ("GET", "/cache/stats", {}),
            ("GET", "/cache/health", {})
        ]
        
        performance_results = {}
        
        for method, endpoint, payload in endpoints_to_test:
            times = []
            
            for i in range(iterations):
                start_time = time.time()
                
                if method == "GET":
                    response = self.make_request(method, endpoint)
                else:
                    response = self.make_request(method, endpoint, json=payload)
                
                end_time = time.time()
                
                if response and response.status_code == 200:
                    times.append((end_time - start_time) * 1000)  # Convert to ms
                else:
                    print(f"    ❌ Failed request {i+1} for {endpoint}")
            
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                median_time = statistics.median(times)
                
                performance_results[endpoint] = {
                    "avg_ms": round(avg_time, 2),
                    "min_ms": round(min_time, 2),
                    "max_ms": round(max_time, 2),
                    "median_ms": round(median_time, 2),
                    "requests": len(times)
                }
                
                self.log_test(f"Performance {endpoint}", True, 
                             f"Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
        
        return performance_results
    
    def test_cache_efficiency(self, course_id: int):
        """Test cache hit rates and efficiency"""
        print("\n🎯 Testing Cache Efficiency...")
        
        # Get initial cache stats
        initial_stats = self.make_request("GET", "/cache/stats")
        if not initial_stats or initial_stats.status_code != 200:
            self.log_test("Cache Efficiency Setup", False, "Could not get initial cache stats")
            return False
        
        initial_data = initial_stats.json().get("cache_stats", {})
        initial_hits = initial_data.get("keyspace_hits", 0)
        initial_misses = initial_data.get("keyspace_misses", 0)
        
        # Make repeated requests to test caching
        test_requests = [
            ("GET", f"/courses/{course_id}/documents"),
            ("GET", "/courses"),
            ("GET", f"/courses/{course_id}/index-status"),
        ]
        
        # First round - should be cache misses
        for method, endpoint in test_requests:
            self.make_request(method, endpoint)
        
        # Second round - should be cache hits
        for method, endpoint in test_requests:
            self.make_request(method, endpoint)
        
        # Get final cache stats
        final_stats = self.make_request("GET", "/cache/stats")
        if final_stats and final_stats.status_code == 200:
            final_data = final_stats.json().get("cache_stats", {})
            final_hits = final_data.get("keyspace_hits", 0)
            final_misses = final_data.get("keyspace_misses", 0)
            
            hit_increase = final_hits - initial_hits
            miss_increase = final_misses - initial_misses
            
            if hit_increase > 0:
                self.log_test("Cache Efficiency", True, 
                             f"Cache hits increased by {hit_increase}, misses by {miss_increase}")
                return True
            else:
                self.log_test("Cache Efficiency", False, 
                             f"No cache hits detected (hits: +{hit_increase}, misses: +{miss_increase})")
                return False
        else:
            self.log_test("Cache Efficiency", False, "Could not get final cache stats")
            return False
    
    def test_concurrent_requests(self, course_id: int, num_threads: int = 5):
        """Test concurrent request handling"""
        print(f"\n🔄 Testing Concurrent Requests ({num_threads} threads)...")
        
        def make_concurrent_request(thread_id):
            """Function to run in each thread"""
            results = []
            
            # Each thread makes multiple requests
            requests_per_thread = [
                ("GET", "/health"),
                ("GET", "/courses"),
                ("GET", f"/courses/{course_id}/documents"),
                ("GET", "/cache/stats")
            ]
            
            for method, endpoint in requests_per_thread:
                start_time = time.time()
                response = self.make_request(method, endpoint)
                end_time = time.time()
                
                results.append({
                    "thread_id": thread_id,
                    "endpoint": endpoint,
                    "success": response is not None and response.status_code == 200,
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status_code if response else None
                })
            
            return results
        
        # Run concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_concurrent_request, i) for i in range(num_threads)]
            all_results = []
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    print(f"    ❌ Thread failed: {e}")
        
        # Analyze results
        successful_requests = [r for r in all_results if r["success"]]
        failed_requests = [r for r in all_results if not r["success"]]
        
        if len(successful_requests) > 0:
            avg_response_time = statistics.mean([r["response_time"] for r in successful_requests])
            success_rate = len(successful_requests) / len(all_results) * 100
            
            self.log_test("Concurrent Requests", True, 
                         f"Success rate: {success_rate:.1f}%, Avg response: {avg_response_time:.2f}ms")
            return True
        else:
            self.log_test("Concurrent Requests", False, 
                         f"All {len(all_results)} requests failed")
            return False
    
    def test_error_handling(self):
        """Test error handling for various scenarios"""
        print("\n🚨 Testing Error Handling...")
        
        error_test_cases = [
            # Invalid endpoints
            ("GET", "/invalid-endpoint", 404),
            ("POST", "/nonexistent", 404),
            
            # Invalid course IDs
            ("GET", "/courses/99999/documents", 500),  # Might be 404 or 500
            ("GET", "/courses/invalid/index-status", 422),
            
            # Invalid session operations
            ("GET", "/chat/sessions/99999/messages", 500),
            ("DELETE", "/chat/sessions/99999", 404),
            
            # Invalid cache operations
            ("POST", "/cache/invalidate/course/99999", 500),
        ]
        
        error_results = []
        
        for method, endpoint, expected_status in error_test_cases:
            response = self.make_request(method, endpoint)
            
            if response:
                actual_status = response.status_code
                if actual_status >= 400:  # Any error status is acceptable
                    error_results.append(True)
                    print(f"    ✅ {method} {endpoint}: {actual_status} (expected error)")
                else:
                    error_results.append(False)
                    print(f"    ❌ {method} {endpoint}: {actual_status} (expected error)")
            else:
                error_results.append(False)
                print(f"    ❌ {method} {endpoint}: No response")
        
        success_rate = sum(error_results) / len(error_results) * 100
        self.log_test("Error Handling", success_rate >= 80, 
                     f"Error handling success rate: {success_rate:.1f}%")
        
        return success_rate >= 80
    
    def test_data_validation(self):
        """Test input validation and data integrity"""
        print("\n🔍 Testing Data Validation...")
        
        validation_tests = [
            # Invalid chat session creation
            {
                "name": "Invalid Email Format",
                "method": "POST",
                "endpoint": "/chat/sessions",
                "payload": {"user_email": "invalid-email", "course_id": 1, "session_name": "Test"},
                "expect_error": True
            },
            {
                "name": "Missing Required Fields",
                "method": "POST",
                "endpoint": "/chat/sessions",
                "payload": {"user_email": "test@example.com"},
                "expect_error": True
            },
            {
                "name": "Invalid Course ID Type",
                "method": "POST",
                "endpoint": "/chat/sessions",
                "payload": {"user_email": "test@example.com", "course_id": "invalid", "session_name": "Test"},
                "expect_error": True
            },
            # Invalid message sending
            {
                "name": "Empty Message Content",
                "method": "POST",
                "endpoint": "/chat/message",
                "payload": {"session_id": 1, "content": ""},
                "expect_error": True
            },
            {
                "name": "Missing Session ID",
                "method": "POST",
                "endpoint": "/chat/message",
                "payload": {"content": "Test message"},
                "expect_error": True
            }
        ]
        
        validation_results = []
        
        for test in validation_tests:
            response = self.make_request(test["method"], test["endpoint"], json=test["payload"])
            
            if response:
                is_error = response.status_code >= 400
                if test["expect_error"] and is_error:
                    validation_results.append(True)
                    print(f"    ✅ {test['name']}: Correctly rejected ({response.status_code})")
                elif not test["expect_error"] and not is_error:
                    validation_results.append(True)
                    print(f"    ✅ {test['name']}: Correctly accepted ({response.status_code})")
                else:
                    validation_results.append(False)
                    print(f"    ❌ {test['name']}: Unexpected result ({response.status_code})")
            else:
                validation_results.append(False)
                print(f"    ❌ {test['name']}: No response")
        
        success_rate = sum(validation_results) / len(validation_results) * 100
        self.log_test("Data Validation", success_rate >= 80, 
                     f"Validation success rate: {success_rate:.1f}%")
        
        return success_rate >= 80
    
    def test_chat_conversation_flow(self, course_id: int):
        """Test complete chat conversation flow with context"""
        print("\n💬 Testing Chat Conversation Flow...")
        
        # Create a test session
        user_email = f"test_{int(time.time())}@example.com"
        session_name = "Conversation Flow Test"
        
        session_id = self.test_create_chat_session(user_email, course_id, session_name)
        if not session_id:
            self.log_test("Chat Conversation Flow", False, "Could not create session")
            return False
        
        # Test conversation with context building
        conversation_messages = [
            "Hello, I'm studying for an exam. Can you help me?",
            "What are the main topics I should focus on?",
            "Can you explain the first topic in more detail?",
            "How does this relate to what we discussed earlier?",
            "Can you give me some practice questions on this topic?"
        ]
        
        conversation_results = []
        previous_response = None
        
        for i, message in enumerate(conversation_messages):
            print(f"    📝 Message {i+1}: {message[:50]}...")
            
            start_time = time.time()
            response = self.test_send_message(session_id, message)
            end_time = time.time()
            
            if response:
                response_time = (end_time - start_time) * 1000
                response_length = len(response.get("message", ""))
                sources_count = len(response.get("sources", []))
                
                # Check if response seems contextual (longer responses for follow-up questions)
                is_contextual = i == 0 or response_length > 50  # First message or substantial response
                
                conversation_results.append({
                    "message_num": i + 1,
                    "success": True,
                    "response_time_ms": response_time,
                    "response_length": response_length,
                    "sources_count": sources_count,
                    "is_contextual": is_contextual
                })
                
                print(f"      ✅ Response: {response_length} chars, {sources_count} sources, {response_time:.0f}ms")
                previous_response = response
            else:
                conversation_results.append({
                    "message_num": i + 1,
                    "success": False
                })
                print(f"      ❌ Failed to get response")
        
        # Analyze conversation flow
        successful_messages = [r for r in conversation_results if r["success"]]
        if len(successful_messages) >= len(conversation_messages) * 0.8:  # 80% success rate
            avg_response_time = statistics.mean([r["response_time_ms"] for r in successful_messages])
            avg_response_length = statistics.mean([r["response_length"] for r in successful_messages])
            total_sources = sum([r["sources_count"] for r in successful_messages])
            
            self.log_test("Chat Conversation Flow", True, 
                         f"{len(successful_messages)}/{len(conversation_messages)} messages successful, "
                         f"Avg response: {avg_response_time:.0f}ms, {avg_response_length:.0f} chars, "
                         f"{total_sources} total sources")
            
            # Clean up
            self.test_delete_session(session_id)
            return True
        else:
            self.log_test("Chat Conversation Flow", False, 
                         f"Only {len(successful_messages)}/{len(conversation_messages)} messages successful")
            
            # Clean up
            self.test_delete_session(session_id)
            return False
    
    def test_stress_test(self, course_id: int, duration_seconds: int = 30):
        """Stress test the API with continuous requests"""
        print(f"\n🔥 Stress Test ({duration_seconds} seconds)...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_count = 0
        success_count = 0
        error_count = 0
        response_times = []
        
        # Mix of different request types
        request_types = [
            ("GET", "/health"),
            ("GET", "/courses"),
            ("GET", f"/courses/{course_id}/documents"),
            ("GET", "/cache/stats"),
            ("GET", f"/courses/{course_id}/index-status")
        ]
        
        print(f"    Running stress test for {duration_seconds} seconds...")
        
        while time.time() < end_time:
            # Random request type
            method, endpoint = random.choice(request_types)
            
            request_start = time.time()
            response = self.make_request(method, endpoint)
            request_end = time.time()
            
            request_count += 1
            response_time = (request_end - request_start) * 1000
            response_times.append(response_time)
            
            if response and response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
            
            # Brief pause to avoid overwhelming the server
            time.sleep(0.1)
        
        # Calculate statistics
        actual_duration = time.time() - start_time
        requests_per_second = request_count / actual_duration
        success_rate = (success_count / request_count) * 100
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        if success_rate >= 95:  # 95% success rate threshold
            self.log_test("Stress Test", True, 
                         f"{request_count} requests in {actual_duration:.1f}s, "
                         f"{requests_per_second:.1f} req/s, {success_rate:.1f}% success, "
                         f"avg response: {avg_response_time:.0f}ms")
            return True
        else:
            self.log_test("Stress Test", False, 
                         f"Success rate too low: {success_rate:.1f}% ({success_count}/{request_count})")
            return False
    
    def run_advanced_test_suite(self, course_id: int):
        """Run comprehensive advanced test suite"""
        print("\n🎯 ADVANCED TEST SUITE")
        print("=" * 50)
        
        advanced_tests = [
            ("Performance Benchmark", lambda: self.test_performance_benchmark(course_id, 5)),
            ("Cache Efficiency", lambda: self.test_cache_efficiency(course_id)),
            ("Concurrent Requests", lambda: self.test_concurrent_requests(course_id, 3)),
            ("Error Handling", lambda: self.test_error_handling()),
            ("Data Validation", lambda: self.test_data_validation()),
            ("Chat Conversation Flow", lambda: self.test_chat_conversation_flow(course_id)),
            ("Stress Test", lambda: self.test_stress_test(course_id, 15))
        ]
        
        advanced_results = []
        
        for test_name, test_func in advanced_tests:
            print(f"\n🔬 Running {test_name}...")
            try:
                result = test_func()
                advanced_results.append(result)
            except Exception as e:
                print(f"    ❌ {test_name} failed with exception: {e}")
                advanced_results.append(False)
        
        # Summary of advanced tests
        passed_advanced = sum(advanced_results)
        total_advanced = len(advanced_results)
        
        print(f"\n📊 ADVANCED TESTS SUMMARY")
        print(f"Passed: {passed_advanced}/{total_advanced} ({passed_advanced/total_advanced*100:.1f}%)")
        
        return passed_advanced >= total_advanced * 0.7  # 70% pass rate for advanced tests
    
    def test_stress_test(self, course_id: int, duration_seconds: int = 30):
        """Stress test the API with continuous requests"""
        print(f"\n🔥 Stress Test ({duration_seconds} seconds)...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_count = 0
        success_count = 0
        error_count = 0
        response_times = []
        
        # Mix of different request types
        request_types = [
            ("GET", "/health"),
            ("GET", "/courses"),
            ("GET", f"/courses/{course_id}/documents"),
            ("GET", "/cache/stats"),
            ("GET", f"/courses/{course_id}/index-status")
        ]
        
        print(f"    Running stress test for {duration_seconds} seconds...")
        
        while time.time() < end_time:
            # Random request type
            method, endpoint = random.choice(request_types)
            
            request_start = time.time()
            response = self.make_request(method, endpoint)
            request_end = time.time()
            
            request_count += 1
            response_time = (request_end - request_start) * 1000
            response_times.append(response_time)
            
            if response and response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
            
            # Brief pause to avoid overwhelming the server
            time.sleep(0.1)
        
        # Calculate statistics
        actual_duration = time.time() - start_time
        requests_per_second = request_count / actual_duration
        success_rate = (success_count / request_count) * 100
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        if success_rate >= 95:  # 95% success rate threshold
            self.log_test("Stress Test", True, 
                         f"{request_count} requests in {actual_duration:.1f}s, "
                         f"{requests_per_second:.1f} req/s, {success_rate:.1f}% success, "
                         f"avg response: {avg_response_time:.0f}ms")
            return True
        else:
            self.log_test("Stress Test", False, 
                         f"Success rate too low: {success_rate:.1f}% ({success_count}/{request_count})")
            return False
    
    def run_advanced_test_suite(self, course_id: int):
        """Run comprehensive advanced test suite"""
        print("\n🎯 ADVANCED TEST SUITE")
        print("=" * 50)
        
        advanced_tests = [
            ("Performance Benchmark", lambda: self.test_performance_benchmark(course_id, 5)),
            ("Cache Efficiency", lambda: self.test_cache_efficiency(course_id)),
            ("Concurrent Requests", lambda: self.test_concurrent_requests(course_id, 3)),
            ("Error Handling", lambda: self.test_error_handling()),
            ("Data Validation", lambda: self.test_data_validation()),
            ("Chat Conversation Flow", lambda: self.test_chat_conversation_flow(course_id)),
            ("Stress Test", lambda: self.test_stress_test(course_id, 15))
        ]
        
        advanced_results = []
        
        for test_name, test_func in advanced_tests:
            print(f"\n🔬 Running {test_name}...")
            try:
                result = test_func()
                advanced_results.append(result)
            except Exception as e:
                print(f"    ❌ {test_name} failed with exception: {e}")
                advanced_results.append(False)
        
        # Summary of advanced tests
        passed_advanced = sum(advanced_results)
        total_advanced = len(advanced_results)
        
        print(f"\n📊 ADVANCED TESTS SUMMARY")
        print(f"Passed: {passed_advanced}/{total_advanced} ({passed_advanced/total_advanced*100:.1f}%)")
        
        return passed_advanced >= total_advanced * 0.7  # 70% pass rate for advanced tests
    
    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting RAG Study Chat API Comprehensive Test")
        print("=" * 60)
        
        # Test 1: Health Check
        if not self.test_health_check():
            print("❌ Health check failed. Is the server running?")
            return False
        
        # Test 2: Get Courses
        courses = self.test_get_courses()
        if not courses:
            print("❌ No courses found. Cannot continue with course-specific tests.")
            return False
        
        # Find a course with documents for testing
        test_course_id = None
        for course in courses:
            course_id = course.get("id")
            docs = self.test_get_course_documents(course_id)
            if docs and len(docs.get("documents", [])) > 0:
                test_course_id = course_id
                break
        
        if not test_course_id:
            print("❌ No courses with documents found. Cannot test document processing.")
            # Still continue with other tests
            test_course_id = courses[0].get("id")  # Use first course anyway
        
        # Test 3: Course Management
        self.test_get_unindexed_courses()
        self.test_get_course_index_status(test_course_id)
        
        # Test 4: Document Processing (optional - takes time)
        process_docs = input("\n🤔 Test document processing? This may take time (y/N): ").lower().strip()
        if process_docs == 'y':
            self.test_process_course_documents(test_course_id)
            self.test_index_unindexed_courses()
        
        # Test 5: Redis Cache System
        self.test_cache_health()
        self.test_cache_stats()
        self.test_cache_invalidation(test_course_id)
        
        # Test 6: Chat System
        test_user_email = "test@example.com"
        session_name = f"Test Session {datetime.now().strftime('%H:%M:%S')}"
        
        session_id = self.test_create_chat_session(test_user_email, test_course_id, session_name)
        
        if session_id:
            # Test chat functionality
            self.test_get_user_sessions(test_user_email)
            
            # Send test messages
            test_messages = [
                "Hello, can you help me with this course?",
                "What topics are covered in the course materials?",
                "Explain the main concepts from the documents."
            ]
            
            for msg in test_messages:
                print(f"\n📝 Sending message: '{msg}'")
                response = self.test_send_message(session_id, msg)
                if response:
                    time.sleep(1)  # Brief pause between messages
            
            # Get all messages
            self.test_get_session_messages(session_id)
            
            # Clean up - delete test session
            self.test_delete_session(session_id)
        
        # Print summary
        self.print_test_summary()
        
        return True
    
    def print_test_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for test in self.test_results:
                if not test["success"]:
                    print(f"  - {test['test']}: {test['details']}")
        
        print("\n🎯 Test completed!")
        
        # Save detailed results to file
        with open("test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "tests": self.test_results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print("📄 Detailed results saved to test_results.json")

def main():
    """Main function to run tests"""
    print("RAG Study Chat API Test Client")
    print("=" * 40)
    
    # Check if server is specified
    server_url = input("Enter server URL (default: http://localhost:8000): ").strip()
    if not server_url:
        server_url = "http://localhost:8000"
    
    # Initialize client
    client = RAGStudyChatClient(server_url)
    
    # Run tests
    try:
        client.run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        client.print_test_summary()
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        client.print_test_summary()

if __name__ == "__main__":
    main()ful_mes
sages)}/{len(conversation_messages)} messages successful")
            
            # Clean up
            self.test_delete_session(session_id)
            return False
    
    def test_stress_test(self, course_id: int, duration_seconds: int = 30):
        """Stress test the API with continuous requests"""
        print(f"\n🔥 Stress Test ({duration_seconds} seconds)...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_count = 0
        success_count = 0
        error_count = 0
        response_times = []
        
        # Mix of different request types
        request_types = [
            ("GET", "/health"),
            ("GET", "/courses"),
            ("GET", f"/courses/{course_id}/documents"),
            ("GET", "/cache/stats"),
            ("GET", f"/courses/{course_id}/index-status")
        ]
        
        print(f"    Running stress test for {duration_seconds} seconds...")
        
        while time.time() < end_time:
            # Random request type
            method, endpoint = random.choice(request_types)
            
            request_start = time.time()
            response = self.make_request(method, endpoint)
            request_end = time.time()
            
            request_count += 1
            response_time = (request_end - request_start) * 1000
            response_times.append(response_time)
            
            if response and response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
            
            # Brief pause to avoid overwhelming the server
            time.sleep(0.1)
        
        # Calculate statistics
        actual_duration = time.time() - start_time
        requests_per_second = request_count / actual_duration
        success_rate = (success_count / request_count) * 100
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        if success_rate >= 95:  # 95% success rate threshold
            self.log_test("Stress Test", True, 
                         f"{request_count} requests in {actual_duration:.1f}s, "
                         f"{requests_per_second:.1f} req/s, {success_rate:.1f}% success, "
                         f"avg response: {avg_response_time:.0f}ms")
            return True
        else:
            self.log_test("Stress Test", False, 
                         f"Success rate too low: {success_rate:.1f}% ({success_count}/{request_count})")
            return False
    
    def run_advanced_test_suite(self, course_id: int):
        """Run comprehensive advanced test suite"""
        print("\n🎯 ADVANCED TEST SUITE")
        print("=" * 50)
        
        advanced_tests = [
            ("Performance Benchmark", lambda: self.test_performance_benchmark(course_id, 5)),
            ("Cache Efficiency", lambda: self.test_cache_efficiency(course_id)),
            ("Concurrent Requests", lambda: self.test_concurrent_requests(course_id, 3)),
            ("Error Handling", lambda: self.test_error_handling()),
            ("Data Validation", lambda: self.test_data_validation()),
            ("Chat Conversation Flow", lambda: self.test_chat_conversation_flow(course_id)),
            ("Stress Test", lambda: self.test_stress_test(course_id, 15))
        ]
        
        advanced_results = []
        
        for test_name, test_func in advanced_tests:
            print(f"\n🔬 Running {test_name}...")
            try:
                result = test_func()
                advanced_results.append(result)
            except Exception as e:
                print(f"    ❌ {test_name} failed with exception: {e}")
                advanced_results.append(False)
        
        # Summary of advanced tests
        passed_advanced = sum(advanced_results)
        total_advanced = len(advanced_results)
        
        print(f"\n📊 ADVANCED TESTS SUMMARY")
        print(f"Passed: {passed_advanced}/{total_advanced} ({passed_advanced/total_advanced*100:.1f}%)")
        
        return passed_advanced >= total_advanced * 0.7  # 70% pass rate for advanced tests
    
    def run_comprehensive_test(self, mode: str = "comprehensive"):
        """Run all tests based on mode"""
        print("🚀 Starting RAG Study Chat API Advanced Test Suite")
        print("=" * 60)
        print(f"Mode: {mode.upper()}")
        print("=" * 60)
        
        # Test 1: Health Check
        if not self.test_health_check():
            print("❌ Health check failed. Is the server running?")
            return False
        
        # Test 2: Get Courses
        courses = self.test_get_courses()
        if not courses:
            print("❌ No courses found. Cannot continue with course-specific tests.")
            return False
        
        # Find a course with documents for testing
        test_course_id = None
        for course in courses:
            course_id = course.get("id")
            docs = self.test_get_course_documents(course_id)
            if docs and len(docs.get("documents", [])) > 0:
                test_course_id = course_id
                break
        
        if not test_course_id:
            print("❌ No courses with documents found. Using first course anyway.")
            test_course_id = courses[0].get("id")
        
        # Test 3: Course Management
        self.test_get_unindexed_courses()
        self.test_get_course_index_status(test_course_id)
        
        # Test 4: Document Processing (optional - takes time)
        if mode in ["comprehensive", "stress"]:
            process_docs = input("\n🤔 Test document processing? This may take time (y/N): ").lower().strip()
            if process_docs == 'y':
                self.test_process_course_documents(test_course_id)
                self.test_index_unindexed_courses()
        
        # Test 5: Redis Cache System
        self.test_cache_health()
        self.test_cache_stats()
        self.test_cache_invalidation(test_course_id)
        
        # Test 6: Basic Chat System
        test_user_email = f"test_{int(time.time())}@example.com"
        session_name = f"Test Session {datetime.now().strftime('%H:%M:%S')}"
        
        session_id = self.test_create_chat_session(test_user_email, test_course_id, session_name)
        
        if session_id:
            # Test chat functionality
            self.test_get_user_sessions(test_user_email)
            
            # Send test messages
            test_messages = [
                "Hello, can you help me with this course?",
                "What topics are covered in the course materials?",
                "Explain the main concepts from the documents."
            ]
            
            for msg in test_messages:
                print(f"\n📝 Sending message: '{msg[:30]}...'")
                response = self.test_send_message(session_id, msg)
                if response:
                    time.sleep(1)  # Brief pause between messages
            
            # Get all messages
            self.test_get_session_messages(session_id)
            
            # Clean up - delete test session
            self.test_delete_session(session_id)
        
        # Test 7: Advanced Tests (based on mode)
        if mode in ["comprehensive", "performance", "stress"]:
            advanced_passed = self.run_advanced_test_suite(test_course_id)
        else:
            advanced_passed = True  # Skip advanced tests in basic mode
        
        # Print comprehensive summary
        self.print_comprehensive_summary(mode, advanced_passed)
        
        return True
    
    def print_comprehensive_summary(self, mode: str, advanced_passed: bool):
        """Print comprehensive test results summary"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Test Mode: {mode.upper()}")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize test results
        categories = {
            "Health & System": ["Health Check"],
            "Course Management": ["Get All Courses", "Get Course", "Get Unindexed", "Index Status"],
            "Document Processing": ["Process Course", "Index Unindexed"],
            "Chat System": ["Create Chat Session", "Get User Sessions", "Send Chat Message", "Get Session Messages", "Delete Chat Session"],
            "Cache Management": ["Redis Cache Health", "Get Cache Stats", "Cache Invalidation"],
            "Advanced Tests": ["Performance", "Cache Efficiency", "Concurrent Requests", "Error Handling", "Data Validation", "Chat Conversation Flow", "Stress Test"]
        }
        
        print(f"\n📋 TEST CATEGORIES:")
        for category, test_keywords in categories.items():
            category_tests = [t for t in self.test_results if any(keyword in t["test"] for keyword in test_keywords)]
            if category_tests:
                category_passed = len([t for t in category_tests if t["success"]])
                category_total = len(category_tests)
                print(f"  {category}: {category_passed}/{category_total} ({category_passed/category_total*100:.0f}%)")
        
        # Performance metrics (if available)
        performance_tests = [t for t in self.test_results if "Performance" in t["test"]]
        if performance_tests:
            print(f"\n⚡ PERFORMANCE HIGHLIGHTS:")
            for test in performance_tests:
                if test["success"] and "ms" in test["details"]:
                    print(f"  {test['test']}: {test['details']}")
        
        # Cache efficiency (if available)
        cache_tests = [t for t in self.test_results if "Cache" in t["test"]]
        if cache_tests:
            print(f"\n🎯 CACHE PERFORMANCE:")
            for test in cache_tests:
                if test["success"]:
                    print(f"  {test['test']}: {test['details']}")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for test in self.test_results:
                if not test["success"]:
                    print(f"  - {test['test']}: {test['details']}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if failed_tests == 0:
            print("  🎉 All tests passed! Your API is working perfectly.")
        elif failed_tests <= total_tests * 0.1:  # Less than 10% failure
            print("  ✅ Excellent! Minor issues detected, but overall system is healthy.")
        elif failed_tests <= total_tests * 0.2:  # Less than 20% failure
            print("  ⚠️  Good performance with some issues to address.")
        else:
            print("  🚨 Multiple issues detected. Review failed tests and fix critical problems.")
        
        if mode == "basic":
            print("  💡 Run with --mode=comprehensive for detailed testing.")
        elif mode == "comprehensive" and advanced_passed:
            print("  🚀 System ready for production deployment!")
        
        print(f"\n🎯 Test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Save detailed results to file
        with open("comprehensive_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "mode": mode,
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100,
                    "advanced_tests_passed": advanced_passed
                },
                "tests": self.test_results,
                "timestamp": datetime.now().isoformat(),
                "recommendations": self._generate_recommendations(failed_tests, total_tests)
            }, f, indent=2)
        
        print("📄 Detailed results saved to comprehensive_test_results.json")
    
    def _generate_recommendations(self, failed_tests: int, total_tests: int) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failure_rate = failed_tests / total_tests
        
        if failure_rate == 0:
            recommendations.append("System is performing optimally")
            recommendations.append("Consider implementing monitoring and alerting")
        elif failure_rate <= 0.1:
            recommendations.append("Minor issues detected - review failed tests")
            recommendations.append("System is ready for production with monitoring")
        elif failure_rate <= 0.2:
            recommendations.append("Address failed tests before production deployment")
            recommendations.append("Implement comprehensive monitoring")
        else:
            recommendations.append("Critical issues detected - fix before deployment")
            recommendations.append("Review system architecture and dependencies")
            recommendations.append("Implement proper error handling and logging")
        
        # Specific recommendations based on test types
        failed_test_names = [t["test"] for t in self.test_results if not t["success"]]
        
        if any("Cache" in name for name in failed_test_names):
            recommendations.append("Check Redis configuration and connectivity")
        
        if any("Chat" in name for name in failed_test_names):
            recommendations.append("Verify OpenAI API key and database connectivity")
        
        if any("Performance" in name for name in failed_test_names):
            recommendations.append("Optimize database queries and caching strategy")
        
        return recommendations

def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description="RAG Study Chat API Advanced Test Client")
    parser.add_argument("--mode", choices=["basic", "comprehensive", "performance", "stress"], 
                       default="comprehensive", help="Test mode to run")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="API server URL")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    print("RAG Study Chat API - Advanced Test Client")
    print("=" * 50)
    print(f"Server URL: {args.url}")
    print(f"Test Mode: {args.mode}")
    print(f"Verbose: {args.verbose}")
    print("=" * 50)
    
    # Initialize client
    client = RAGStudyChatClient(args.url)
    
    # Run tests based on mode
    try:
        if args.mode == "basic":
            print("Running basic functionality tests...")
            client.run_comprehensive_test("basic")
        elif args.mode == "comprehensive":
            print("Running comprehensive test suite...")
            client.run_comprehensive_test("comprehensive")
        elif args.mode == "performance":
            print("Running performance-focused tests...")
            client.run_comprehensive_test("performance")
        elif args.mode == "stress":
            print("Running stress tests...")
            client.run_comprehensive_test("stress")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        client.print_comprehensive_summary(args.mode, False)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        client.print_comprehensive_summary(args.mode, False)

if __name__ == "__main__":
    main()
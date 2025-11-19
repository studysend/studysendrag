#!/usr/bin/env python3
"""
View document summary test results in a readable format
"""

import json
import sys
from datetime import datetime

def load_results(filename=None):
    """Load the most recent results file"""
    if filename:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ File {filename} not found")
            return None
    
    # Find the most recent file
    import glob
    files = glob.glob('document_summaries_test_*.json')
    if not files:
        print("❌ No summary test files found")
        return None
    
    latest_file = max(files)
    print(f"📂 Loading: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def display_summary(results, show_full=False, filter_successful=None):
    """Display results in a formatted way"""
    if not results:
        return
    
    metadata = results['test_metadata']
    summaries = results['summary_results']
    
    print("🎯 DOCUMENT SUMMARY TEST RESULTS")
    print("=" * 50)
    print(f"📅 Test Period: {metadata['start_time']} to {metadata['end_time']}")
    print(f"📊 Success Rate: {metadata['success_rate']}")
    print(f"📈 Results: {metadata['successful_summaries']}/{metadata['total_documents']}")
    print()
    
    # Filter results if requested
    if filter_successful is not None:
        summaries = [s for s in summaries if s['summary_result']['success'] == filter_successful]
        status = "successful" if filter_successful else "failed"
        print(f"🔍 Showing {status} summaries only ({len(summaries)} results)")
        print()
    
    for i, result in enumerate(summaries, 1):
        success = result['summary_result']['success']
        status_icon = "✅" if success else "❌"
        
        print(f"{status_icon} {i}. Post ID {result['post_id']} - {result['doc_name']}")
        print(f"   📝 Post Name: {result['post_name']}")
        print(f"   🎓 Course ID: {result['course_id']}")
        print(f"   💬 Session: {result['session_id']}")
        
        if success:
            summary = result['summary_result']['summary_content']
            if show_full:
                print(f"   📄 Summary:\n{summary}")
            else:
                preview = summary[:200] + "..." if len(summary) > 200 else summary
                print(f"   📄 Summary: {preview}")
        else:
            error = result['summary_result'].get('error', 'Unknown error')
            print(f"   ❌ Error: {error}")
        
        print(f"   🕒 Time: {result['summary_result']['timestamp']}")
        print("-" * 50)

def show_statistics(results):
    """Show detailed statistics"""
    summaries = results['summary_results']
    
    print("📊 DETAILED STATISTICS")
    print("=" * 30)
    
    # Success/failure breakdown
    successful = [s for s in summaries if s['summary_result']['success']]
    failed = [s for s in summaries if not s['summary_result']['success']]
    
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    print()
    
    # Document type breakdown
    doc_types = {}
    for result in summaries:
        doc_name = result['doc_name']
        if doc_name:
            ext = doc_name.split('.')[-1].lower()
            if ext not in doc_types:
                doc_types[ext] = {'total': 0, 'successful': 0}
            doc_types[ext]['total'] += 1
            if result['summary_result']['success']:
                doc_types[ext]['successful'] += 1
    
    print("📄 By Document Type:")
    for ext, stats in doc_types.items():
        success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  .{ext}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
    print()
    
    # Course distribution
    courses = {}
    for result in summaries:
        course_id = result['course_id']
        if course_id not in courses:
            courses[course_id] = 0
        courses[course_id] += 1
    
    print("🎓 By Course ID:")
    for course_id, count in sorted(courses.items()):
        print(f"  Course {course_id}: {count} documents")
    print()
    
    # Summary length analysis
    lengths = [len(s['summary_result']['summary_content']) for s in successful]
    if lengths:
        print("📏 Summary Length Analysis:")
        print(f"  Average: {sum(lengths) / len(lengths):.0f} characters")
        print(f"  Min: {min(lengths)} characters")
        print(f"  Max: {max(lengths)} characters")

def main():
    """Main function with command line options"""
    filename = None
    show_full = False
    filter_successful = None
    show_stats = False
    
    # Simple command line parsing
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--file' and i + 1 < len(args):
            filename = args[i + 1]
            i += 2
        elif arg == '--full':
            show_full = True
            i += 1
        elif arg == '--successful':
            filter_successful = True
            i += 1
        elif arg == '--failed':
            filter_successful = False
            i += 1
        elif arg == '--stats':
            show_stats = True
            i += 1
        elif arg == '--help':
            print("Usage: python view_summary_results.py [options]")
            print("Options:")
            print("  --file FILENAME    Load specific JSON file")
            print("  --full            Show full summary content")
            print("  --successful      Show only successful summaries")
            print("  --failed          Show only failed summaries") 
            print("  --stats           Show detailed statistics")
            print("  --help            Show this help message")
            return
        else:
            print(f"Unknown option: {arg}")
            print("Use --help for usage information")
            return
    
    # Load and display results
    results = load_results(filename)
    if not results:
        return
    
    if show_stats:
        show_statistics(results)
    else:
        display_summary(results, show_full, filter_successful)

if __name__ == "__main__":
    main()

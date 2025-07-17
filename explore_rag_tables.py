import psycopg2
from psycopg2 import sql

def explore_rag_relevant_tables():
    connection_string = "postgresql://neondb_owner:vCFIsy2nER8c@ep-wandering-feather-a4mv42v8.us-east-1.aws.neon.tech/neondb?sslmode=require"
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        print("=== RAG APPLICATION - RELEVANT TABLES ANALYSIS ===\n")
        
        # 1. POST table - Contains course documents/PDFs
        print("1. POST TABLE (Primary source for PDFs):")
        print("-" * 50)
        cursor.execute("""
            SELECT id, post_name, doc_name, doc_url, course_id, crn, details, date
            FROM post 
            WHERE doc_url IS NOT NULL 
            ORDER BY date DESC 
            LIMIT 10;
        """)
        posts = cursor.fetchall()
        
        print(f"Total posts with documents: {len(posts)}")
        for post in posts:
            print(f"  ID: {post[0]} | Name: {post[1]} | Doc: {post[2]}")
            print(f"  URL: {post[3]} | Course: {post[4]} | CRN: {post[5]}")
            print(f"  Date: {post[7]}\n")
        
        # 2. COURSES table - Course categorization
        print("\n2. COURSES TABLE (Course categorization):")
        print("-" * 50)
        cursor.execute("SELECT * FROM courses ORDER BY id;")
        courses = cursor.fetchall()
        
        for course in courses:
            print(f"  ID: {course[0]} | Grade: {course[1]} | Category: {course[2]} | Subject: {course[3]}")
        
        # 3. SESSIONS table - Learning sessions with files
        print("\n3. SESSIONS TABLE (Sessions with files):")
        print("-" * 50)
        cursor.execute("""
            SELECT id, title, description, course_id, files, admin_email
            FROM sessions 
            WHERE files IS NOT NULL 
            ORDER BY event_date DESC 
            LIMIT 5;
        """)
        sessions = cursor.fetchall()
        
        for session in sessions:
            print(f"  ID: {session[0]} | Title: {session[1]}")
            print(f"  Course: {session[3]} | Files: {session[4]}")
            print(f"  Admin: {session[5]}\n")
        
        # 4. SESSION_FILES table - Additional files
        print("\n4. SESSION_FILES TABLE (Additional files):")
        print("-" * 50)
        cursor.execute("SELECT * FROM session_files ORDER BY changed_date DESC LIMIT 5;")
        session_files = cursor.fetchall()
        
        for file in session_files:
            print(f"  ID: {file[0]} | File: {file[1]} | User: {file[4]}")
        
        # 5. Profile table - User context for chat
        print("\n5. PROFILE TABLE (User context for personalized chat):")
        print("-" * 50)
        cursor.execute("SELECT email, name, college, department, major, description FROM profile LIMIT 3;")
        profiles = cursor.fetchall()
        
        for profile in profiles:
            print(f"  Email: {profile[0]} | Name: {profile[1]}")
            print(f"  College: {profile[2]} | Dept: {profile[3]} | Major: {profile[4]}\n")
        
        # Analysis and recommendations
        print("\n=== RAG APPLICATION RECOMMENDATIONS ===")
        print("-" * 50)
        print("📚 PRIMARY CONTENT SOURCE:")
        print("  • POST table: Contains doc_url (PDF links), doc_name, course_id")
        print("  • Filter by: doc_url IS NOT NULL for actual documents")
        
        print("\n🏷️  CONTENT CATEGORIZATION:")
        print("  • COURSES table: Grade, category, subject for content organization")
        print("  • CRN table: Course reference numbers for specific course sections")
        
        print("\n👥 USER PERSONALIZATION:")
        print("  • PROFILE table: User's college, department, major for personalized responses")
        print("  • SAVEDPOSTS table: User's saved content for preference learning")
        
        print("\n💬 CHAT CONTEXT:")
        print("  • SESSIONS table: Learning sessions and associated files")
        print("  • BOOKINGS table: User's scheduled learning sessions")
        
        print("\n🔧 RECOMMENDED RAG STRATEGY:")
        print("  1. Index documents from POST.doc_url where doc_url IS NOT NULL")
        print("  2. Use COURSES table for content categorization and filtering")
        print("  3. Leverage PROFILE data for personalized responses")
        print("  4. Use SAVEDPOSTS to understand user preferences")
        print("  5. Consider SESSIONS data for contextual learning paths")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    explore_rag_relevant_tables()
"""
Debug script to check what chunks are indexed for a specific post
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def check_post_chunks(post_id: int):
    """Check what chunks exist for a specific post"""
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check post info
        post_query = text("""
            SELECT p.id, p.post_name, p.doc_name, p.doc_url, c.id as course_id, c.subject
            FROM post p
            JOIN courses c ON p.course_id = c.id
            WHERE p.id = :post_id
        """)
        post_result = conn.execute(post_query, {"post_id": post_id})
        post_row = post_result.fetchone()

        if not post_row:
            print(f"Post {post_id} not found!")
            return

        print(f"\n{'='*60}")
        print(f"POST INFO:")
        print(f"{'='*60}")
        print(f"Post ID: {post_row[0]}")
        print(f"Post Name: {post_row[1]}")
        print(f"Doc Name: {post_row[2]}")
        print(f"Doc URL: {post_row[3]}")
        print(f"Course ID: {post_row[4]}")
        print(f"Subject: {post_row[5]}")

        # Check chunks for this post
        chunks_query = text("""
            SELECT id, post_id, course_id, doc_name, post_name, chunk_index, total_chunks,
                   LENGTH(chunk_text) as text_length
            FROM document_chunks
            WHERE post_id = :post_id
            ORDER BY chunk_index
        """)
        chunks_result = conn.execute(chunks_query, {"post_id": post_id})
        chunks = chunks_result.fetchall()

        print(f"\n{'='*60}")
        print(f"INDEXED CHUNKS FOR POST {post_id}:")
        print(f"{'='*60}")

        if not chunks:
            print(f"❌ NO CHUNKS FOUND! Post {post_id} has NOT been indexed.")
            print(f"\nTo index this post, use:")
            print(f"  curl -X POST http://localhost:8100/posts/{post_id}/process-background")
        else:
            print(f"✅ Found {len(chunks)} chunks")
            print(f"\nFirst 5 chunks:")
            for i, chunk in enumerate(chunks[:5]):
                print(f"\n  Chunk #{chunk[5] + 1}/{chunk[6]}:")
                print(f"    - Chunk ID: {chunk[0]}")
                print(f"    - Post ID: {chunk[1]}")
                print(f"    - Course ID: {chunk[2]}")
                print(f"    - Doc Name: {chunk[3]}")
                print(f"    - Post Name: {chunk[4]}")
                print(f"    - Text Length: {chunk[7]} chars")

        # Check for other posts with chunks
        other_posts_query = text("""
            SELECT DISTINCT post_id, doc_name, COUNT(*) as chunk_count
            FROM document_chunks
            GROUP BY post_id, doc_name
            ORDER BY post_id
        """)
        other_result = conn.execute(other_posts_query)
        other_posts = other_result.fetchall()

        print(f"\n{'='*60}")
        print(f"ALL INDEXED POSTS:")
        print(f"{'='*60}")

        if other_posts:
            for post in other_posts:
                marker = "👉" if post[0] == post_id else "  "
                print(f"{marker} Post ID {post[0]}: {post[1]} ({post[2]} chunks)")
        else:
            print("No posts have been indexed yet!")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python debug_post_chunks.py <post_id>")
        sys.exit(1)

    post_id = int(sys.argv[1])
    check_post_chunks(post_id)

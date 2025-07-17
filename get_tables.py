import psycopg2
from psycopg2 import sql

def get_database_tables():
    # Database connection string
    connection_string = "postgresql://neondb_owner:vCFIsy2nER8c@ep-wandering-feather-a4mv42v8.us-east-1.aws.neon.tech/neondb?sslmode=require"
    
    try:
        # Connect to the database
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Query to get all tables in the public schema
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        
        cursor.execute(query)
        tables = cursor.fetchall()
        
        print("Tables in the database:")
        print("-" * 30)
        
        if tables:
            for table in tables:
                print(f"• {table[0]}")
        else:
            print("No tables found in the public schema.")
        
        # Get table details (optional - shows column info)
        print("\nTable details:")
        print("-" * 50)
        
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # Get column information
            column_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s
            AND table_schema = 'public'
            ORDER BY ordinal_position;
            """
            
            cursor.execute(column_query, (table_name,))
            columns = cursor.fetchall()
            
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"  - {col[0]} ({col[1]}) {nullable}")
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    get_database_tables()
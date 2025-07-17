#!/usr/bin/env python3
"""
RAG Study Chat API Setup Script

This script helps set up the RAG Study Chat API system.
It checks dependencies, validates configuration, and provides setup guidance.

Usage:
    python setup.py
"""

import os
import sys
import subprocess
import importlib
from typing import List, Tuple

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies() -> List[str]:
    """Check if required packages are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'psycopg2',
        'boto3',
        'python-dotenv',
        'pydantic',
        'sqlalchemy',
        'pgvector',
        'openai',
        'llama-cloud',
        'llama-index',
        'apscheduler'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            # Handle special cases
            if package == 'psycopg2':
                importlib.import_module('psycopg2')
            elif package == 'python-dotenv':
                importlib.import_module('dotenv')
            elif package == 'llama-cloud':
                importlib.import_module('llama_cloud_services')
            elif package == 'llama-index':
                importlib.import_module('llama_index')
            else:
                importlib.import_module(package)
            
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    return missing_packages

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("   Copy .env.example to .env and configure your API keys")
        return False
    
    print("✅ .env file found")
    
    # Check required environment variables
    required_vars = [
        'DATABASE_URL',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_BUCKET_NAME',
        'LLAMA_CLOUD_API_KEY',
        'OPENAI_API_KEY'
    ]
    
    from dotenv import load_dotenv
    load_dotenv()
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_') or value == '':
            missing_vars.append(var)
            print(f"❌ {var} not configured")
        else:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var:
                masked_value = value[:8] + '...' if len(value) > 8 else '***'
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
    
    return len(missing_vars) == 0

def test_database_connection():
    """Test database connection"""
    try:
        from dotenv import load_dotenv
        import psycopg2
        
        load_dotenv()
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            print("❌ DATABASE_URL not configured")
            return False
        
        # Test connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check if pgvector extension is available
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        
        if result:
            print("✅ Database connection successful")
            print("✅ pgvector extension available")
        else:
            print("✅ Database connection successful")
            print("⚠️  pgvector extension not found - you may need to install it")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_openai_api():
    """Test OpenAI API connection"""
    try:
        from dotenv import load_dotenv
        from openai import OpenAI
        
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key or api_key.startswith('your_'):
            print("❌ OpenAI API key not configured")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Test with a simple embedding request
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=["test"],
            encoding_format="float"
        )
        
        if response.data:
            print("✅ OpenAI API connection successful")
            print(f"✅ text-embedding-3-small model accessible")
            return True
        else:
            print("❌ OpenAI API test failed")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False

def install_dependencies(packages: List[str]):
    """Install missing packages"""
    if not packages:
        return True
    
    print(f"\n📦 Installing {len(packages)} missing packages...")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install'
        ] + packages)
        
        print("✅ All packages installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False

def create_env_file():
    """Create .env file from template"""
    if os.path.exists('.env'):
        overwrite = input(".env file already exists. Overwrite? (y/N): ").lower().strip()
        if overwrite != 'y':
            return False
    
    if os.path.exists('.env.example'):
        import shutil
        shutil.copy('.env.example', '.env')
        print("✅ Created .env file from template")
        print("⚠️  Please edit .env file and add your API keys")
        return True
    else:
        print("❌ .env.example file not found")
        return False

def main():
    """Main setup function"""
    print("🚀 RAG Study Chat API Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    print("\n📦 Checking dependencies...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"\n⚠️  {len(missing_packages)} packages are missing")
        install = input("Install missing packages? (Y/n): ").lower().strip()
        
        if install != 'n':
            if not install_dependencies(missing_packages):
                return False
            
            # Re-check dependencies
            print("\n🔄 Re-checking dependencies...")
            missing_packages = check_dependencies()
            
            if missing_packages:
                print(f"❌ Still missing packages: {missing_packages}")
                return False
    
    print("\n🔧 Checking configuration...")
    
    # Check .env file
    if not check_env_file():
        create = input("Create .env file from template? (Y/n): ").lower().strip()
        if create != 'n':
            create_env_file()
            print("\n⚠️  Please configure your API keys in .env file and run setup again")
            return False
    
    print("\n🔌 Testing connections...")
    
    # Test database
    db_ok = test_database_connection()
    
    # Test OpenAI API
    openai_ok = test_openai_api()
    
    print("\n" + "=" * 40)
    print("📊 SETUP SUMMARY")
    print("=" * 40)
    
    if db_ok and openai_ok:
        print("✅ Setup completed successfully!")
        print("\n🚀 You can now start the server:")
        print("   python main.py")
        print("\n🧪 Or run tests:")
        print("   python test_client.py")
        return True
    else:
        print("❌ Setup incomplete")
        if not db_ok:
            print("   - Fix database connection issues")
        if not openai_ok:
            print("   - Configure OpenAI API key")
        return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()
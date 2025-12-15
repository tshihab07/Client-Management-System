# database.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import logging

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client & db
client = None
db = None

def get_mongo_uri() -> str:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise ValueError("❌ MONGODB_URI missing in .env")
    
    # ✅ Ensure database name is in URI — critical!
    if "/?" in uri and "/clientms_db?" not in uri:
        # Insert database name before query params
        base, query = uri.split("/?", 1)
        if not base.endswith("/"):
            base += "/"
        
        uri = f"{base}clientms_db?{query}"
    
    elif "/?" not in uri and not uri.endswith("/clientms_db"):
        # Append database name
        uri = uri.rstrip("/") + "/clientms_db"
    return uri


async def connect_to_mongo():
    global client, db
    try:
        uri = get_mongo_uri()
        logger.info(f"📡 Connecting to: {uri.split('@')[0]}@***.mongodb.net/...")
        
        # ✅ CORRECT CONFIG FOR WINDOWS + ATLAS + PYTHON 3.10+
        client = MongoClient(
                uri,
                serverSelectionTimeoutMS=20000,
                connectTimeoutMS=20000,
                socketTimeoutMS=20000,
                retryWrites=True,
                maxPoolSize=5,
                appname="ClientMS"
            )
        
        # Test with server info (more reliable than ping)
        server_info = client.admin.command('serverStatus', {'top': 1})
        db = client["clientms_db"]
        logger.info(f"✅ Connected to MongoDB Atlas! Version: {server_info.get('version', 'unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Fatal DB connection error: {type(e).__name__}: {e}")
        raise

async def close_mongo_connection():
    global client
    if client:
        client.close()
        logger.info("🔌 MongoDB connection closed.")

def get_db():
    if db is None:
        raise RuntimeError("❌ DB not initialized. Call connect_to_mongo() first.")
    return db

def get_collection(collection_name: str):
    return get_db()[collection_name]
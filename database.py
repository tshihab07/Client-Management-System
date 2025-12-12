# database.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client and db references
client = None
db = None

def get_mongo_uri() -> str:
    """Get MongoDB URI from environment, with validation."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise ValueError("MONGODB_URI not found in environment variables.")
    # Basic validation
    if "mongodb+srv://" not in uri:
        raise ValueError("Invalid MongoDB URI: must start with 'mongodb+srv://'.")
    return uri

async def connect_to_mongo():
    """Establish connection to MongoDB Atlas."""
    global client, db
    try:
        uri = get_mongo_uri()
        # Use connection pooling and retry settings
        client = MongoClient(
            uri,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            retryWrites=True,
            retryReads=True
        )
        # Test connection
        client.admin.command('ping')
        db = client["clientms_db"]  # Database name from your spec
        logger.info("✅ Successfully connected to MongoDB Atlas.")
    except (ConnectionFailure, ConfigurationError) as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during DB connection: {e}")
        raise

async def close_mongo_connection():
    """Gracefully close MongoDB connection."""
    global client
    if client:
        client.close()
        logger.info("🔌 MongoDB connection closed.")

def get_db():
    """Dependency to get DB instance."""
    if db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return db

def get_collection(collection_name: str):
    """Get a collection by name."""
    return get_db()[collection_name]
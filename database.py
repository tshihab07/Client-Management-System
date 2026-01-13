import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import logging

# load environment variables
load_dotenv()

# Configure the logging subsystem to capture informational and error messages.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# global references for the MongoDB client instance and the active database.
# these are initialized during connection setup and reused across the application.
client = None
db = None

def get_mongo_uri() -> str:
    """
    Retrieve and validate the MongoDB connection URI from environment variables.
    Ensures that the target database name ('clientms_db') is embedded in the URI,
    inserting or appending it as needed based on URI structure.
    """
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise ValueError("MONGODB_URI missing in .env")
    
    # ensure database name is in URI
    # if the URI contains query parameters but does not include, an explicit database name, insert the required database.
    if "/?" in uri and "/clientms_db?" not in uri:
        base, query = uri.split("/?", 1)            # insert database name before query params
        if not base.endswith("/"):
            base += "/"
        
        uri = f"{base}clientms_db?{query}"
    
    # if the URI has no query parameters and does not end with the database name, append it explicitly.
    elif "/?" not in uri and not uri.endswith("/clientms_db"):
        uri = uri.rstrip("/") + "/clientms_db"          # append database name
    
    return uri


async def connect_to_mongo():
    """
    establish an asynchronous connection to MongoDB using the processed URI.
    initializes the global `client` and `db` variables so they can be reused by other modules.
    connection settings are tuned for MongoDB Atlas and
    """
    global client, db
    try:
        uri = get_mongo_uri()
        logger.info(f"📡 Connecting to: {uri.split('@')[0]}@***.mongodb.net/...")
        
        # configure the MongoClient with recommended settings for stability and network resiliency when connecting to MongoDB Atlas clusters
        client = MongoClient(
                uri,
                serverSelectionTimeoutMS=20000,
                connectTimeoutMS=20000,
                socketTimeoutMS=20000,
                retryWrites=True,
                maxPoolSize=5,
                appname="ClientMS"
            )
         
        # test the server connection  info by issuing a serverStatus command (more reliable than ping)
        # this is a deeper health check compared to a simple ping.
        server_info = client.admin.command('serverStatus', {'top': 1})
        
        db = client["clientms_db"]          # Select the primary application database
        
        logger.info(f"Connected to MongoDB Atlas! Version: {server_info.get('version', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Fatal DB connection error: {type(e).__name__}: {e}")
        raise


async def close_mongo_connection():
    """
    Close the active MongoDB client connection if it has been initialized.
    Intended to be called during application shutdown for proper cleanup.
    """
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed.")


def get_db():
    """
    Return the active MongoDB database object. Ensures that the database
    connection has been initialized before allowing access.
    """
    if db is None:
        raise RuntimeError("DB not initialized. Call connect_to_mongo() first.")
    
    return db


def get_collection(collection_name: str):
    """
    Retrieve a MongoDB collection by name from the active database.
    This is a convenience wrapper to centralize collection access.
    """
    return get_db()[collection_name]
# test_mongo.py (Windows-Friendly)
import os
import ssl
from pymongo import MongoClient

# ✅ FORCE TLS 1.2 — critical for Windows
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

uri = "mongodb+srv://clientMS:du6YWwAE0IQZ3dJy@cluster07.emeitu4.mongodb.net/clientms_db?retryWrites=true&w=majority&appName=ClientMS"

print("📡 Connecting with TLS 1.2 + certifi...")

client = MongoClient(
                uri,
                serverSelectionTimeoutMS=20000,
                connectTimeoutMS=20000,
                socketTimeoutMS=20000,
                retryWrites=True,
                maxPoolSize=5,
                appname="ClientMS"
            )

try:
    # Use serverStatus (more reliable than ping)
    info = client.admin.command("serverStatus", {"top": 1})
    print(f"✅ SUCCESS! MongoDB Atlas Version: {info.get('version', 'unknown')}")
    print(f"   Host: {info.get('host', 'unknown')}")
    print(f"   Connections: {info.get('connections', {}).get('current', 'N/A')}")
    
    # Test DB access
    db = client["clientms_db"]
    count = db.list_collection_names()
    print(f"   Collections: {count if count else '[] (empty)'}")
    
except Exception as e:
    print(f"❌ FAILED: {type(e).__name__}: {e}")
    if "SSL" in str(e) or "TLS" in str(e):
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Run Windows Update → Install all certificate updates")
        print("2. Temporarily disable antivirus/firewall (test only)")
        print("3. Try from a different network (e.g., phone hotspot)")
    raise
finally:
    client.close()
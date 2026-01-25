import bcrypt

password = "admin123"
# Encode to bytes
pwd_bytes = password.encode('utf-8')
# Hash with 12 rounds (secure & fast)
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(pwd_bytes, salt)

print("bcrypt hash (copy this into security.py):")
print(hashed.decode('utf-8'))
print("\n Verification test:")
print("Valid?", bcrypt.checkpw(pwd_bytes, hashed))
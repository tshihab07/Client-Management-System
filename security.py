import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from models import UserInDB, Token

# Load environment
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))

if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in environment variables.")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme (for API auth — we'll use cookies for web)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

ADMIN_USER = UserInDB(
    username="tshihab07",
    hashed_password="$2b$12$0gUQeg7wcTSHad5HDDzBDebCyIROSomifSXml0PkWF3L6wNf6Uhgm"
)

ADMIN_USER = UserInDB(
    username="tshihab07",
    hashed_password="$2b$12$0gUQeg7wcTSHad5HDDzBDebCyIROSomifSXml0PkWF3L6wNf6Uhgm"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    if username == ADMIN_USER.username and verify_password(password, ADMIN_USER.hashed_password):
        return ADMIN_USER
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    
    except JWTError:
        raise credentials_exception
    
    if username != ADMIN_USER.username:
        raise credentials_exception
    
    return ADMIN_USER


async def get_current_user_from_cookie(request: Request) -> UserInDB:
    """Extract token from HTTP-only cookie — used for web UI."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    
    # Remove 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username != ADMIN_USER.username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
        return ADMIN_USER
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?error=session_expired"}
        )
import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from database import connect_to_mongo, close_mongo_connection, get_db
from security import get_current_user_from_cookie
from routers import auth, clients, transactions

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

# Initialize app
app = FastAPI(
    title="ClientMS Admin Panel",
    description="Secure client management dashboard for VendorVerse",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(clients.router, prefix="/api", tags=["clients"])
app.include_router(transactions.router, prefix="/api", tags=["transactions"])

# Root redirect
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Admin dashboard — protected route
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: dict = Depends(get_current_user_from_cookie)
):
    # Fetch summary stats from DB (to be implemented in clients router)
    # For now, mock data — will be replaced with real aggregation
    summary = {
        "total_clients": 42,
        "total_amount": 150000,
        "total_paid": 110000,
        "total_due": 40000
    }
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "summary": summary
        }
    )

# Logout — clears cookie and redirects
@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token", path="/", httponly=True, samesite="lax")
    return response
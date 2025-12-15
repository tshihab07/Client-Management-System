import os

from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from database import connect_to_mongo, close_mongo_connection, get_db, get_collection as get_client_collection
from security import get_current_user_from_cookie
from routers import auth, clients, transactions
from routers.clients import get_summary_stats
from models import ClientInDB

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
async def admin_dashboard( request: Request, user: dict = Depends(get_current_user_from_cookie), collection = Depends(get_client_collection)):
    # ✅ Fetch real summary stats from MongoDB
    summary = await get_summary_stats(collection=collection)
    
    # Optional: Fetch recent clients for table (e.g., top 10)
    cursor = collection.find().sort("created_at", -1).limit(10)
    recent_clients = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        recent_clients.append(ClientInDB(**doc))
    
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user,
            "summary": summary,
            "clients": recent_clients  # ← pass to template for table
        }
    )


# Logout — clears cookie and redirects
@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token", path="/", httponly=True, samesite="lax")
    return response


# === FRONTEND ROUTES (HTML PAGES) ===

@app.get("/add", response_class=HTMLResponse)
async def add_client_page(
    request: Request,
    user: dict = Depends(get_current_user_from_cookie)
):
    
    return templates.TemplateResponse("add_client.html", {"request": request, "user": user})


@app.get("/view", response_class=HTMLResponse)
async def view_clients_page(
    request: Request,
    search: str = Query(None),
    payment_status: str = Query(None),
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_client_collection)
):
    # Reuse the same logic as /api/clients
    query = {}
    if search:
        query["$or"] = [
            {"client_name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    if payment_status:
        query["payment_status"] = payment_status
    
    cursor = collection.find(query).sort("created_at", -1)
    clients = []
    
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        clients.append(ClientInDB(**doc))
    
    return templates.TemplateResponse(
        "view_clients.html",
        {
            "request": request,
            "user": user,
            "clients": clients
        }
    )


@app.get("/pending", response_class=HTMLResponse)
async def pending_clients_page(
    request: Request,
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_client_collection)
):
    cursor = collection.find({"payment_status": "Pending"}).sort("due", -1)
    clients = [ClientInDB(**{**doc, "_id": str(doc["_id"])}) for doc in cursor]
    
    return templates.TemplateResponse(
        "pending.html",
        {"request": request, "user": user, "clients": clients}
    )


@app.get("/completed", response_class=HTMLResponse)
async def completed_clients_page(
    request: Request,
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_client_collection)
):
    cursor = collection.find({"payment_status": "Completed"}).sort("updated_at", -1)
    clients = [ClientInDB(**{**doc, "_id": str(doc["_id"])}) for doc in cursor]
    
    return templates.TemplateResponse(
        "completed.html",
        {"request": request, "user": user, "clients": clients}
    )


@app.get("/transaction", response_class=HTMLResponse)
async def transaction_page(
    request: Request,
    client_id: str = Query(...),
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_client_collection)
):
    client = collection.find_one({"_id": client_id})
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Convert ObjectId and add ID
    client["_id"] = str(client["_id"])
    client_data = ClientInDB(**client)
    
    return templates.TemplateResponse(
        "transaction.html",
        {
            "request": request,
            "user": user,
            "client": client_data
        }
    )
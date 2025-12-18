import os
from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional
from bson import ObjectId

from database import connect_to_mongo, close_mongo_connection, get_collection
from models import ClientInDB
from security import get_current_user_from_cookie
from routers import auth, clients, transactions

# lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

# initialize app
app = FastAPI(
    title="ClientMS Admin Panel",
    description="Secure client management dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# include API routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(clients.router, prefix="/api", tags=["clients"])
app.include_router(transactions.router, prefix="/api", tags=["transactions"])


def get_clientms_collection():
    return get_collection("ClientMS")


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token", path="/", httponly=True, samesite="lax")
    return response


# admin Dashboard
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    summary = await clients.get_summary_stats(collection=collection)
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
            "clients": recent_clients
        }
    )


@app.get("/add", response_class=HTMLResponse)
async def add_client_page(
    request: Request,
    user: dict = Depends(get_current_user_from_cookie)
):
    return templates.TemplateResponse("add_client.html", {"request": request, "user": user})


@app.get("/view", response_class=HTMLResponse)
async def view_clients_page(
    request: Request,
    search: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    query = {}
    if search:
        query["$or"] = [
            {"client_name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    if payment_status:
        query["payment_status"] = payment_status
    
    cursor = collection.find(query).sort("created_at", -1)
    clients_list = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        clients_list.append(ClientInDB(**doc))
    
    return templates.TemplateResponse(
        "view_clients.html",
        {"request": request, "user": user, "clients": clients_list}
    )


@app.get("/pending", response_class=HTMLResponse)
async def pending_clients_page(
    request: Request,
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    cursor = collection.find({"payment_status": "Pending"}).sort("due", -1)
    clients_list = [ClientInDB(**{**doc, "_id": str(doc["_id"])}) for doc in cursor]
    return templates.TemplateResponse(
        "pending.html",
        {"request": request, "user": user, "clients": clients_list}
    )


@app.get("/completed", response_class=HTMLResponse)
async def completed_clients_page(
    request: Request,
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    cursor = collection.find({"payment_status": "Completed"}).sort("updated_at", -1)
    clients_list = [ClientInDB(**{**doc, "_id": str(doc["_id"])}) for doc in cursor]
    return templates.TemplateResponse(
        "completed.html",
        {"request": request, "user": user, "clients": clients_list}
    )


# safe handling and transaction history display
@app.get("/transaction", response_class=HTMLResponse)
async def transaction_page(
    request: Request,
    client_id: Optional[str] = Query(None),
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    client_data = None
    error = None

    if client_id:
        try:
            obj_id = ObjectId(client_id)
            client = collection.find_one({"_id": obj_id})
            if not client:
                error = "Client not found"
            else:
                client["_id"] = str(client["_id"])
                client_data = ClientInDB(**client)
        except Exception:
            error = "Invalid client ID"
    else:
        error = "No client selected. Please choose a client from Pending list."

    return templates.TemplateResponse(
        "transaction.html",
        {
            "request": request,
            "user": user,
            "client": client_data,
            "error": error
        }
    )


# read-only client detail page
@app.get("/client/{client_id}", response_class=HTMLResponse)
async def client_detail_page(
    request: Request,
    client_id: str,
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    try:
        obj_id = ObjectId(client_id)
        client = collection.find_one({"_id": obj_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client["_id"] = str(client["_id"])
        client_data = ClientInDB(**client)
        return templates.TemplateResponse(
            "client_detail.html",
            {"request": request, "user": user, "client": client_data}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID")
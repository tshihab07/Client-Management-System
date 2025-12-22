import os
from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId
from jose import jwt, JWTError
from math import ceil
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

from database import connect_to_mongo, close_mongo_connection, get_collection
from models import ClientInDB
from security import get_current_user_from_cookie, SECRET_KEY, ALGORITHM
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

# set number of items per page
PAGE_SIZE = 20

# Global Auth Middleware (CRITICAL)
PUBLIC_PATHS = (
    "/login",
    "/auth/login",
    "/auth/token",
    "/static",
    "/favicon.ico"
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # allow public paths
    if path.startswith(PUBLIC_PATHS):
        return await call_next(request)

    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    if token.startswith("Bearer "):
        token = token[7:]

    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

    return await call_next(request)

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
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/", httponly=True, samesite="lax")
    return response


# admin Dashboard
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    page: int = Query(1, ge=1),
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    
    summary = await clients.get_summary_stats(collection=collection)

    total_clients = collection.count_documents({})
    total_pages = ceil(total_clients / PAGE_SIZE)
    cursor = collection.find().sort("created_at", -1).skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    
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
            "clients": recent_clients,
            "page": page,
            "total_pages": total_pages,
            "total_clients": total_clients,
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
    page: int = Query(1, ge=1),
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
    
    total_clients = collection.count_documents(query)
    total_pages = ceil(total_clients / PAGE_SIZE)
    cursor = collection.find(query).sort("created_at", -1).skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    clients_list = []
    
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        clients_list.append(ClientInDB(**doc))
    
    return templates.TemplateResponse(
        "view_clients.html",
        {"request": request,
        "user": user,
        "clients": clients_list,
        "total_pages": total_pages,
        "total_clients": total_clients,
        "page": page
        }
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


# update payment route
@app.get("/payment", response_class=HTMLResponse)
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
        "update_payment.html",
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


@app.get("/transaction", response_class=HTMLResponse)
async def transaction_global_page(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),  # "Completed", "Pending", or None for All
    phone_search: Optional[str] = Query(None, alias="phone"),
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    # Build client query
    client_query = {}
    if status_filter in ["Completed", "Pending"]:
        client_query["payment_status"] = status_filter
    
    if phone_search:
        client_query["phone"] = {"$regex": phone_search.strip(), "$options": "i"}

    # Fetch all matching clients
    cursor = collection.find(client_query)
    clients = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        clients.append(ClientInDB(**doc))

    # In the global transaction route — replace the payment flattening loop with:
    all_payments = []
    for client in clients:
        history = client.payment_history or []
        history = sorted(history, key=lambda x: x.timestamp)
        
        if not isinstance(history, list):
            history = []
        
        # Enrich payments
        for i, tx in enumerate(history):
            paid_so_far = tx.amount
            remaining_after = max(0.0, round(client.amount - paid_so_far, 2))

            all_payments.append({
                "client_id": client.id,
                "client_name": client.client_name,
                "phone": client.phone or "—",
                "project": client.project,
                "category": client.category or "—",
                "amount_paid": tx.amount,
                "timestamp": tx.timestamp,
                "notes": tx.notes or "—",
                "remaining_after": remaining_after,
                "client_status": client.payment_status
        })

    # Sort by timestamp (most recent first)
    all_payments.sort(key=lambda x: x["timestamp"], reverse=True)

    return templates.TemplateResponse(
        "transaction_global.html",
        {
            "request": request,
            "user": user,
            "payments": all_payments,
            "status_filter": status_filter,
            "phone_search": phone_search or ""
        }
    )


@app.get("/transaction/client/{client_id}", response_class=HTMLResponse)
async def transaction_client_page(
    request: Request,
    client_id: str,
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection)
):
    # Try to fetch client by ObjectId first
    client = None
    try:
        obj_id = ObjectId(client_id)
        client = collection.find_one({"_id": obj_id})
    except InvalidId:
        # client_id is not a valid ObjectId → ignore
        pass

    # Fallback: try string-based _id (for legacy data)
    if not client:
        client = collection.find_one({"_id": client_id})

    # If still not found → real 404
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Normalize and load into Pydantic model
    client["_id"] = str(client["_id"])
    client_data = ClientInDB(**client)

    # Enrich payment history with cumulative remaining balance
    history_enriched = []
    paid_total = 0.0

    # Ensure chronological order
    payment_history = sorted(
        client_data.payment_history,
        key=lambda x: x.timestamp
    )

    for tx in payment_history:
        paid_total += tx.amount
        remaining = max(0.0, round(client_data.amount - paid_total, 2))

        history_enriched.append({
            "amount": tx.amount,
            "timestamp": tx.timestamp,
            "notes": tx.notes,
            "remaining_after": remaining
        })

    # Render template
    return templates.TemplateResponse(
        "transaction_client.html",
        {
            "request": request,
            "user": user,
            "client": client_data,
            "payment_history": history_enriched
        }
    )


# Invoice generation route
@app.get("/clients/{client_id}/invoice")
async def download_invoice(
    client_id: str,
    user: dict = Depends(get_current_user_from_cookie),
    collection = Depends(get_clientms_collection),
):
    try:
        obj_id = ObjectId(client_id)
        client = collection.find_one({"_id": obj_id})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid client ID")

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Normalize ID
    client["_id"] = str(client["_id"])

    # Use EXISTING fields only
    client_name = client.get("client_name", "Unknown Client")
    project = client.get("project", "—")
    phone = client.get("phone", "—")
    amount = client.get("amount", 0.0)
    paid = client.get("paid", 0.0)
    due = client.get("due", 0.0)

    # Generate filename
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"Invoice_{client_name.replace(' ', '_')}_{date_str}.pdf"

    # Create PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "INVOICE")
    y -= 40

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Client Name: {client_name}")
    y -= 20
    pdf.drawString(50, y, f"Phone: {phone}")
    y -= 20
    pdf.drawString(50, y, f"Project: {project}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Payment Summary")
    y -= 20

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Total Amount: ৳{amount:.2f}")
    y -= 18
    pdf.drawString(50, y, f"Paid Amount: ৳{paid:.2f}")
    y -= 18
    pdf.drawString(50, y, f"Due Amount: ৳{due:.2f}")
    y -= 40

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(50, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
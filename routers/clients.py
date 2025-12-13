from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
from database import get_collection
from models import ClientCreate, ClientInDB, ClientUpdate

router = APIRouter()

def get_client_collection():
    return get_collection("ClientMS")

@router.post("/clients", response_model=ClientInDB, status_code=status.HTTP_201_CREATED)
async def create_client(
    client: ClientCreate,
    collection = Depends(get_client_collection)
):
    # Compute derived fields
    due = client.amount - client.paid
    payment_status = "Completed" if due <= 0.01 else "Pending"
    
    # Prepare DB document
    client_dict = client.dict()
    client_dict.update({
        "due": due,
        "payment_status": payment_status,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    # Insert
    result = collection.insert_one(client_dict)
    client_dict["_id"] = str(result.inserted_id)
    
    return ClientInDB(**client_dict)


@router.get("/clients", response_model=List[ClientInDB])
async def get_clients(
    search: Optional[str] = Query(None, description="Search by name or phone"),
    payment_status: Optional[str] = Query(None, regex="^(Pending|Completed)$"),
    collection = Depends(get_client_collection)
):
    query = {}
    
    # Search: name or phone (assuming phone field exists — add if needed)
    if search:
        query["$or"] = [
            {"client_name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}  # ← will add phone to model later if missing
        ]
    
    # Filter by status
    if payment_status:
        query["payment_status"] = payment_status
    
    cursor = collection.find(query).sort("created_at", -1)
    clients = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        clients.append(ClientInDB(**doc))
    return clients


@router.get("/clients/pending", response_model=List[ClientInDB])
async def get_pending_clients(collection = Depends(get_client_collection)):
    cursor = collection.find({"payment_status": "Pending"}).sort("due", -1)
    return [ClientInDB(**{**doc, "_id": str(doc["_id"])}) for doc in cursor]


@router.get("/clients/completed", response_model=List[ClientInDB])
async def get_completed_clients(collection = Depends(get_client_collection)):
    cursor = collection.find({"payment_status": "Completed"}).sort("created_at", -1)
    return [ClientInDB(**{**doc, "_id": str(doc["_id"])}) for doc in cursor]


# Dashboard summary (used by /admin)
@router.get("/clients/summary")
async def get_summary_stats(collection = Depends(get_client_collection)):
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_clients": {"$sum": 1},
                "total_amount": {"$sum": "$amount"},
                "total_paid": {"$sum": "$paid"},
                "total_due": {"$sum": "$due"}
            }
        },
        {
            "$project": {
                "_id": 0,
                "total_clients": 1,
                "total_amount": {"$round": ["$total_amount", 2]},
                "total_paid": {"$round": ["$total_paid", 2]},
                "total_due": {"$round": ["$total_due", 2]}
            }
        }
    ]

    result = list(collection.aggregate(pipeline))
    
    return result[0] if result else {
        "total_clients": 0,
        "total_amount": 0.0,
        "total_paid": 0.0,
        "total_due": 0.0
    }
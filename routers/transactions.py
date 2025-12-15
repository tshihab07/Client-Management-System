from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from bson import ObjectId
from database import get_collection
from models import TransactionCreate

router = APIRouter()

def get_client_collection():
    return get_collection("ClientMS")

@router.post("/transactions", status_code=status.HTTP_200_OK)
async def record_transaction(transaction: TransactionCreate, collection = Depends(get_client_collection)):
    try:
        client_id = ObjectId(transaction.client_id)
    
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client ID format")
    
    # Find client
    client = collection.find_one({"_id": client_id})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    current_paid = float(client["paid"])
    current_amount = float(client["amount"])
    amount_to_add = float(transaction.amount_paid)
    
    # Prevent non-positive payments
    if amount_to_add <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than 0")
    
    # Compute new values (with rounding to 2 decimals)
    new_paid = round(current_paid + amount_to_add, 2)
    new_due = round(current_amount - new_paid, 2)
    
    # Allow minor floating-point tolerance (e.g., 0.001 → 0.00)
    if new_due < 0 and abs(new_due) < 0.01:
        new_due = 0.0
    
    # Enforce: due ≥ 0
    if new_due < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Overpayment: Total paid ({new_paid}) exceeds amount ({current_amount})")
    
    # Determine status
    new_status = "Completed" if new_due == 0.0 else "Pending"
    
    # Update DB
    result = collection.update_one(
        {"_id": client_id},
        {
            "$set": {
                "paid": new_paid,
                "due": new_due,
                "payment_status": new_status,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "payment_history": {
                    "amount": amount_to_add,
                    "timestamp": datetime.utcnow(),
                    "notes": transaction.notes or ""
                }
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update client")
    
    return {
        "message": "Payment updated successfully",
        "client_id": str(client_id),
        "new_paid": new_paid,
        "new_due": new_due,
        "status": new_status
    }
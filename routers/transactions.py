from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from database import get_collection
from models import TransactionCreate

router = APIRouter()

def get_client_collection():
    return get_collection("ClientMS")


@router.post("/transactions", status_code=status.HTTP_200_OK)
async def record_transaction(
    transaction: TransactionCreate,
    collection = Depends(get_client_collection)
):
    # Find client
    client = collection.find_one({"_id": transaction.client_id})
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    current_paid = client["paid"]
    current_amount = client["amount"]
    new_paid = current_paid + transaction.amount_paid
    
    # Prevent overpayment
    if new_paid > current_amount + 0.01:  # tolerance for float
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Overpayment: Total cannot exceed {current_amount}"
        )
    
    # Compute new due & status
    new_due = current_amount - new_paid
    new_status = "Completed" if new_due <= 0.01 else "Pending"
    
    # Update atomically
    result = collection.update_one(
        {"_id": transaction.client_id},
        {
            "$set": {
                "paid": round(new_paid, 2),
                "due": round(new_due, 2),
                "payment_status": new_status,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "payment_history": {
                    "amount": transaction.amount_paid,
                    "timestamp": datetime.utcnow(),
                    "notes": transaction.notes or ""
                }
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update client"
        )
    
    return {
        "message": "Payment updated successfully",
        "client_id": transaction.client_id,
        "new_paid": round(new_paid, 2),
        "new_due": round(new_due, 2),
        "status": new_status
    }
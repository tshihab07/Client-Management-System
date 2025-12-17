from fastapi import APIRouter, Depends, HTTPException, status, Form
from starlette.responses import RedirectResponse
from datetime import datetime
from bson import ObjectId
from database import get_collection

router = APIRouter()

def get_client_collection():
    return get_collection("ClientMS")

@router.post("/transactions", status_code=status.HTTP_303_SEE_OTHER)
async def record_transaction(
    client_id: str = Form(...),
    amount_paid: float = Form(...),
    notes: str = Form(""),
    collection = Depends(get_client_collection)
):
    # Validate client_id
    try:
        obj_id = ObjectId(client_id)
    except Exception:
        return RedirectResponse(
            url="/view?error=Invalid client ID format",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Fetch client
    client = collection.find_one({"_id": obj_id})
    if not client:
        return RedirectResponse(
            url="/view?error=Client not found",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Parse numbers
    try:
        current_paid = float(client.get("paid", 0))
        current_amount = float(client.get("amount", 0))
        amount_to_add = float(amount_paid)
    except (ValueError, TypeError):
        return RedirectResponse(
            url=f"/transaction?client_id={client_id}&error=Invalid numeric values",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Validate amount
    if amount_to_add <= 0:
        return RedirectResponse(
            url=f"/transaction?client_id={client_id}&error=Payment amount must be greater than 0",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Compute new values
    new_paid = round(current_paid + amount_to_add, 2)
    new_due = round(current_amount - new_paid, 2)

    # Tolerance for floating point errors
    if new_due < 0 and abs(new_due) < 0.01:
        new_due = 0.0

    if new_due < 0:
        return RedirectResponse(
            url=f"/transaction?client_id={client_id}&error=Overpayment: total paid ({new_paid}) exceeds amount ({current_amount})",
            status_code=status.HTTP_303_SEE_OTHER
        )

    new_status = "Completed" if new_due == 0.0 else "Pending"

    # Update DB
    result = collection.update_one(
        {"_id": obj_id},
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
                    "notes": notes or ""
                }
            }
        }
    )

    if result.modified_count == 0:
        return RedirectResponse(
            url=f"/transaction?client_id={client_id}&error=Failed to update database",
            status_code=status.HTTP_303_SEE_OTHER
        )

    return RedirectResponse(
        url="/view?message=Payment recorded successfully",
        status_code=status.HTTP_303_SEE_OTHER
    )
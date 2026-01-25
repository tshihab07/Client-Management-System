from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import datetime

# Core data models
class ClientBase(BaseModel):
    """
    Shared base model for client data.
    Used as the foundation for create, update, and database models.
    """
    
    # Basic client identity and contact information
    client_name: str = Field(..., min_length=1, example="John Doe")
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    
    # Project-related information
    project: str = Field(..., min_length=1, example="Website Redesign")
    category: Optional[str] = None
    
    # Financial fields
    amount: float = Field(..., gt=0, example=15000.0)
    paid: float = Field(ge=0, example=5000.0)

    @validator('paid')
    def validate_paid(cls, v, values):
        """
        Ensure that the amount paid does not exceed
        the total project amount.
        """

        amount = values.get('amount', 0)
        if v > amount:
            raise ValueError('Paid cannot exceed total amount')
        return v

# record client payment history
class PaymentRecord(BaseModel):
    """
    Represents a single payment entry made by a client.
    Stored as part of a client's payment history.
    """

    amount: float
    timestamp: datetime
    notes: Optional[str] = None


# Client Creation Model
class ClientCreate(ClientBase):
    """
    Model used when creating a new client.
    Inherits all required fields from ClientBase.
    """

    pass


# Client Database Model
class ClientInDB(ClientBase):
    """
    Model representing a client as stored in the database.
    Includes database-specific fields and computed values.
    """

    # Database identifier (MongoDB ObjectId)
    id: str = Field(..., alias="_id")

    # Computed financial fields
    due: float = Field(..., ge=0)
    payment_status: str

    # Audit timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Historical record of all payments
    payment_history: List[PaymentRecord] = Field(default_factory=list)

    class Config:
        """
        Allow population using field aliases
        (mapping MongoDB `_id` to `id`).
        """
         
        populate_by_name = True


# Client Update Model
class ClientUpdate(BaseModel):
    """
    Model used for partial client updates.
    Currently supports updating payment information only.
    """

    paid: Optional[float] = None


# Transaction Model
class TransactionCreate(BaseModel):
    """
    Represents a payment transaction request
    applied to a specific client.
    """

    client_id: str
    amount_paid: float = Field(..., gt=0)
    notes: Optional[str] = None


# Auth Models
class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    """
    Authentication token returned after successful login.
    """

    access_token: str
    token_type: str = "bearer"


class UserInDB(BaseModel):
    """
    Persisted user model storing credentials securely.
    """
    username: str
    hashed_password: str
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from datetime import datetime

# Core data models
class ClientBase(BaseModel):
    client_name: str = Field(..., min_length=1, example="John Doe")
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    project: str = Field(..., min_length=1, example="Website Redesign")
    category: Optional[str] = None
    amount: float = Field(..., gt=0, example=15000.0)
    paid: float = Field(ge=0, example=5000.0)

    @validator('paid')
    def validate_paid(cls, v, values):
        amount = values.get('amount', 0)
        if v > amount:
            raise ValueError('Paid cannot exceed total amount')
        return v

# record client payment history
class PaymentRecord(BaseModel):
    amount: float
    timestamp: datetime
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientInDB(ClientBase):
    id: str = Field(..., alias="_id")
    due: float = Field(..., ge=0)
    payment_status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    payment_history: List[PaymentRecord] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class ClientUpdate(BaseModel):
    paid: Optional[float] = None
    # `due` and `payment_status` are auto-calculated


# Transaction Model
class TransactionCreate(BaseModel):
    client_id: str
    amount_paid: float = Field(..., gt=0)
    notes: Optional[str] = None


# Auth Models
class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInDB(BaseModel):
    username: str
    hashed_password: str
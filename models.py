from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

# core data models
class ClientBase(BaseModel):
    client_name: str = Field(..., min_length=1, example="John Doe")
    project: str = Field(..., min_length=1, example="Website Redesign")
    category: Optional[str] = None
    phone: Optional[str] = None
    amount: float = Field(..., gt=0, example=15000.0)
    paid: float = Field(ge=0, example=5000.0)


    @validator('paid')
    def validate_paid(cls, v, values):
        amount = values.get('amount', 0)
        if v > amount:
            raise ValueError('Paid cannot exceed total amount')
       
        return v


class ClientCreate(ClientBase):
    pass


class ClientInDB(ClientBase):
    id: str = Field(..., alias="_id")
    payment_status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ClientUpdate(BaseModel):
    paid: Optional[float] = None
    # due will be auto-calculated


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
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

# core data models
class ClientBase(BaseModel):
    client_name: str = Field(..., min_length=1, example="John Doe")
    project: str = Field(..., min_length=1, example="Website Redesign")
    category: str = Field(..., min_length=1, example="Web Development")
    amount: float = Field(..., gt=0, example=15000.0)
    paid: float = Field(ge=0, example=5000.0)
    due: float = Field(ge=0, example=10000.0)

    @validator('due', always=True)
    def validate_due(cls, v, values):
        amount = values.get('amount', 0)
        paid = values.get('paid', 0)
        expected_due = amount - paid
        if abs(v - expected_due) > 0.01:
            raise ValueError(f'Due must be amount - paid ({expected_due})')
        return expected_due

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
    payment_status: str = Field(..., pattern=r"^(Pending|Completed)$")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True  # Allows using 'id' instead of '_id' in code


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
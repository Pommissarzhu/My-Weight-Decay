from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class FoodItem(BaseModel):
    name: str
    estimated_calories: int
    amount: str

class MacroNutrients(BaseModel):
    protein: str
    carbs: str
    fat: str

class AIAnalysisResult(BaseModel):
    food_items: List[FoodItem]
    total_calories: int
    macro_nutrients: MacroNutrients
    health_score: int
    suggestion: str

class FoodLogBase(BaseModel):
    food_name: str
    calories: int
    nutrients: Dict[str, str]
    advice: str

class FoodLogCreate(FoodLogBase):
    image_path: str

class FoodLog(FoodLogBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    email: str
    height: float
    weight: float
    age: int
    gender: str
    target_weight: float

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    
    class Config:
        orm_mode = True

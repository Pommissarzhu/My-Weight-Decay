from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import json

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)  # 简单示例，实际应用应加密
    height = Column(Float)
    weight = Column(Float)
    age = Column(Integer)
    gender = Column(String)
    target_weight = Column(Float)
    preferences = Column(Text)  # 存储 JSON 字符串

    food_logs = relationship("FoodLog", back_populates="user")

class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_path = Column(String)
    food_name = Column(String)
    calories = Column(Integer)
    nutrients = Column(Text)  # 存储 JSON 字符串: {"protein": "g", "carbs": "g", "fat": "g"}
    advice = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="food_logs")

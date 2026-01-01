from fastapi import FastAPI, UploadFile, File, Depends, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import shutil
import os
import uuid
import json
import logging

from . import models, database, schemas
from .services import ai_service, scheduler_service

# 初始化应用
app = FastAPI(title="My Weight Decay")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 模板配置
templates = Jinja2Templates(directory="app/templates")

# 确保上传目录存在
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 启动事件
@app.on_event("startup")
def startup_event():
    # 创建数据库表
    models.Base.metadata.create_all(bind=database.engine)
    # 启动定时任务
    scheduler_service.start_scheduler()
    
    # 初始化示例用户 (如果不存在)
    db = next(database.get_db())
    if not db.query(models.User).filter(models.User.email == "demo@example.com").first():
        demo_user = models.User(
            email="demo@example.com",
            height=174,
            weight=87,
            age=23,
            gender="Male",
            target_weight=75,
            preferences='{"daily_email": true}'
        )
        db.add(demo_user)
        db.commit()


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    首页路由
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload_food")
async def upload_food(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    """
    处理图片上传并调用 AI 分析
    """
    try:
        # 1. 保存文件
        file_extension = file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 相对路径用于前端访问
        relative_path = f"uploads/{file_name}"
        
        # 2. 调用 AI 分析 (这里需要真实的用户信息，暂时用 hardcode)
        # 实际项目中应该从 Session 或 Token 获取当前用户
        user = db.query(models.User).first()
        user_info = f"{user.gender}, {user.age}岁, {user.height}cm, {user.weight}kg, 正在减重"
        
        # 为了演示，如果没配置 API Key，返回 Mock 数据
        if not os.getenv("DASHSCOPE_API_KEY"):
            print("Warning: No API Key found, using mock data")
            import time
            time.sleep(1) # 模拟延迟
            return {
                "food_items": [{"name": "模拟红烧肉", "estimated_calories": 450, "amount": "150g"}],
                "total_calories": 450,
                "macro_nutrients": {"protein": "20g", "carbs": "10g", "fat": "35g"},
                "health_score": 6,
                "suggestion": "红烧肉脂肪含量较高，建议搭配绿色蔬菜食用。",
                "image_path": relative_path # 把图片路径带回给前端暂存
            }

        result = ai_service.analyze_food_image(file_path, user_info)
        
        if result:
            result['image_path'] = relative_path
            return result
        else:
            return JSONResponse(status_code=500, content={"error": "AI 分析失败，请重试"})
            
    except Exception as e:
        logging.error(f"Upload error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/confirm_food")
async def confirm_food(data: dict, db: Session = Depends(database.get_db)):
    """
    用户确认后将记录写入数据库
    """
    try:
        # 实际项目中这里需要校验用户身份
        user = db.query(models.User).first()
        
        # 将前端传回的 JSON 数据转换为数据库模型
        # 注意：这里需要根据 ai_service 返回的结构和 models.py 对应
        # 前端传回的 data 应该是包含 image_path 和 AI 分析结果的大 JSON
        
        food_names = [item['name'] for item in data.get('food_items', [])]
        food_name_str = ", ".join(food_names)
        
        new_log = models.FoodLog(
            user_id=user.id,
            image_path=data.get('image_path'), # 需要确保 upload 接口返回了这个
            food_name=food_name_str,
            calories=data.get('total_calories'),
            nutrients=json.dumps(data.get('macro_nutrients')),
            advice=data.get('suggestion'),
            created_at=datetime.now()
        )
        
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        
        return {"status": "success", "id": new_log.id}
    except Exception as e:
        logging.error(f"Save error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/stats")
async def get_stats(db: Session = Depends(database.get_db)):
    """
    获取今日统计数据
    """
    user = db.query(models.User).first()
    if not user:
        return {"today_calories": 0, "recent_logs": []}
    
    # 今日 0点
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    # 查询今日记录
    today_logs = db.query(models.FoodLog).filter(
        models.FoodLog.user_id == user.id,
        models.FoodLog.created_at >= today_start
    ).all()
    
    today_calories = sum(log.calories for log in today_logs)
    
    # 获取最近 5 条记录用于展示
    recent_logs = db.query(models.FoodLog).filter(
        models.FoodLog.user_id == user.id
    ).order_by(models.FoodLog.created_at.desc()).limit(5).all()
    
    return {
        "today_calories": today_calories,
        "recent_logs": recent_logs
    }

if __name__ == "__main__":
    import uvicorn
    # allow remote access
    uvicorn.run(app, host="0.0.0.0", port=8000)

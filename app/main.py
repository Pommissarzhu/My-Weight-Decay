from fastapi import FastAPI, UploadFile, File, Depends, Request, HTTPException, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import shutil
import os
import uuid
import json
import logging
from dotenv import load_dotenv

load_dotenv()

import models, database, schemas
from services import ai_service, scheduler_service, auth_service

# 初始化应用
app = FastAPI(title="My Weight Decay")

# 添加 Session 中间件
# 注意：在生产环境中 secret_key 应该从环境变量获取
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-super-secret-key"))

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板配置
templates = Jinja2Templates(directory="templates")

# 确保上传目录存在
UPLOAD_DIR = "static/uploads"
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
            password_hash=auth_service.get_password_hash("demo123"),
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
async def read_root(request: Request, db: Session = Depends(database.get_db)):
    """
    首页路由 - 需要登录
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login")
        
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not auth_service.verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "邮箱或密码错误"})
    
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, 
                   email: str = Form(...), 
                   password: str = Form(...),
                   height: float = Form(...), 
                   weight: float = Form(...), 
                   age: int = Form(...),
                   gender: str = Form(...), 
                   target_weight: float = Form(...),
                   db: Session = Depends(database.get_db)):
    try:
        if len(password) > 14 or not password.isascii():
             return templates.TemplateResponse("register.html", {"request": request, "error": "密码必须是ASCII字符且不超过14位"})

        if db.query(models.User).filter(models.User.email == email).first():
            return templates.TemplateResponse("register.html", {"request": request, "error": "邮箱已被注册"})
        
        hashed_pw = auth_service.get_password_hash(password)
        # JSON string for preferences
        default_preferences = json.dumps({"daily_email": True})
        
        new_user = models.User(
            email=email, 
            password_hash=hashed_pw, 
            height=height, 
            weight=weight,
            age=age, 
            gender=gender, 
            target_weight=target_weight,
            preferences=default_preferences
        )
        db.add(new_user)
        db.commit()
        request.session["user_id"] = new_user.id
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(e)})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@app.post("/forgot-password")
async def forgot_password(request: Request, email: str = Form(...), new_password: str = Form(...), db: Session = Depends(database.get_db)):
     user = db.query(models.User).filter(models.User.email == email).first()
     if user:
         if len(new_password) > 14 or not new_password.isascii():
              return templates.TemplateResponse("forgot_password.html", {"request": request, "error": "新密码格式错误"})
         user.password_hash = auth_service.get_password_hash(new_password)
         db.commit()
         return templates.TemplateResponse("login.html", {"request": request, "message": "密码重置成功，请登录"})
     
     return templates.TemplateResponse("forgot_password.html", {"request": request, "error": "邮箱未找到"})



@app.post("/upload_food")
async def upload_food(request: Request, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
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
        
        # 2. 调用 AI 分析 
        user_id = request.session.get("user_id")
        if not user_id:
             return JSONResponse(status_code=401, content={"error": "请先登录"})
        
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
             return JSONResponse(status_code=401, content={"error": "用户不存在"})

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
async def confirm_food(request: Request, data: dict, db: Session = Depends(database.get_db)):
    """
    用户确认后将记录写入数据库
    """
    try:
        user_id = request.session.get("user_id")
        if not user_id:
             return JSONResponse(status_code=401, content={"error": "请先登录"})

        user = db.query(models.User).filter(models.User.id == user_id).first()
        
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
async def get_stats(request: Request, db: Session = Depends(database.get_db)):
    """
    获取今日统计数据
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return {"today_calories": 0, "recent_logs": []}
    user = db.query(models.User).filter(models.User.id == user_id).first()
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

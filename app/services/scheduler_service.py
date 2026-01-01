from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models, database

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def send_daily_report():
    """
    发送每日饮食报告
    """
    logger.info("开始生成每日报告...")
    
    # 这里的逻辑需要根据实际情况完善，比如遍历所有用户发送
    # 这里为了演示，假设只给 ID 为 1 的用户发送
    
    db = database.SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == 1).first()
        if not user or not user.email:
            logger.warning("未找到该用户或邮箱为空")
            return

        # 查询过去24小时的记录
        yesterday = datetime.now() - timedelta(days=1)
        logs = db.query(models.FoodLog).filter(
            models.FoodLog.user_id == user.id,
            models.FoodLog.created_at >= yesterday
        ).all()
        
        total_calories = sum(log.calories for log in logs) if logs else 0
        
        # 简单的邮件内容构建
        subject = f"每日饮食日报 - {datetime.now().strftime('%Y-%m-%d')}"
        body = f"""
        <h1>你好, {user.email}</h1>
        <p>你昨天总共摄入了 <strong>{total_calories}</strong> 千卡。</p>
        <p>继续加油！</p>
        """
        
        # 发送邮件逻辑 (需要配置 SMTP)
        # send_email(user.email, subject, body)
        logger.info(f"报告生成完毕，准备发送给: {user.email} (模拟发送)")

    except Exception as e:
        logger.error(f"发送报告失败: {e}")
    finally:
        db.close()

def start_scheduler():
    # 每天凌晨 00:30 执行
    trigger = CronTrigger(hour=0, minute=30)
    scheduler.add_job(send_daily_report, trigger)
    scheduler.start()
    logger.info("定时任务调度器已启动")

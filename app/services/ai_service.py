from http import HTTPStatus
import dashscope
import os
import json
import logging
from typing import Optional
from ..schemas import AIAnalysisResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 请确保环境变量 DASHSCOPE_API_KEY 已设置
# dashscope.api_key = os.getenv("DASHSCOPE_API_KEY") 

def analyze_food_image(image_path: str, user_info: str) -> Optional[dict]:
    """
    调用通义千问-VL 分析食物图片
    """
    prompt = f"""
    我上传了一张食物照片。请作为专业的营养师进行分析。
    用户信息：{user_info}
    请分析图片中的食物，并以纯 JSON 格式返回，不要包含Markdown标记(`json ... `)。
    JSON 格式必须严格遵守以下结构：
    {{
    "food_items": [{{"name": "菜名", "estimated_calories": 整数(千卡), "amount": "估计分量"}}],
    "total_calories": 整数,
    "macro_nutrients": {{"protein": "g", "carbs": "g", "fat": "g"}},
    "health_score": 1-10,
    "suggestion": "针对该用户的简短建议(50字以内)"
    }}
    """
    
    messages = [
        {
            "role": "user",
            "content": [
                {"image": image_path},
                {"text": prompt}
            ]
        }
    ]

    try:
        # 使用 qwen-vl-max 或者 qwen-vl-plus
        response = dashscope.MultiModalConversation.call(
            model='qwen-vl-max',
            messages=messages
        )

        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0].message.content
            # 清理可能的 markdown 标记
            content = content.replace("```json", "").replace("```", "").strip()
            try:
                result_json = json.loads(content)
                return result_json
            except json.JSONDecodeError:
                logger.error(f"JSON 解析失败: {content}")
                return None
        else:
            logger.error(f"API 调用失败: {response.code} - {response.message}")
            return None

    except Exception as e:
        logger.error(f"发生异常: {e}")
        return None

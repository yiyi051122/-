# -*- coding: utf-8 -*-
"""
工具模块
"""

import re
from datetime import datetime


def clean_text(text):
    """清理文本"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_disease_name(text):
    """从文本中提取病害名称"""
    disease_keywords = [
        "条锈病", "白粉病", "赤霉病", "纹枯病", "叶锈病"
    ]
    for keyword in disease_keywords:
        if keyword in text:
            return f"小麦{keyword}"
    return None


def format_timestamp():
    """格式化时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_input(user_input):
    """验证用户输入"""
    if not user_input or len(user_input.strip()) < 5:
        return False, "请输入更详细的症状描述（至少5个字符）"
    return True, "输入有效"


def calculate_confidence(symptom_text, disease_symptom):
    """计算症状匹配置信度"""
    if not symptom_text or not disease_symptom:
        return 0.0
    
    symptom_keywords = set(symptom_text)
    disease_keywords = set(disease_symptom)
    
    if not disease_keywords:
        return 0.0
    
    intersection = symptom_keywords & disease_keywords
    confidence = len(intersection) / len(disease_keywords)
    
    return round(confidence * 100, 2)


def get_severity_level(confidence):
    """根据置信度判断严重程度"""
    if confidence >= 80:
        return "高", "症状匹配度高，建议立即采取防治措施"
    elif confidence >= 50:
        return "中", "症状部分匹配，建议进一步观察确认"
    else:
        return "低", "症状匹配度较低，建议提供更详细的症状描述"


class DiagnosisLogger:
    """诊断日志记录器"""
    
    def __init__(self, log_file="diagnosis_log.txt"):
        self.log_file = log_file
    
    def log(self, user_input, diagnosis_result):
        """记录诊断日志"""
        timestamp = format_timestamp()
        log_entry = f"""
{'='*50}
时间: {timestamp}
用户输入: {user_input}
诊断结果: {diagnosis_result[:200]}...
{'='*50}
"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass

# -*- coding: utf-8 -*-
"""
文本预处理模块
去除参考文献、目录、页眉页脚、期刊元数据等无效内容
"""

import re
import os


def preprocess_text(text: str) -> str:
    """
    预处理文本，去除无效内容
    
    Args:
        text: 原始文本
        
    Returns:
        处理后的文本
    """
    if not text:
        return text
    
    if '## 原始文本' in text:
        match = re.search(r'## 原始文本\s*\n(.*?)(?=\n## 抽取的实体|\n## 抽取的关系|\n## 抽取时间|$)', text, re.DOTALL)
        if match:
            text = match.group(1)
    
    text = re.sub(r'^#\s*[^\n]+\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s*[^\n]+\n', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'^\s*-\s*[^\n]+--\[[^\]]+\]-->[^\n]+\n', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'^\s*-\s*\[[^\]]+\]\s*[^\n]+\n', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*$', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'第\s*\d+\s*卷.*?Vol\.\s*\d+.*?\n', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\d{4}年\d{1,2}月.*?Journal.*?\n', '', text, flags=re.IGNORECASE)
    text = re.sub(r'第\s*\d+\s*卷\s*第\s*\d+\s*期.*?\n', '', text)
    
    text = re.sub(r'^[A-Za-z\s&]+Science[^,\n]*,\s*\d+.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[A-Za-z\s&]+Administration[^,\n]*,\s*\d+.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[A-Za-z\s&]+Research[^,\n]*,\s*\d+.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[A-Za-z\s&]+Journal[^,\n]*,\s*\d+.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[A-Z][A-Z\s&]+[A-Z]\s*\d{4}\s*,\s*\d+.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^SPECIAL\s+ECONOMIC\s+ANIMALS\s+AND\s+PLANTS.*?\n', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^特种经济动植物\s*$', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'\n特种经济动植物\n', '\n', text)
    text = re.sub(r'\nSPECIAL\s+ECONOMIC\s+ANIMALS\s+AND\s+PLANTS\n', '\n', text, flags=re.IGNORECASE)
    
    text = re.sub(r'^\s*-\s*\d+\s*-\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*-\s*\d+\s*-', ' ', text)
    
    text = re.sub(r'Abstract[:：].*?(?=Key\s*words|关键词|1\s+[^\s]|$)', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'Key\s*words[:：][^\n]+', '', text, flags=re.IGNORECASE)
    
    text = re.sub(r'^[A-Z][a-z]+\s+[A-Z][a-z]+.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\([A-Za-z,\s]+\d+\s*,\s*[A-Za-z]+\s*\)\s*$', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'中图分类号[:：]\s*\S+.*?\n', '', text)
    text = re.sub(r'文献标志码[:：]\s*\S+.*?\n', '', text)
    text = re.sub(r'文章编号[:：]\s*[\d\-]+.*?\n', '', text)
    
    text = re.sub(r'[\u4e00-\u9fa5]+\s*[\d#，,\s]*\n.*?(?:大学|学院|中心|站|局|所).*?\n', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'^\s*[\d\.]*\s*[\u4e00-\u9fa5]+(?:大学|学院|中心|站|局|所|公司).*?[，,].*?[省市县].*?\d{5,}.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[\u4e00-\u9fa5]+(?:省|市|县|区).*?[，,].*?\n', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'表\s*\d+[^\n]*', '', text)
    
    text = re.sub(r'^[\s\-\─\—\|]{3,}$', '', text, flags=re.MULTILINE)
    
    patterns = [
        r'参考文献\s*[\[（(]?\d*[\]）)]?\s*[\n:].*',
        r'References\s*[\[（(]?\d*[\]）)]?\s*[\n:].*',
        r'\[参考文献\].*',
        r'【参考文献】.*',
        r'参考文献：.*',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\（\d+\）', '', text)
    text = re.sub(r'\(\d+\)', '', text)
    text = re.sub(r'\[\d+[-,]\d+\]', '', text)
    
    text = re.sub(r'\[J\]\.\s*[^\n]+', '', text)
    text = re.sub(r'\[M\]\.\s*[^\n]+', '', text)
    text = re.sub(r'\[C\]\.\s*[^\n]+', '', text)
    text = re.sub(r'\[D\]\.\s*[^\n]+', '', text)
    
    text = re.sub(r'^[\u4e00-\u9fa5]+[，,][^，,\n]*[，,]\s*\d{4}[，,:：].*?[\d~－—]+.*?\.\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[A-Za-z\s]+[A-Z][^,\n]*[，,].*?\d{4}.*?\.\s*$', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'^[A-Za-z]+\s+[A-Za-z]+[,\s]+[A-Za-z\s]+[,\s]*\d{4}[,\s\.].*?\.\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[A-Za-z\.]+\s+[A-Za-z\.]+.*?\d{4}.*?[\d~－—]+.*?\.\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\s*[\u4e00-\u9fa5A-Za-z]+.*?[\d~－—]+\d+.*?\.\s*$', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'^[A-Za-z]+\s+for\s+the\s+evaluation\s+of.*?\.\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^[A-Za-z\s]+[A-Za-z]+[,\s]+[A-Za-z\s]+et\s+al\..*?\.\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^[\u4e00-\u9fa5]+[\u4e00-\u9fa5\s]+等\s+[\u4e00-\u9fa5A-Za-z]+.*?\.\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\u4e00-\u9fa5]+[\u4e00-\u9fa5\s]+\.\s*[\d\-~－—]+\s*\.?\s*$', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'目\s*录\s*\n.*?(?=\n\n|\n[一二三四五六七八九十])', '', text, flags=re.DOTALL)
    
    text = re.sub(r'第\s*\d+\s*页\s*(共\s*\d+\s*页)?', '', text)
    text = re.sub(r'Page\s*\d+', '', text, flags=re.IGNORECASE)
    
    text = re.sub(r'收稿日期.*', '', text)
    text = re.sub(r'作者简介.*', '', text)
    text = re.sub(r'基金项目.*', '', text)
    text = re.sub(r'通信作者.*', '', text)
    
    text = re.sub(r'DOI:?\s*\S+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'https?://\S+', '', text)
    
    text = re.sub(r'^\s*\d+\.\s*[\u4e00-\u9fa5]+(?:大学|学院|中心|站|局|所).*?\n', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^\s*\n', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    text = re.sub(r'^[、，,。\s]+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n[、，,。\s]+', '\n', text)
    
    text = re.sub(r'^\d+%?\s*[。，、；：]\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\s*[。，、；：]\s*\n', '', text, flags=re.MULTILINE)
    
    text = re.sub(r'^\s*\d+(?:\.\d+)?%\s*$', '', text, flags=re.MULTILINE)
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            if re.match(r'^[、，,。\s]', line):
                line = re.sub(r'^[、，,。\s]+', '', line)
            cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)
    
    return text.strip()


def preprocess_file(input_path: str, output_path: str = None) -> str:
    """
    预处理文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径（可选）
        
    Returns:
        处理后的文本
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    processed = preprocess_text(text)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(processed)
    
    return processed


def preprocess_directory(input_dir: str, output_dir: str = None):
    """
    预处理目录下所有txt文件
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录（可选）
    """
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    txt_files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
    
    for filename in txt_files:
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename) if output_dir else None
        
        original_len = len(open(input_path, 'r', encoding='utf-8').read())
        processed = preprocess_file(input_path, output_path)
        processed_len = len(processed)
        
        print(f"{filename}: {original_len} -> {processed_len} 字符 ({processed_len/original_len*100:.1f}%)")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = preprocess_file(sys.argv[1])
        print(f"原文长度: {len(open(sys.argv[1], 'r', encoding='utf-8').read())}")
        print(f"处理后长度: {len(result)}")
        print(f"压缩比: {len(result)/len(open(sys.argv[1], 'r', encoding='utf-8').read())*100:.1f}%")

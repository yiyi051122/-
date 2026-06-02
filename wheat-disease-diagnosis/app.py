# -*- coding: utf-8 -*-
"""知识增强优化的小麦病害辅助诊断问答系统 - 支持模块化检索对比实验
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import streamlit as st
import sys
import time
import json
import re
from io import BytesIO
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SYSTEM_NAME, SYSTEM_DESCRIPTION, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, CHROMA_PERSIST_DIR
from src.rag.langchain_rag import WheatDiseaseLangChain


VALID_USERNAME = "xiaomai"
VALID_PASSWORD = "12345678"


def clean_markdown(text):
    if not text:
        return text
    
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'^\s*[-*+]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def create_pdf_report(user_input, diagnosis_result, diagnosis_time):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.units import cm
        
        pdfmetrics.registerFont(TTFont('SimSun', 'C:/Windows/Fonts/simsun.ttc', subfontIndex=0))
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='SimSun',
            fontSize=18,
            alignment=1,
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName='SimSun',
            fontSize=14,
            spaceAfter=10
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName='SimSun',
            fontSize=12,
            leading=18
        )
        
        story = []
        
        story.append(Paragraph('小麦病害诊断报告', title_style))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph(f'诊断时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', body_style))
        story.append(Paragraph(f'诊断耗时: {diagnosis_time:.3f}秒', body_style))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph('用户输入:', heading_style))
        story.append(Paragraph(user_input, body_style))
        story.append(Spacer(1, 0.5*cm))
        
        story.append(Paragraph('诊断结果:', heading_style))
        clean_result = clean_markdown(diagnosis_result)
        for line in clean_result.split('\n'):
            if line.strip():
                story.append(Paragraph(line, body_style))
        
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    except Exception as e:
        import traceback
        error_msg = f"PDF生成失败: {str(e)}\n{traceback.format_exc()}"
        st.error(error_msg)
        return None


def load_custom_css():
    st.markdown("""
    <style>
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            padding: 1rem 0;
            margin-bottom: 2rem;
        }

        .main-header-small {
            font-size: 1.8rem;
            font-weight: 600;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            padding: 0.5rem 0;
            margin-bottom: 1rem;
        }
        
        .card {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.8);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .card-home {
            background: white;
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            margin-bottom: 1.5rem;
            border: 2px solid transparent;
            transition: all 0.3s ease;
            cursor: pointer;
            min-height: 180px;
        }

        .card-home:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 40px rgba(102, 126, 234, 0.25);
            border-color: #667eea;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
        }
        
        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1a1a2e;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .card-title-home {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        
        .metric-label {
            font-size: 0.875rem;
            opacity: 0.9;
        }
        
        .status-success {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .status-error {
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .status-warning {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .stTextArea textarea {
            border-radius: 12px;
            border: 2px solid #e0e0e0;
            transition: border-color 0.3s ease;
        }
        
        .stTextArea textarea:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 12px;
            padding: 0.75rem 2rem;
            font-weight: 600;
            color: white;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }

        .stButton > button.home-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            color: white;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            font-size: 0.875rem;
        }
        
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        }
        
        [data-testid="stSidebar"] .element-container {
            color: white;
        }
        
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {
            color: white !important;
        }
        
        .diagnosis-result {
            background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
            border-radius: 16px;
            padding: 1.5rem;
            border-left: 4px solid #667eea;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px 12px 0 0;
            padding: 10px 20px;
            background-color: #f0f2f6;
            border: none;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .footer {
            text-align: center;
            padding: 2rem 0;
            color: #666;
            font-size: 0.875rem;
        }
        
        .info-box {
            background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
            border-radius: 12px;
            padding: 1rem;
            border-left: 4px solid #00bcd4;
            margin-bottom: 1rem;
        }
        
        .success-box {
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            border-radius: 12px;
            padding: 1rem;
            border-left: 4px solid #4caf50;
            margin-bottom: 1rem;
        }
        
        .warning-box {
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            border-radius: 12px;
            padding: 1rem;
            border-left: 4px solid #ff9800;
            margin-bottom: 1rem;
        }
        
        .module-tag {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 15px;
            font-size: 0.75rem;
            margin: 0.25rem;
            font-weight: 500;
        }
        
        .module-tag-disabled {
            display: inline-block;
            background: #e0e0e0;
            color: #999;
            padding: 0.25rem 0.75rem;
            border-radius: 15px;
            font-size: 0.75rem;
            margin: 0.25rem;
            font-weight: 500;
        }
        
        .preset-btn {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            color: white;
            cursor: pointer;
            margin: 0.25rem;
            font-size: 0.8rem;
            transition: all 0.2s ease;
        }
        
        .preset-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .preset-btn-active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: transparent;
        }

        .login-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 2rem;
        }

        .login-card {
            background: white;
            border-radius: 24px;
            padding: 3rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
        }

        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .login-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }

        .login-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.5rem;
        }

        .login-subtitle {
            font-size: 0.9rem;
            color: #666;
        }

        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }

        .feature-desc {
            font-size: 0.95rem;
            color: #666;
            line-height: 1.6;
        }
    </style>
    """, unsafe_allow_html=True)


class WheatDiseaseDiagnosisSystemHybrid:
    def __init__(self):
        self.rag = None
        self._initialized = False
        self._enabled_modules = {"kg", "dense", "bm25"}
    
    def _ensure_initialized(self):
        if not self._initialized:
            self.rag = WheatDiseaseLangChain(enabled_modules=self._enabled_modules)
            self._initialized = True
    
    def set_enabled_modules(self, modules):
        self._enabled_modules = modules
        if self._initialized and self.rag:
            self.rag.set_enabled_modules(modules)
    
    def get_enabled_modules(self):
        return self._enabled_modules
    
    def diagnose(self, user_input):
        self._ensure_initialized()
        
        if not user_input or not user_input.strip():
            return None, "请输入症状描述"
        
        try:
            start_time = time.time()
            contexts = self.rag.retrieve(user_input)
            retrieval_time = time.time() - start_time
            
            start_time = time.time()
            result = self.rag.diagnose(user_input)
            diagnosis_time = time.time() - start_time
            
            return result, {
                "retrieval_time": retrieval_time,
                "diagnosis_time": diagnosis_time,
                "total_time": retrieval_time + diagnosis_time,
                "contexts": contexts,
                "enabled_modules": self._enabled_modules
            }
        except Exception as e:
            import traceback
            return None, f"诊断失败: {str(e)}\n{traceback.format_exc()}"
    
    def close(self):
        if self.rag:
            self.rag.close()


def init_session_state():
    if 'system' not in st.session_state:
        st.session_state.system = WheatDiseaseDiagnosisSystemHybrid()
    if 'diagnosis_history' not in st.session_state:
        st.session_state.diagnosis_history = []
    if 'enabled_modules' not in st.session_state:
        st.session_state.enabled_modules = {"kg", "dense", "bm25"}
    if 'test_results' not in st.session_state:
        st.session_state.test_results = None
    if 'test_running' not in st.session_state:
        st.session_state.test_running = False
    if 'full_test_results' not in st.session_state:
        st.session_state.full_test_results = None
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'login'


def render_login_page():
    load_custom_css()
    
    st.markdown("""
    <div class="login-container">
        <div class="login-card">
            <div class="login-header">
                <div class="login-icon">🌾</div>
                <div class="login-title">知识增强优化的小麦病害辅助诊断问答系统</div>
            </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="margin-bottom: 1.5rem; width: 50%; margin-left: auto; margin-right: auto;">
    """, unsafe_allow_html=True)
    
    username = st.text_input("账号", placeholder="请输入账号", key="login_username")
    password = st.text_input("密码", placeholder="请输入密码", type="password", key="login_password")
    
    st.markdown("""
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("登录", type="primary", use_container_width=True):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.session_state.logged_in = True
            st.session_state.current_page = 'home'
            st.rerun()
        else:
            st.markdown("""
            <div class="status-error" style="text-align: center;">
                <span>✗</span> 账号或密码错误
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("""
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_home_page():
    load_custom_css()
    
    st.markdown(f'<h1 class="main-header">🏠 {SYSTEM_NAME}</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>📌 欢迎使用小麦病害辅助诊断系统</strong><br>
        请选择下方功能模块开始使用系统功能。
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("""
        <div class="card-home">
            <div class="feature-icon">🔍</div>
            <div class="card-title-home">病害诊断</div>
            <div class="feature-desc">输入小麦病害症状描述，系统将提供详细的病害分析和防治建议。</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 进入病害诊断", key="btn_diagnosis", use_container_width=True, type="primary"):
            st.session_state.current_page = 'diagnosis'
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="card-home">
            <div class="feature-icon">🧪</div>
            <div class="card-title-home">检索测试</div>
            <div class="feature-desc">对不同检索方案进行对比测试，支持7种组合方案的召回率、精确率、F1分数和命中率评估。</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🧪 进入检索测试", key="btn_test", use_container_width=True, type="primary"):
            st.session_state.current_page = 'test'
            st.rerun()
    
    col3, col4 = st.columns(2, gap="large")
    
    with col3:
        st.markdown("""
        <div class="card-home">
            <div class="feature-icon">📊</div>
            <div class="card-title-home">向量数据库</div>
            <div class="feature-desc">可视化管理Chroma向量数据库，支持文档列表浏览、相似度搜索和统计信息查看。</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📊 进入向量数据库", key="btn_vector", use_container_width=True, type="primary"):
            st.session_state.current_page = 'vector_db'
            st.rerun()
    
    with col4:
        st.markdown("""
        <div class="card-home">
            <div class="feature-icon">🕸️</div>
            <div class="card-title-home">知识图谱</div>
            <div class="feature-desc">可视化展示Neo4j知识图谱，包含节点统计、关系统计和实体列表浏览功能。</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🕸️ 进入知识图谱", key="btn_kg", use_container_width=True, type="primary"):
            st.session_state.current_page = 'knowledge_graph'
            st.rerun()


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <div style="font-size: 3rem;">🌾</div>
            <h2 style="margin: 0.5rem 0; color: white;">小麦病害诊断</h2>
            <p style="color: rgba(255,255,255,0.7); font-size: 0.875rem;">知识增强优化系统</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("### 🔧 检索模块配置")
        
        module_names = {
            "kg": "🕸️ 知识图谱 (KG)",
            "dense": "📊 向量检索 (Dense)",
            "bm25": "🔍 BM25关键词"
        }
        
        module_short_names = {
            "kg": "KG",
            "dense": "Dense",
            "bm25": "BM25"
        }
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            kg_enabled = st.checkbox("KG", value="kg" in st.session_state.enabled_modules, key="cb_kg")
        with col2:
            dense_enabled = st.checkbox("Dense", value="dense" in st.session_state.enabled_modules, key="cb_dense")
        with col3:
            bm25_enabled = st.checkbox("BM25", value="bm25" in st.session_state.enabled_modules, key="cb_bm25")
        
        new_modules = set()
        if kg_enabled:
            new_modules.add("kg")
        if dense_enabled:
            new_modules.add("dense")
        if bm25_enabled:
            new_modules.add("bm25")
        
        if not new_modules:
            new_modules = {"kg", "dense", "bm25"}
        
        st.session_state.enabled_modules = new_modules
        st.session_state.system.set_enabled_modules(new_modules)
        
        st.markdown("")
        st.markdown("**当前配置:**")
        enabled_display = " + ".join([module_short_names[m] for m in new_modules])
        st.markdown(f"<div style='text-align:center; color:#667eea; font-weight:600;'>{enabled_display}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📊 系统状态")
        
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            with driver.session() as session:
                node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            driver.close()
            st.markdown(f"""
            <div class="status-success">
                <span>✓</span> Neo4j: {node_count}节点, {rel_count}关系
            </div>
            """, unsafe_allow_html=True)
        except:
            st.markdown("""
            <div class="status-error">
                <span>✗</span> Neo4j: 未连接
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")
        
        if os.path.exists(CHROMA_PERSIST_DIR) and os.listdir(CHROMA_PERSIST_DIR):
            st.markdown("""
            <div class="status-success">
                <span>✓</span> ChromaDB: 已加载
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-warning">
                <span>!</span> ChromaDB: 未构建
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 🏠 导航")
        
        st.markdown("""
        <style>
            .sidebar-home-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0.75rem 1rem;
                width: 100%;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .sidebar-home-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }
        </style>
        """, unsafe_allow_html=True)
        
        if st.button("🏠 返回首页", key="sidebar_home", use_container_width=True, type="primary"):
            st.session_state.current_page = 'home'
            st.rerun()


def render_main_page():
    st.markdown('<h1 class="main-header">🔍 病害诊断</h1>', unsafe_allow_html=True)
    
    enabled_modules = st.session_state.enabled_modules
    module_short_names = {"kg": "KG", "dense": "Dense", "bm25": "BM25"}
    enabled_display = " + ".join([module_short_names[m] for m in enabled_modules])
    
    st.markdown(f"""
    <div class="info-box">
        <strong>📌 当前检索模式：</strong><span style="color:#667eea; font-weight:600;">{enabled_display}</span><br>
        输入小麦病害症状描述，系统将基于所选模块进行诊断。
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <div class="card-title">📝 症状描述</div>
    </div>
    """, unsafe_allow_html=True)
    
    user_input = st.text_area(
        "请描述病害症状：",
        placeholder="例如：小麦叶片出现黄色斑点，沿叶脉排列成行，呈虚线状...",
        height=120,
        label_visibility="collapsed"
    )
    
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        diagnose_btn = st.button("🔍 开始诊断", type="primary", use_container_width=True)
    
    if diagnose_btn:
        if not user_input.strip():
            st.markdown("""
            <div class="warning-box">
                <strong>⚠️ 提示：</strong>请输入症状描述后再进行诊断。
            </div>
            """, unsafe_allow_html=True)
        else:
            with st.spinner("🔄 正在诊断中..."):
                system = st.session_state.system
                result, info = system.diagnose(user_input)
                
                if result:
                    st.session_state.diagnosis_history.append({
                        "input": user_input,
                        "result": result,
                        "time": info.get("total_time", 0),
                        "modules": enabled_display
                    })
                    
                    st.markdown("""
                    <div class="success-box">
                        <strong>✅ 诊断完成！</strong>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{info['retrieval_time']:.3f}s</div>
                            <div class="metric-label">检索耗时</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{info['diagnosis_time']:.3f}s</div>
                            <div class="metric-label">诊断耗时</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{info['total_time']:.3f}s</div>
                            <div class="metric-label">总耗时</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    contexts = info.get("contexts", {})
                    
                    if contexts:
                        st.markdown("")
                        st.markdown("""
                        <div class="card">
                            <div class="card-title">📂 检索上下文详情</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        context_tabs = []
                        tab_names = []
                        if "kg" in enabled_modules:
                            tab_names.append("🕸️ 知识图谱")
                        if "dense" in enabled_modules:
                            tab_names.append("📊 向量检索")
                        if "bm25" in enabled_modules:
                            tab_names.append("🔍 BM25")
                        
                        if tab_names:
                            context_tabs = st.tabs(tab_names)
                            
                            tab_idx = 0
                            if "kg" in enabled_modules:
                                with context_tabs[tab_idx]:
                                    st.text_area("知识图谱检索结果", contexts.get("kg_context", "无"), height=150, key="ctx_kg")
                                tab_idx += 1
                            
                            if "dense" in enabled_modules:
                                with context_tabs[tab_idx]:
                                    st.text_area("向量检索结果", contexts.get("dense_context", "无"), height=150, key="ctx_dense")
                                tab_idx += 1
                            
                            if "bm25" in enabled_modules:
                                with context_tabs[tab_idx]:
                                    st.text_area("BM25检索结果", contexts.get("bm25_context", "无"), height=150, key="ctx_bm25")
                                tab_idx += 1
                    
                    st.markdown("")
                    st.markdown("""
                    <div class="card">
                        <div class="card-title">📋 诊断结果</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    clean_result = clean_markdown(result)
                    st.markdown(f"""
                    <div class="diagnosis-result">
                        {clean_result.replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    pdf_buffer = create_pdf_report(user_input, result, info.get('total_time', 0))
                    if pdf_buffer:
                        st.download_button(
                            label="📄 导出为PDF",
                            data=pdf_buffer,
                            file_name=f"诊断报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            key="download_pdf"
                        )
                else:
                    st.markdown(f"""
                    <div class="status-error">
                        <span>✗</span> 诊断失败: {info}
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown("")
    st.markdown("""
    <div class="card">
        <div class="card-title">📜 诊断历史</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.diagnosis_history:
        for i, record in enumerate(reversed(st.session_state.diagnosis_history[-5:])):
            with st.expander(f"[{record.get('modules', 'N/A')}] 耗时: {record['time']:.3f}s", expanded=False):
                st.markdown(f"**输入:** {record['input']}")
                st.markdown(f"**结果预览:** {record['result'][:150]}...")
    else:
        st.markdown("""
        <div style="text-align: center; color: #999; padding: 2rem;">
            <p>暂无诊断记录</p>
        </div>
        """, unsafe_allow_html=True)


def render_vector_db_page():
    st.markdown('<h1 class="main-header">📊 向量数据库可视化</h1>', unsafe_allow_html=True)
    
    if not os.path.exists(CHROMA_PERSIST_DIR) or not os.listdir(CHROMA_PERSIST_DIR):
        st.markdown("""
        <div class="warning-box">
            <strong>⚠️ 提示：</strong>向量数据库未构建，请先运行 build_vector_db.py
        </div>
        """, unsafe_allow_html=True)
        return
    
    try:
        import chromadb
        import pandas as pd
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        collections = client.list_collections()
        
        for collection in collections:
            count = collection.count()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">📁 集合: {collection.name}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{count}</div>
                    <div class="metric-label">文档数量(Chunk)</div>
                </div>
                """, unsafe_allow_html=True)
            
            if count > 0:
                tab1, tab2, tab3 = st.tabs(["📄 文档列表", "🔍 搜索测试", "📈 统计信息"])
                
                with tab1:
                    all_results = collection.get()
                    
                    df_data = []
                    for i, (doc_id, doc) in enumerate(zip(all_results['ids'], all_results['documents']), 1):
                        preview = doc[:100] + "..." if len(doc) > 100 else doc
                        df_data.append({
                            "序号": i,
                            "文档ID": doc_id,
                            "字数": len(doc),
                            "内容预览": preview.replace('\n', ' ')
                        })
                    
                    df = pd.DataFrame(df_data)
                    
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "序号": st.column_config.NumberColumn("序号", width="small"),
                            "文档ID": st.column_config.TextColumn("文档ID", width="medium"),
                            "字数": st.column_config.NumberColumn("字数", width="small"),
                            "内容预览": st.column_config.TextColumn("内容预览", width="large")
                        }
                    )
                    
                    st.caption(f"共 {count} 个文档片段")
                    
                    st.markdown("---")
                    st.markdown("**查看完整文档内容：**")
                    selected_idx = st.selectbox(
                        "选择文档序号：",
                        range(1, count + 1),
                        key="doc_selector"
                    )
                    
                    if selected_idx:
                        selected_doc = all_results['documents'][selected_idx - 1]
                        selected_id = all_results['ids'][selected_idx - 1]
                        st.markdown(f"**文档ID:** {selected_id}")
                        st.text_area("完整内容", selected_doc, height=200, key=f"full_doc_{selected_idx}")
                
                with tab2:
                    st.markdown("""
                    <div class="card">
                        <div class="card-title">向量相似度搜索</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    search_query = st.text_input(
                        "输入查询文本：",
                        placeholder="例如：小麦条锈病症状",
                        key="search_query"
                    )
                    
                    top_k = st.slider("返回结果数量", 1, 10, 5, key="top_k")
                    
                    if st.button("🔍 搜索", key="search_btn") and search_query:
                        search_results = collection.query(
                            query_texts=[search_query],
                            n_results=top_k
                        )
                        
                        if search_results['documents'] and search_results['documents'][0]:
                            st.markdown(f"""
                            <div class="success-box">
                                <strong>✅ 找到 {len(search_results['documents'][0])} 个相关文档</strong>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            search_df_data = []
                            for i, (doc, distance) in enumerate(zip(
                                search_results['documents'][0],
                                search_results['distances'][0]
                            ), 1):
                                similarity = 1 / (1 + distance)
                                preview = doc[:80] + "..." if len(doc) > 80 else doc
                                search_df_data.append({
                                    "排名": i,
                                    "相似度": f"{similarity:.2%}",
                                    "距离": f"{distance:.4f}",
                                    "内容预览": preview.replace('\n', ' ')
                                })
                            
                            search_df = pd.DataFrame(search_df_data)
                            st.dataframe(
                                search_df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "排名": st.column_config.NumberColumn("排名", width="small"),
                                    "相似度": st.column_config.TextColumn("相似度", width="small"),
                                    "距离": st.column_config.TextColumn("距离", width="small"),
                                    "内容预览": st.column_config.TextColumn("内容预览", width="large")
                                }
                            )
                            
                            st.markdown("---")
                            st.markdown("**查看完整搜索结果：**")
                            result_idx = st.selectbox(
                                "选择结果序号：",
                                range(1, len(search_results['documents'][0]) + 1),
                                key="search_result_selector"
                            )
                            
                            if result_idx:
                                full_doc = search_results['documents'][0][result_idx - 1]
                                st.text_area("完整内容", full_doc, height=200, key=f"full_search_{result_idx}")
                        else:
                            st.markdown("""
                            <div class="warning-box">
                                <strong>⚠️ 未找到相关文档</strong>
                            </div>
                            """, unsafe_allow_html=True)
                
                with tab3:
                    st.markdown("""
                    <div class="card">
                        <div class="card-title">文档长度分布</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    all_results = collection.get()
                    lengths = [len(doc) for doc in all_results['documents']]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总文档数", len(lengths))
                    with col2:
                        st.metric("最小长度", f"{min(lengths)} 字")
                    with col3:
                        st.metric("最大长度", f"{max(lengths)} 字")
                    with col4:
                        st.metric("平均长度", f"{sum(lengths)/len(lengths):.0f} 字")
                    
                    length_df = pd.DataFrame({'长度': lengths})
                    st.bar_chart(length_df['长度'].value_counts().sort_index())
        
    except Exception as e:
        st.markdown(f"""
        <div class="status-error">
            <span>✗</span> 读取向量数据库失败: {e}
        </div>
        """, unsafe_allow_html=True)


def run_full_evaluation():
    import json
    from itertools import combinations
    from datetime import datetime
    from dataclasses import asdict
    
    dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                "data", "evaluation", "qa_dataset_700.json")
    
    if not os.path.exists(dataset_path):
        return None, "测试数据集不存在"
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        qa_data = json.load(f)
    
    from src.evaluation.evaluate_7_schemes import UnifiedRetriever, calculate_metrics
    
    optimization_results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                             "data", "evaluation", "bayesian_optimization_results.json")
    optimized_weights = None
    if os.path.exists(optimization_results_path):
        with open(optimization_results_path, 'r', encoding='utf-8') as f:
            optimization_results = json.load(f)
            optimized_weights = optimization_results['best_weights']
    
    all_modules = ["kg", "dense", "bm25"]
    module_names = {"kg": "知识图谱", "dense": "向量检索", "bm25": "BM25"}
    
    schemes = []
    for r in range(1, len(all_modules) + 1):
        for combo in combinations(all_modules, r):
            schemes.append(set(combo))
    
    results = []
    
    for enabled_modules in schemes:
        scheme_name = " + ".join([module_names[m] for m in enabled_modules])
        
        scheme_weights = None
        if optimized_weights:
            scheme_weights = {m: optimized_weights.get(m, 1.0) for m in enabled_modules}
        
        retriever = UnifiedRetriever(enabled_modules, weights=scheme_weights)
        retriever.initialize()
        
        recall_list = []
        precision_list = []
        f1_list = []
        hit_rate_list = []
        
        start_time = time.time()
        
        for item in qa_data:
            query = item["question"]
            ground_truth = set(item["ground_truth_docs"])
            
            retrieved = retriever.retrieve(query, top_k=5)
            
            metrics = calculate_metrics(retrieved, ground_truth)
            recall_list.append(metrics.recall)
            precision_list.append(metrics.precision)
            f1_list.append(metrics.f1)
            hit_rate_list.append(metrics.hit_rate)
        
        elapsed = time.time() - start_time
        retriever.close()
        
        total = len(qa_data)
        result = {
            "scheme_name": scheme_name,
            "modules": list(enabled_modules),
            "total_queries": total,
            "avg_recall": sum(recall_list) / total,
            "avg_precision": sum(precision_list) / total,
            "avg_f1": sum(f1_list) / total,
            "avg_hit_rate": sum(hit_rate_list) / total,
            "time_elapsed": elapsed
        }
        results.append(result)
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               "data", "evaluation", "evaluation_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    output_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_queries": len(qa_data),
        "results": results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    test_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                      "data", "evaluation", "test_history.txt")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(test_history_path, 'a', encoding='utf-8') as f:
        f.write("\n")
        for r in results:
            modules_str = ",".join(sorted(r['modules']))
            history_line = f"{timestamp}\t{modules_str}\t{r['avg_recall']*100:.2f}%\t{r['avg_precision']*100:.2f}%\t{r['avg_f1']*100:.2f}%\t{r['avg_hit_rate']*100:.2f}\n"
            f.write(history_line)
        f.write("\n")
    
    return results, None


def run_retrieval_test(enabled_modules):
    import json
    from itertools import combinations
    from datetime import datetime
    
    dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                "data", "evaluation", "qa_dataset_700.json")
    
    if not os.path.exists(dataset_path):
        return None, "测试数据集不存在"
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        qa_data = json.load(f)
    
    from src.evaluation.evaluate_7_schemes import UnifiedRetriever, calculate_metrics
    
    optimization_results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                             "data", "evaluation", "bayesian_optimization_results.json")
    optimized_weights = None
    if os.path.exists(optimization_results_path):
        with open(optimization_results_path, 'r', encoding='utf-8') as f:
            optimization_results = json.load(f)
            optimized_weights = optimization_results['best_weights']
    
    scheme_weights = None
    if optimized_weights:
        scheme_weights = {m: optimized_weights.get(m, 1.0) for m in enabled_modules}
    
    retriever = UnifiedRetriever(enabled_modules, weights=scheme_weights)
    retriever.initialize()
    
    recall_list = []
    precision_list = []
    f1_list = []
    hit_rate_list = []
    
    start_time = time.time()
    
    for item in qa_data:
        query = item["question"]
        ground_truth = set(item["ground_truth_docs"])
        
        retrieved = retriever.retrieve(query, top_k=5)
        
        metrics = calculate_metrics(retrieved, ground_truth)
        recall_list.append(metrics.recall)
        precision_list.append(metrics.precision)
        f1_list.append(metrics.f1)
        hit_rate_list.append(metrics.hit_rate)
    
    elapsed = time.time() - start_time
    retriever.close()
    
    total = len(qa_data)
    results = {
        "scheme_name": " + ".join([{"kg": "知识图谱", "dense": "向量检索", "bm25": "BM25"}[m] for m in enabled_modules]),
        "total_queries": total,
        "avg_recall": sum(recall_list) / total,
        "avg_precision": sum(precision_list) / total,
        "avg_f1": sum(f1_list) / total,
        "avg_hit_rate": sum(hit_rate_list) / total,
        "time_elapsed": elapsed
    }
    
    test_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                      "data", "evaluation", "test_history.txt")
    os.makedirs(os.path.dirname(test_history_path), exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    modules_str = ",".join(sorted(enabled_modules))
    
    history_line = f"{timestamp}\t{modules_str}\t{results['avg_recall']*100:.2f}%\t{results['avg_precision']*100:.2f}%\t{results['avg_f1']*100:.2f}%\t{results['avg_hit_rate']*100:.2f}%\n"
    
    with open(test_history_path, 'a', encoding='utf-8') as f:
        f.write("\n")
        f.write(history_line)
        f.write("\n")
    
    return results, None


def render_test_page():
    st.markdown('<h1 class="main-header">🧪 检索方案测试</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>📌 测试说明：</strong><br>
        选择检索模块后点击测试按钮，系统将使用当前配置对700个问答对进行检索测试，计算召回率、精确率、F1分数和命中率。
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <div class="card-title">🔧 测试配置</div>
    </div>
    """, unsafe_allow_html=True)
    
    enabled_modules = st.session_state.enabled_modules
    module_names = {"kg": "知识图谱", "dense": "向量检索", "bm25": "BM25"}
    module_short_names = {"kg": "KG", "dense": "Dense", "bm25": "BM25"}
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        kg_enabled = st.checkbox("🕸️ 知识图谱 (KG)", value="kg" in enabled_modules, key="test_cb_kg")
    with col2:
        dense_enabled = st.checkbox("📊 向量检索 (Dense)", value="dense" in enabled_modules, key="test_cb_dense")
    with col3:
        bm25_enabled = st.checkbox("🔍 BM25关键词", value="bm25" in enabled_modules, key="test_cb_bm25")
    
    test_modules = set()
    if kg_enabled:
        test_modules.add("kg")
    if dense_enabled:
        test_modules.add("dense")
    if bm25_enabled:
        test_modules.add("bm25")
    
    if not test_modules:
        test_modules = {"kg", "dense", "bm25"}
    
    selected_display = " + ".join([module_names[m] for m in test_modules])
    st.markdown(f"**当前选择方案:** `{selected_display}`")
    
    st.markdown("")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        test_btn = st.button("🚀 开始测试", type="primary", use_container_width=True)
    with col2:
        full_test_btn = st.button("📊 完整评估", type="primary", use_container_width=True)
    
    if test_btn:
        st.session_state.test_running = True
        st.session_state.test_results = None
        st.session_state.full_test_results = None
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.markdown("""
        <div class="warning-box">
            <strong>⏳ 正在初始化测试环境...</strong>
        </div>
        """, unsafe_allow_html=True)
        
        progress_bar.progress(10)
        
        status_text.markdown("""
        <div class="warning-box">
            <strong>⏳ 正在加载测试数据集 (700个问答对)...</strong>
        </div>
        """, unsafe_allow_html=True)
        
        progress_bar.progress(20)
        
        status_text.markdown(f"""
        <div class="warning-box">
            <strong>⏳ 正在测试方案: {selected_display}...</strong>
        </div>
        """, unsafe_allow_html=True)
        
        progress_bar.progress(30)
        
        results, error = run_retrieval_test(test_modules)
        
        progress_bar.progress(100)
        
        if error:
            status_text.markdown(f"""
            <div class="status-error">
                <span>✗</span> 测试失败: {error}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.session_state.test_results = results
            status_text.markdown("""
            <div class="success-box">
                <strong>✅ 测试完成！</strong>
            </div>
            """, unsafe_allow_html=True)
    
    if full_test_btn:
        st.session_state.test_running = True
        st.session_state.test_results = None
        st.session_state.full_test_results = None
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.markdown("""
        <div class="warning-box">
            <strong>⏳ 正在运行完整评估 (7种方案)...</strong>
        </div>
        """, unsafe_allow_html=True)
        
        progress_bar.progress(5)
        
        full_results, error = run_full_evaluation()
        
        progress_bar.progress(100)
        
        if error:
            status_text.markdown(f"""
            <div class="status-error">
                <span>✗</span> 评估失败: {error}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.session_state.full_test_results = full_results
            status_text.markdown("""
            <div class="success-box">
                <strong>✅ 完整评估完成！结果已保存到 evaluation_results.json</strong>
            </div>
            """, unsafe_allow_html=True)
    
    if st.session_state.test_results:
        results = st.session_state.test_results
        
        st.markdown("")
        st.markdown("""
        <div class="card">
            <div class="card-title">📊 测试结果</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"**测试方案:** `{results['scheme_name']}`")
        st.markdown(f"**测试样本数:** {results['total_queries']} 个问答对")
        st.markdown(f"**测试耗时:** {results['time_elapsed']:.2f} 秒")
        
        st.markdown("")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{results['avg_recall']*100:.2f}%</div>
                <div class="metric-label">召回率 (Recall)</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{results['avg_precision']*100:.2f}%</div>
                <div class="metric-label">精确率 (Precision)</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{results['avg_f1']*100:.2f}%</div>
                <div class="metric-label">F1分数</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{results['avg_hit_rate']*100:.2f}%</div>
                <div class="metric-label">命中率 (Hit Rate)</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")
        st.markdown("""
        <div class="card">
            <div class="card-title">📖 指标说明</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        | 指标 | 公式 | 含义 |
        |------|------|------|
        | **召回率** | 检索到的相关文档数 / 所有相关文档数 | 在所有相关文档中，检索系统找回了多少 |
        | **精确率** | 检索到的相关文档数 / 检索返回的总文档数 | 在检索返回的文档中，有多少是真正相关的 |
        | **F1分数** | 2 × (Precision × Recall) / (Precision + Recall) | 精确率和召回率的调和平均数 |
        | **命中率** | Top-K结果中是否包含相关文档 (1=是, 0=否) | 检索结果是否命中了相关文档 |
        """)
        
        st.markdown("")
        st.markdown("""
        <div class="card">
            <div class="card-title">📋 历史测试记录</div>
        </div>
        """, unsafe_allow_html=True)
        
        test_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                         "data", "evaluation", "test_history.txt")
        
        if os.path.exists(test_history_path):
            with open(test_history_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if lines:
                import pandas as pd
                
                header = ["测试时间", "检索模块", "召回率", "精确率", "F1分数", "命中率"]
                data_rows = []
                for line in lines:
                    parts = line.strip().split('\t')
                    if len(parts) >= 6:
                        data_rows.append(parts[:6])
                
                if data_rows:
                    data_rows = data_rows[-10:]
                    
                    df = pd.DataFrame(data_rows, columns=header)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.markdown("""
                    <div style="text-align: center; color: #999; padding: 1rem;">
                        <p>暂无有效历史记录</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="text-align: center; color: #999; padding: 1rem;">
                    <p>暂无历史测试记录</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center; color: #999; padding: 1rem;">
                <p>暂无历史测试记录，测试完成后将自动保存</p>
            </div>
            """, unsafe_allow_html=True)
    
    if 'full_test_results' in st.session_state and st.session_state.full_test_results:
        full_results = st.session_state.full_test_results
        
        st.markdown("")
        st.markdown("""
        <div class="card">
            <div class="card-title">📊 完整评估结果 (7种方案对比)</div>
        </div>
        """, unsafe_allow_html=True)
        
        import pandas as pd
        
        df_data = []
        for r in full_results:
            df_data.append({
                "检索方案": r['scheme_name'],
                "召回率": f"{r['avg_recall']*100:.2f}%",
                "精确率": f"{r['avg_precision']*100:.2f}%",
                "F1分数": f"{r['avg_f1']*100:.2f}%",
                "命中率": f"{r['avg_hit_rate']*100:.2f}%",
                "耗时(秒)": f"{r['time_elapsed']:.2f}"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_knowledge_graph_page():
    st.markdown('<h1 class="main-header">🕸️ 知识图谱可视化</h1>', unsafe_allow_html=True)
    
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{node_count}</div>
                    <div class="metric-label">节点总数</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{rel_count}</div>
                    <div class="metric-label">关系总数</div>
                </div>
                """, unsafe_allow_html=True)
            
            tab1, tab2, tab3 = st.tabs(["📊 节点统计", "🔗 关系统计", "📋 实体列表"])
            
            with tab1:
                st.markdown("""
                <div class="card">
                    <div class="card-title">节点类型分布</div>
                </div>
                """, unsafe_allow_html=True)
                
                result = session.run("""
                    MATCH (n) 
                    RETURN labels(n)[0] as 类型, count(n) as 数量 
                    ORDER BY 数量 DESC
                """)
                data = [(r['类型'], r['数量']) for r in result]
                
                if data:
                    import pandas as pd
                    df = pd.DataFrame(data, columns=['类型', '数量'])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.bar_chart(df.set_index('类型')['数量'])
            
            with tab2:
                st.markdown("""
                <div class="card">
                    <div class="card-title">关系类型分布</div>
                </div>
                """, unsafe_allow_html=True)
                
                result = session.run("""
                    MATCH ()-[r]->() 
                    RETURN type(r) as 关系类型, count(r) as 数量 
                    ORDER BY 数量 DESC
                """)
                data = [(r['关系类型'], r['数量']) for r in result]
                
                if data:
                    import pandas as pd
                    df = pd.DataFrame(data, columns=['关系类型', '数量'])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.bar_chart(df.set_index('关系类型')['数量'])
            
            with tab3:
                st.markdown("""
                <div class="card">
                    <div class="card-title">实体浏览</div>
                </div>
                """, unsafe_allow_html=True)
                
                entity_type = st.selectbox(
                    "选择实体类型:",
                    ["Disease", "Symptom", "Stage", "Cause", "Control", "Pesticide", "Part"]
                )
                
                entity_labels = {
                    "Disease": "病害",
                    "Symptom": "症状",
                    "Stage": "生育期",
                    "Cause": "病因",
                    "Control": "防治方法",
                    "Pesticide": "药剂",
                    "Part": "危害部位"
                }
                
                if entity_type == "Disease":
                    result = session.run("MATCH (d:Disease) RETURN d.name as name ORDER BY name")
                elif entity_type == "Symptom":
                    result = session.run("MATCH (s:Symptom) RETURN s.desc as name ORDER BY name")
                elif entity_type == "Stage":
                    result = session.run("MATCH (st:Stage) RETURN st.name as name ORDER BY name")
                elif entity_type == "Cause":
                    result = session.run("MATCH (c:Cause) RETURN c.desc as name ORDER BY name")
                elif entity_type == "Control":
                    result = session.run("MATCH (ctrl:Control) RETURN ctrl.desc as name ORDER BY name")
                elif entity_type == "Pesticide":
                    result = session.run("MATCH (p:Pesticide) RETURN p.name as name ORDER BY name")
                elif entity_type == "Part":
                    result = session.run("MATCH (pt:Part) RETURN pt.name as name ORDER BY name")
                
                entities = [r['name'] for r in result]
                
                st.markdown(f"""
                <div class="info-box">
                    <strong>共 {len(entities)} 个 {entity_labels.get(entity_type, entity_type)} 实体</strong>
                </div>
                """, unsafe_allow_html=True)
                
                for i, name in enumerate(entities, 1):
                    st.markdown(f"**{i}.** {name}")
        
        driver.close()
        
    except Exception as e:
        st.markdown(f"""
        <div class="status-error">
            <span>✗</span> 连接Neo4j失败: {e}
        </div>
        """, unsafe_allow_html=True)


def main():
    page = st.session_state.get('current_page', 'login')
    
    if page == 'home':
        st.set_page_config(
            page_title="知识增强优化的小麦病害辅助诊断问答系统",
            page_icon="🌾",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
    else:
        st.set_page_config(
            page_title="知识增强优化的小麦病害辅助诊断问答系统",
            page_icon="🌾",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    init_session_state()
    
    if not st.session_state.logged_in:
        render_login_page()
        return
    
    load_custom_css()
    
    if page != 'home':
        render_sidebar()
    
    if page == 'home':
        render_home_page()
    elif page == 'diagnosis':
        render_main_page()
    elif page == 'test':
        render_test_page()
    elif page == 'vector_db':
        render_vector_db_page()
    elif page == 'knowledge_graph':
        render_knowledge_graph_page()


if __name__ == "__main__":
    main()
# ============================================
# 小麦病害辅助诊断系统配置文件
# ============================================

import os

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 系统信息
SYSTEM_NAME = "知识增强优化的小麦病害辅助诊断问答系统"
SYSTEM_DESCRIPTION = "基于知识图谱、向量检索和BM25的混合检索小麦病害诊断系统"

# Neo4j图数据库配置
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-bd4c96f2be2b4f5785d2ecf66f6180c7"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 向量数据库配置
FAISS_INDEX_DIR = os.path.join(PROJECT_ROOT, "data", "faiss_index")
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "data", "chroma_db")
EMBEDDING_MODEL = "moka-ai/m3e-base"

# 向量数据库类型选择: "chroma" 或 "faiss"
VECTOR_DB_TYPE = "chroma"

# 知识库配置 - 使用绝对路径
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_ROOT, "data", "knowledge_base")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# 系统配置
MAX_TOKENS = 1000
TEMPERATURE = 0.1
TOP_K_RETRIEVAL = 3

# 支持的病害类型（与extraction_rules.py保持一致）
DISEASE_TYPES = [
    "小麦条锈病", "小麦白粉病", "小麦赤霉病", "小麦纹枯病", "小麦叶锈病",
    "小麦丛矮病", "小麦全蚀病", "小麦叶枯病", "小麦基腐病", "小麦散黑穗病",
    "小麦斑点病", "小麦根腐病", "小麦灰霉病", "小麦炭疽病", "小麦白秆病",
    "小麦眼斑病", "小麦秆锈病", "小麦粒线虫病", "小麦红粉病", "小麦细菌性叶枯病",
    "小麦细菌性条斑病", "小麦胞囊线虫病", "小麦腥黑穗病", "小麦茎基腐病", "小麦蓝矮病",
    "小麦褐斑病", "小麦褐腐病", "小麦链格孢叶枯病", "小麦雪腐病", "小麦雪霉叶枯病",
    "小麦霜霉病", "小麦颖枯病", "小麦黄矮病", "小麦黄花叶病", "小麦黑胚病", "小麦黑颖病"
]

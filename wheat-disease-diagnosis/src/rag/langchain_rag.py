# -*- coding: utf-8 -*-
"""
LangChain集成模块
使用LangChain框架实现RAG检索和诊断生成
系统3：知识图谱 + Dense + BM25 混合检索（支持模块化开关）
"""

import os
import sys
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, DEEPSEEK_API_KEY, DEEPSEEK_API_URL, CHROMA_PERSIST_DIR, KNOWLEDGE_BASE_DIR, EMBEDDING_MODEL


@dataclass
class LangChainConfig:
    """LangChain配置"""
    neo4j_uri: str = NEO4J_URI
    neo4j_user: str = NEO4J_USER
    neo4j_password: str = NEO4J_PASSWORD
    chroma_persist_dir: str = CHROMA_PERSIST_DIR
    knowledge_base_dir: str = KNOWLEDGE_BASE_DIR
    deepseek_api_key: str = DEEPSEEK_API_KEY
    deepseek_api_url: str = DEEPSEEK_API_URL
    embedding_model: str = EMBEDDING_MODEL


class WheatDiseaseLangChain:
    """基于LangChain的小麦病害诊断系统 - 支持模块化检索"""
    
    AVAILABLE_MODULES = {"kg", "dense", "bm25"}
    
    MODULE_NAMES = {
        "kg": "知识图谱",
        "dense": "向量检索",
        "bm25": "BM25关键词检索"
    }
    
    DIAGNOSIS_PROMPT_TEMPLATE = """你是一位资深的小麦病害诊断专家。请根据以下知识信息，对用户的症状描述进行诊断。

{context_sections}

【用户描述】
{question}

【诊断要求】
1. 首先判断可能的病害名称
2. 分析症状匹配依据
3. 提供完整的防治建议
4. 如果信息不足，请说明需要补充的信息

请给出详细的诊断结果：
"""
    
    def __init__(self, config: Optional[LangChainConfig] = None, enabled_modules: Optional[Set[str]] = None):
        self.config = config or LangChainConfig()
        self._chroma_client = None
        self._chroma_collection = None
        self._embedding_model = None
        self._neo4j_driver = None
        self._bm25_retriever = None
        self._bm25_docs = []
        
        if enabled_modules is None:
            self.enabled_modules = {"kg", "dense", "bm25"}
        else:
            self.enabled_modules = enabled_modules & self.AVAILABLE_MODULES
            if not self.enabled_modules:
                self.enabled_modules = {"kg", "dense", "bm25"}
    
    def set_enabled_modules(self, modules: Set[str]):
        """设置启用的模块"""
        self.enabled_modules = modules & self.AVAILABLE_MODULES
        if not self.enabled_modules:
            self.enabled_modules = {"kg", "dense", "bm25"}
    
    def enable_module(self, module: str):
        """启用单个模块"""
        if module in self.AVAILABLE_MODULES:
            self.enabled_modules.add(module)
    
    def disable_module(self, module: str):
        """禁用单个模块"""
        if module in self.enabled_modules and len(self.enabled_modules) > 1:
            self.enabled_modules.discard(module)
    
    def is_module_enabled(self, module: str) -> bool:
        """检查模块是否启用"""
        return module in self.enabled_modules
    
    def get_enabled_modules_info(self) -> Dict[str, bool]:
        """获取所有模块的启用状态"""
        return {module: module in self.enabled_modules for module in self.AVAILABLE_MODULES}
    
    def get_enabled_modules_display(self) -> str:
        """获取启用的模块显示名称"""
        names = [self.MODULE_NAMES[m] for m in self.enabled_modules]
        return " + ".join(names)
    
    @property
    def chroma_collection(self):
        """延迟加载 ChromaDB 集合和嵌入模型 - 只使用自定义嵌入模型"""
        if self._chroma_collection is None:
            try:
                import chromadb
                self._chroma_client = chromadb.PersistentClient(path=self.config.chroma_persist_dir)
                self._chroma_collection = self._chroma_client.get_collection('wheat_disease_knowledge')
                print(f"ChromaDB 加载成功: {self._chroma_collection.count()} 个文档")
                
                print(f"加载嵌入模型: {self.config.embedding_model}")
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(self.config.embedding_model)
                print(f"嵌入模型加载成功!")
            except Exception as e:
                print(f"ChromaDB或嵌入模型加载失败，Dense检索将不可用: {e}")
                import traceback
                traceback.print_exc()
                self._chroma_collection = None
                self._embedding_model = None
        return self._chroma_collection
    
    @property
    def neo4j_driver(self):
        """延迟加载Neo4j驱动"""
        if self._neo4j_driver is None:
            try:
                from neo4j import GraphDatabase
                self._neo4j_driver = GraphDatabase.driver(
                    self.config.neo4j_uri,
                    auth=(self.config.neo4j_user, self.config.neo4j_password)
                )
                print("Neo4j 连接成功")
            except Exception as e:
                print(f"Neo4j连接失败: {e}")
        return self._neo4j_driver
    
    @property
    def bm25_retriever(self):
        """延迟加载BM25检索器"""
        if self._bm25_retriever is None:
            try:
                from rank_bm25 import BM25Okapi
                import jieba
                
                self._bm25_docs = []
                kb_dir = self.config.knowledge_base_dir
                
                if os.path.exists(kb_dir):
                    for filename in os.listdir(kb_dir):
                        if filename.endswith('.txt'):
                            filepath = os.path.join(kb_dir, filename)
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                                self._bm25_docs.append(content)
                
                if self._bm25_docs:
                    tokenized = [list(jieba.cut(doc)) for doc in self._bm25_docs]
                    self._bm25_retriever = BM25Okapi(tokenized)
                    print(f"BM25 索引构建成功: {len(self._bm25_docs)} 个文档")
            except Exception as e:
                print(f"BM25检索器初始化失败: {e}")
        return self._bm25_retriever
    
    def retrieve_from_kg(self, query: str) -> str:
        """从知识图谱检索 - 改进版"""
        if not self.is_module_enabled("kg"):
            return ""
        
        driver = self.neo4j_driver
        if not driver:
            return "知识图谱未连接"
        
        results = []
        found_diseases = set()
        
        try:
            import jieba
            
            stop_words = {'什么', '怎么', '如何', '哪些', '主要', '症状', '方法', '防治', 
                         '措施', '特点', '原因', '条件', '时期', '阶段', '进行', '可以',
                         '应该', '需要', '通过', '使用', '采用', '实施', '发生', '出现'}
            
            keywords = [w for w in jieba.cut(query) if len(w) > 1 and w not in stop_words]
            
            disease_keywords = []
            for kw in keywords:
                if any(x in kw for x in ['病', '锈', '霉', '腐', '枯', '粉', '矮', '黑', '斑']):
                    disease_keywords.append(kw)
            
            for keyword in disease_keywords:
                try:
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (d:Disease)
                            WHERE d.name CONTAINS $keyword
                            RETURN d.name as disease
                            LIMIT 10
                        """, keyword=keyword)
                        
                        for record in result:
                            if record['disease'] not in found_diseases:
                                found_diseases.add(record['disease'])
                except Exception:
                    pass
            
            for keyword in keywords:
                try:
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
                            WHERE s.desc CONTAINS $keyword
                            RETURN DISTINCT d.name as disease, s.desc as symptom
                            LIMIT 5
                        """, keyword=keyword)
                        
                        for record in result:
                            if record['disease'] not in found_diseases:
                                found_diseases.add(record['disease'])
                                results.append(f"病害: {record['disease']}, 症状: {record['symptom']}")
                except Exception:
                    pass
                
                try:
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (d:Disease)-[:CAUSED_BY]->(c:Cause)
                            WHERE c.desc CONTAINS $keyword
                            RETURN DISTINCT d.name as disease, c.desc as cause
                            LIMIT 5
                        """, keyword=keyword)
                        
                        for record in result:
                            if record['disease'] not in found_diseases:
                                found_diseases.add(record['disease'])
                                results.append(f"病害: {record['disease']}, 病因: {record['cause']}")
                except Exception:
                    pass
                
                try:
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (d:Disease)-[:HAS_CONTROL]->(c:Control)
                            WHERE c.desc CONTAINS $keyword
                            RETURN DISTINCT d.name as disease, c.desc as control
                            LIMIT 5
                        """, keyword=keyword)
                        
                        for record in result:
                            if record['disease'] not in found_diseases:
                                found_diseases.add(record['disease'])
                                results.append(f"病害: {record['disease']}, 防治: {record['control']}")
                except Exception:
                    pass
                
                try:
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (d:Disease)-[:USES_PESTICIDE]->(p:Pesticide)
                            WHERE p.name CONTAINS $keyword
                            RETURN DISTINCT d.name as disease, p.name as pesticide
                            LIMIT 5
                        """, keyword=keyword)
                        
                        for record in result:
                            if record['disease'] not in found_diseases:
                                found_diseases.add(record['disease'])
                                results.append(f"病害: {record['disease']}, 药剂: {record['pesticide']}")
                except Exception:
                    pass
        
        except Exception:
            pass
        
        if results:
            return "\n".join(results)
        return "未找到相关知识"
    
    def retrieve_from_dense(self, query: str, top_k: int = 3) -> str:
        """向量检索 (Dense Retrieval) - 只使用自定义嵌入模型"""
        if not self.is_module_enabled("dense"):
            return ""
        
        collection = self.chroma_collection
        if not collection:
            return "向量数据库未加载"
        
        if not hasattr(self, '_embedding_model') or self._embedding_model is None:
            return "嵌入模型未加载，Dense检索不可用"
        
        try:
            query_embedding = self._embedding_model.encode(query).tolist()
            results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
            
            if results['documents'] and results['documents'][0]:
                output = []
                for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0]), 1):
                    preview = doc[:300] + "..." if len(doc) > 300 else doc
                    source = ""
                    if results.get('metadatas') and results['metadatas'][0]:
                        metadata = results['metadatas'][0][i-1]
                        source = metadata.get('source', '')
                        if source:
                            source = f" [来源: {source}]"
                    output.append(f"{i}. [相似度:{1-dist:.3f}]{source}\n{preview}")
                return "\n".join(output)
            return "未找到相关文档"
        except Exception as e:
            return f"向量检索失败: {str(e)}"
    
    def retrieve_from_bm25(self, query: str, top_k: int = 3) -> str:
        """BM25关键词检索"""
        if not self.is_module_enabled("bm25"):
            return ""
        
        if not self.bm25_retriever or not self._bm25_docs:
            return "BM25索引未加载"
        
        try:
            import jieba
            tokenized_query = list(jieba.cut(query))
            scores = self.bm25_retriever.get_scores(tokenized_query)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            
            results = []
            for i, idx in enumerate(top_indices, 1):
                if scores[idx] > 0:
                    preview = self._bm25_docs[idx][:300] + "..." if len(self._bm25_docs[idx]) > 300 else self._bm25_docs[idx]
                    results.append(f"{i}. [得分:{scores[idx]:.2f}] {preview}")
            
            return "\n".join(results) if results else "未找到相关文档"
        except Exception as e:
            return f"BM25检索失败: {str(e)}"
    
    def retrieve(self, query: str) -> Dict[str, str]:
        """综合检索 - 根据启用的模块返回对应结果"""
        return {
            "kg_context": self.retrieve_from_kg(query) if self.is_module_enabled("kg") else "",
            "dense_context": self.retrieve_from_dense(query) if self.is_module_enabled("dense") else "",
            "bm25_context": self.retrieve_from_bm25(query) if self.is_module_enabled("bm25") else ""
        }
    
    def _build_context_sections(self, contexts: Dict[str, str]) -> str:
        """根据启用的模块构建上下文部分"""
        sections = []
        
        if self.is_module_enabled("kg") and contexts.get("kg_context"):
            sections.append(f"【知识图谱信息】\n{contexts['kg_context']}")
        
        if self.is_module_enabled("dense") and contexts.get("dense_context"):
            sections.append(f"【向量检索信息】\n{contexts['dense_context']}")
        
        if self.is_module_enabled("bm25") and contexts.get("bm25_context"):
            sections.append(f"【BM25关键词检索信息】\n{contexts['bm25_context']}")
        
        return "\n\n".join(sections) if sections else "无检索信息"
    
    def diagnose(self, question: str) -> str:
        """诊断 - 使用DeepSeek API"""
        contexts = self.retrieve(question)
        
        context_sections = self._build_context_sections(contexts)
        
        prompt = self.DIAGNOSIS_PROMPT_TEMPLATE.format(
            context_sections=context_sections,
            question=question
        )
        
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.config.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一位专业的小麦病害诊断专家。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            api_url = "https://api.deepseek.com/chat/completions"
            
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"API调用失败: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"诊断失败: {str(e)}"
    
    def close(self):
        """关闭连接"""
        if self._neo4j_driver:
            self._neo4j_driver.close()


def create_langchain_rag(enabled_modules: Optional[Set[str]] = None):
    """创建LangChain RAG实例"""
    return WheatDiseaseLangChain(enabled_modules=enabled_modules)


if __name__ == "__main__":
    rag = create_langchain_rag()
    
    test_query = "小麦叶片出现黄色斑点"
    print(f"查询: {test_query}")
    print(f"启用模块: {rag.get_enabled_modules_display()}")
    
    contexts = rag.retrieve(test_query)
    print("\n知识图谱结果:")
    print(contexts["kg_context"])
    
    print("\n向量检索结果:")
    print(contexts["dense_context"])
    
    print("\nBM25检索结果:")
    print(contexts["bm25_context"])
    
    print("\n诊断结果:")
    print(rag.diagnose(test_query))

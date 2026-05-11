# -*- coding: utf-8 -*-
"""
RAG检索增强模块
结合知识图谱和向量知识库进行检索
"""

import sys
sys.path.append('..')
from config import TOP_K_RETRIEVAL


class RAGRetriever:
    """RAG检索器"""
    
    def __init__(self):
        self._kg = None
        self._kb_builder = None
        self._vector_store = None
    
    @property
    def kg(self):
        """延迟加载知识图谱"""
        if self._kg is None:
            try:
                from src.knowledge_graph.kg_retriever import WheatDiseaseKG
                self._kg = WheatDiseaseKG()
            except Exception as e:
                print(f"知识图谱加载失败: {e}")
        return self._kg
    
    @property
    def kb_builder(self):
        """延迟加载知识库构建器"""
        if self._kb_builder is None:
            try:
                from src.rag.knowledge_base import KnowledgeBaseBuilder
                self._kb_builder = KnowledgeBaseBuilder()
            except Exception as e:
                print(f"知识库构建器加载失败: {e}")
        return self._kb_builder
    
    def init_vector_store(self):
        """初始化向量存储"""
        if self._vector_store is None and self.kb_builder:
            try:
                self._vector_store = self.kb_builder.load_vector_store()
            except Exception as e:
                print(f"向量存储加载失败: {e}")
    
    def retrieve_from_kg(self, query):
        """从知识图谱检索"""
        if self.kg:
            return self.kg.retrieve(query)
        return "知识图谱未加载"
    
    def retrieve_from_kb(self, query, top_k=TOP_K_RETRIEVAL):
        """从向量知识库检索"""
        self.init_vector_store()
        
        if self._vector_store is None:
            return "知识库未加载"
        
        try:
            docs = self._vector_store.similarity_search(query, k=top_k)
            return "\n\n".join([doc.page_content for doc in docs])
        except Exception as e:
            return f"知识库检索失败: {str(e)}"
    
    def retrieve(self, query):
        """综合检索：知识图谱 + 向量知识库"""
        kg_context = self.retrieve_from_kg(query)
        kb_context = self.retrieve_from_kb(query)
        
        combined_context = f"""
【知识图谱检索结果】
{kg_context}

【知识库检索结果】
{kb_context}
"""
        return combined_context
    
    def close(self):
        """关闭连接"""
        if self._kg:
            self._kg.close()


def retrieve_context(query):
    """便捷函数：检索上下文"""
    retriever = RAGRetriever()
    try:
        return retriever.retrieve(query)
    finally:
        retriever.close()


if __name__ == "__main__":
    test_query = "小麦叶片出现黄色斑点"
    print(f"测试查询: {test_query}")
    print(retrieve_context(test_query))

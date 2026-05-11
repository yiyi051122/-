# -*- coding: utf-8 -*-
"""
小麦病害知识库构建模块
使用ChromaDB构建向量知识库
"""

import os
import sys
sys.path.append('..')
from config import KNOWLEDGE_BASE_DIR, CHROMA_PERSIST_DIR, CHUNK_SIZE, CHUNK_OVERLAP

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader


class KnowledgeBaseBuilder:
    """知识库构建器"""
    
    def __init__(self, knowledge_dir=KNOWLEDGE_BASE_DIR, persist_dir=CHROMA_PERSIST_DIR):
        self.knowledge_dir = knowledge_dir
        self.persist_dir = persist_dir
        self._embeddings = None
        self._vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "；", "，", " "]
        )
    
    @property
    def embeddings(self):
        """延迟加载embeddings"""
        if self._embeddings is None:
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                self._embeddings = HuggingFaceEmbeddings(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2"
                )
            except Exception as e:
                print(f"加载embedding模型失败: {e}")
                raise
        return self._embeddings
    
    def load_documents(self):
        """加载知识文档"""
        documents = []
        
        if os.path.exists(self.knowledge_dir):
            loader = DirectoryLoader(
                self.knowledge_dir,
                glob="**/*.txt",
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"}
            )
            documents = loader.load()
        
        return documents
    
    def split_documents(self, documents):
        """分割文档"""
        return self.text_splitter.split_documents(documents)
    
    def build_vector_store(self, documents=None):
        """构建向量存储"""
        from langchain_community.vectorstores import Chroma
        
        if documents is None:
            documents = self.load_documents()
        
        if not documents:
            print("警告: 没有找到知识文档，将创建空的知识库")
            documents = []
        
        split_docs = self.split_documents(documents)
        
        os.makedirs(self.persist_dir, exist_ok=True)
        
        vectorstore = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            persist_directory=self.persist_dir
        )
        
        print(f"知识库构建完成，共 {len(split_docs)} 个文档片段")
        return vectorstore
    
    def load_vector_store(self):
        """加载已有向量存储"""
        from langchain_community.vectorstores import Chroma
        
        if not os.path.exists(self.persist_dir):
            return self.build_vector_store()
        
        return Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings
        )


def build_knowledge_base():
    """构建知识库的便捷函数"""
    builder = KnowledgeBaseBuilder()
    return builder.build_vector_store()


if __name__ == "__main__":
    build_knowledge_base()

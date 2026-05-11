# -*- coding: utf-8 -*-
"""
向量数据库构建工具 - 使用支持中文的嵌入模型（简化版）
解决ChromaDB默认嵌入函数不支持中文的问题
"""

import os
import sys
import shutil

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import KNOWLEDGE_BASE_DIR, CHUNK_SIZE, CHUNK_OVERLAP, CHROMA_PERSIST_DIR, EMBEDDING_MODEL
from src.utils.text_preprocessor import preprocess_text


def split_text_recursive(text: str, chunk_size: int = 500, chunk_overlap: int = 50, separators=None):
    """递归分割文本"""
    if separators is None:
        separators = ["\n\n", "\n", "。", "；", "，", " "]
    
    final_chunks = []
    separator = separators[-1]
    new_separators = []
    
    for i, sep in enumerate(separators):
        if sep == "":
            separator = sep
            break
        if sep in text:
            separator = sep
            new_separators = separators[i + 1:]
            break
    
    if separator:
        splits = text.split(separator)
    else:
        splits = list(text)
    
    good_splits = []
    
    for split in splits:
        if len(split) < chunk_size:
            good_splits.append(split)
        else:
            if good_splits:
                merged_text = _merge_splits(good_splits, separator, chunk_size, chunk_overlap)
                final_chunks.extend(merged_text)
                good_splits = []
            
            if new_separators:
                recursive_chunks = split_text_recursive(split, chunk_size, chunk_overlap, new_separators)
                final_chunks.extend(recursive_chunks)
            else:
                final_chunks.append(split)
    
    if good_splits:
        merged_text = _merge_splits(good_splits, separator, chunk_size, chunk_overlap)
        final_chunks.extend(merged_text)
    
    return final_chunks


def _merge_splits(splits, separator, chunk_size, chunk_overlap):
    """合并分割片段"""
    merged_chunks = []
    current_chunk = []
    current_length = 0
    
    for split in splits:
        split_len = len(split)
        separator_len = len(separator) if current_chunk else 0
        
        if current_length + split_len + separator_len > chunk_size and current_chunk:
            merged_chunks.append(separator.join(current_chunk))
            
            while current_chunk and current_length > chunk_overlap:
                removed = current_chunk.pop(0)
                current_length -= len(removed)
                if current_chunk:
                    current_length -= len(separator)
            
            if not current_chunk:
                current_length = 0
        
        current_chunk.append(split)
        current_length += split_len + separator_len
    
    if current_chunk:
        merged_chunks.append(separator.join(current_chunk))
    
    return merged_chunks


def build_vector_db_chinese():
    """构建向量数据库 - 使用支持中文的嵌入模型"""
    print("=" * 60)
    print("向量数据库构建工具 (支持中文)")
    print("=" * 60)
    print(f"知识库目录: {KNOWLEDGE_BASE_DIR}")
    print(f"向量数据库目录: {CHROMA_PERSIST_DIR}")
    print(f"嵌入模型: {EMBEDDING_MODEL}")
    
    print("\n[1] 清理旧数据库...")
    if os.path.exists(CHROMA_PERSIST_DIR):
        try:
            shutil.rmtree(CHROMA_PERSIST_DIR)
            print("    已删除旧数据库目录")
        except Exception as e:
            print(f"    删除失败: {e}")
            print("    尝试继续...")
    
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        print(f"\n错误: 知识库目录不存在: {KNOWLEDGE_BASE_DIR}")
        return False
    
    txt_files = sorted([f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.txt')])
    
    if not txt_files:
        print(f"\n错误: 未找到任何 .txt 文件")
        return False
    
    print(f"\n[2] 加载文档，找到 {len(txt_files)} 个文件")
    
    texts = []
    metadatas = []
    
    for filename in txt_files:
        filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = preprocess_text(content)
            
            if content.strip():
                chunks = split_text_recursive(
                    content,
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                    separators=["\n\n", "\n", "。", "；", "，", " "]
                )
                
                for i, chunk in enumerate(chunks):
                    if chunk.strip():
                        texts.append(chunk)
                        metadatas.append({
                            "source": filename,
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        })
                
                if len(txt_files) <= 20 or txt_files.index(filename) % 10 == 0:
                    print(f"  加载: {filename} ({len(chunks)} 个分块)")
        except Exception as e:
            print(f"  读取失败 {filename}: {e}")
    
    print(f"\n共加载 {len(texts)} 个文档片段")
    
    if not texts:
        print("错误: 没有有效的文档内容")
        return False
    
    print("\n[3] 构建 ChromaDB 向量索引...")
    
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    
    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        
        print("    创建客户端...")
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        
        print(f"    加载嵌入模型: {EMBEDDING_MODEL}")
        print("    (首次运行需要下载模型，请耐心等待...)")
        
        embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        
        print("    删除旧集合（如果存在）...")
        try:
            client.delete_collection('wheat_disease_knowledge')
            print("    已删除旧集合")
        except:
            print("    没有旧集合需要删除")
        
        print("    创建集合...")
        collection = client.create_collection(
            name='wheat_disease_knowledge',
            embedding_function=embedding_function
        )
        
        ids = [str(i) for i in range(len(texts))]
        
        print(f"    添加 {len(texts)} 个文档片段...")
        print(f"    这可能需要几分钟时间...")
        
        batch_size = 30
        for i in range(0, len(texts), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_texts = texts[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            
            collection.add(
                documents=batch_texts, 
                ids=batch_ids,
                metadatas=batch_metas
            )
            
            progress = min(i+batch_size, len(texts))
            if progress % 60 == 0 or progress == len(texts):
                print(f"    已添加 {progress}/{len(texts)} ({progress*100//len(texts)}%)")
        
        print(f"\n[4] 向量数据库构建完成!")
        print(f"    存储位置: {CHROMA_PERSIST_DIR}")
        print(f"    文档片段数量: {collection.count()}")
        print(f"    源文件数量: {len(txt_files)}")
        print(f"    嵌入模型: {EMBEDDING_MODEL}")
        print(f"    中文支持: ✓")
        
        print("\n[5] 测试检索效果...")
        test_query = "小麦条锈病症状"
        results = collection.query(query_texts=[test_query], n_results=3)
        
        if results['documents'] and results['documents'][0]:
            print(f"    测试查询: {test_query}")
            print(f"    返回结果数: {len(results['documents'][0])}")
            print(f"    第一条文档预览: {results['documents'][0][0][:100]}...")
            if results.get('metadatas') and results['metadatas'][0]:
                print(f"    第一条来源: {results['metadatas'][0][0].get('source', 'N/A')}")
        
    except Exception as e:
        print(f"错误: 构建向量数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("构建完成! 使用支持中文的嵌入模型")
    print("查询时将使用相同的嵌入模型确保向量空间一致")
    print("=" * 60)
    return True


if __name__ == "__main__":
    build_vector_db_chinese()

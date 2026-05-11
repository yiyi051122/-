# -*- coding: utf-8 -*-
"""
7种检索方案对比评估脚本
正确的评估指标计算方式
"""

import os
import sys
import json
import time
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from itertools import combinations
from difflib import SequenceMatcher

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config import CHROMA_PERSIST_DIR, KNOWLEDGE_BASE_DIR, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, EMBEDDING_MODEL

DISEASE_NAMES_FOR_JIEBA = [
    '白秆病', '条锈病', '叶锈病', '秆锈病', '白粉病', '赤霉病', 
    '纹枯病', '根腐病', '叶枯病', '全蚀病', '散黑穗病', '腥黑穗病',
    '秆黑粉病', '黄矮病', '丛矮病', '霜霉病', '雪腐病', '链格孢叶枯病',
    '土传花叶病毒病', '细菌性条斑病', '胞囊线虫病', '麦角病', '黑节病',
    '蓝矮病', '基腐病', '斑点病', '炭疽病', '灰霉病', '颖枯病',
    '黄斑叶枯病', '黑颖病', '梭条斑花叶病', '秆枯病', '粒线虫病',
    '蜜穗病', '雪霉叶枯病', '蠕孢叶斑根腐病', '红矮病', '卷曲病',
    '花叶病毒病', '禾谷胞囊线虫病'
]

def _init_jieba():
    import jieba
    for name in DISEASE_NAMES_FOR_JIEBA:
        jieba.add_word(name)

_init_jieba()


@dataclass
class EvaluationMetrics:
    """评估指标"""
    recall: float
    precision: float
    f1: float
    hit_rate: float


@dataclass
class SchemeResult:
    """方案测试结果"""
    scheme_name: str
    modules: List[str]
    weights: Dict[str, float]
    total_queries: int
    avg_recall: float
    avg_precision: float
    avg_f1: float
    avg_hit_rate: float
    time_elapsed: float


def extract_disease_name(filename: str) -> str:
    """从文件名提取病害名称"""
    name = filename.replace('.txt', '').lower()
    
    disease_map = {
        '条锈病': ['条锈', 'stripe_rust'],
        '叶锈病': ['叶锈', 'leaf_rust'],
        '秆锈病': ['秆锈', 'stem_rust'],
        '白粉病': ['白粉', 'powdery_mildew', 'powd'],
        '赤霉病': ['赤霉', 'fusarium', 'head_blight'],
        '纹枯病': ['纹枯', 'sheath_blight', 'shea'],
        '根腐病': ['根腐', 'root_rot'],
        '叶枯病': ['叶枯', 'leaf_blight'],
        '全蚀病': ['全蚀'],
        '散黑穗病': ['散黑穗'],
        '腥黑穗病': ['腥黑穗'],
        '秆黑粉病': ['秆黑粉'],
        '黄矮病': ['黄矮'],
        '丛矮病': ['丛矮'],
        '霜霉病': ['霜霉'],
        '雪腐病': ['雪腐'],
        '链格孢叶枯病': ['链格孢'],
        '土传花叶病毒病': ['土传花叶'],
        '细菌性条斑病': ['细菌性条斑'],
        '胞囊线虫病': ['胞囊'],
        '麦角病': ['麦角'],
        '黑节病': ['黑节'],
        '蓝矮病': ['蓝矮'],
        '基腐病': ['基腐'],
        '斑点病': ['斑点'],
        '炭疽病': ['炭疽'],
        '灰霉病': ['灰霉'],
        '颖枯病': ['颖枯'],
        '黄斑叶枯病': ['黄斑'],
        '黑颖病': ['黑颖'],
        '梭条斑花叶病': ['梭条斑'],
        '秆枯病': ['秆枯'],
        '粒线虫病': ['粒线虫'],
        '蜜穗病': ['蜜穗'],
        '雪霉叶枯病': ['雪霉叶枯'],
        '蠕孢叶斑根腐病': ['蠕孢'],
        '红矮病': ['红矮'],
        '卷曲病': ['卷曲'],
        '白秆病': ['白秆'],
        '花叶病毒病': ['花叶病毒'],
        '禾谷胞囊线虫病': ['胞囊线虫'],
    }
    
    for disease, keywords in disease_map.items():
        for kw in keywords:
            if kw.lower() in name:
                return disease
    
    name_clean = filename.replace('.txt', '')
    name_clean = name_clean.replace('1小麦', '').replace('小麦', '')
    name_clean = name_clean.split('_')[0].strip()
    
    if '病毒' in name_clean:
        name_clean = name_clean.replace('病毒', '')
    
    return name_clean[:4] if len(name_clean) > 4 else name_clean


def calculate_similarity(s1: str, s2: str) -> float:
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, s1, s2).ratio()


def fuzzy_match_disease(name1: str, name2: str, threshold: float = 0.7) -> bool:
    """判断两个病害名称是否匹配"""
    if name1 == name2:
        return True
    
    if name1 in name2 or name2 in name1:
        return True
    
    if calculate_similarity(name1, name2) >= threshold:
        return True
    
    return False


class UnifiedRetriever:
    """统一检索器 - 支持7种方案"""
    
    def __init__(self, enabled_modules: Set[str], weights: Optional[Dict[str, float]] = None):
        self.enabled_modules = enabled_modules
        self.weights = weights or {m: 1.0 for m in enabled_modules}
        self._chroma_collection = None
        self._neo4j_driver = None
        self._bm25_retriever = None
        self._bm25_docs = []
        self._doc_files = []
        self._doc_contents = []
        
    def initialize(self):
        """初始化所有启用的模块"""
        if "bm25" in self.enabled_modules:
            self._init_bm25()
        
        if "dense" in self.enabled_modules:
            self._init_chroma()
        
        if "kg" in self.enabled_modules:
            self._init_neo4j()
        
        if not self._doc_files:
            self._load_doc_files()
        
        if not self._neo4j_driver:
            self._init_neo4j()
        
        self._build_disease_file_mapping()
    
    def _load_doc_files(self):
        """加载文档文件列表"""
        if os.path.exists(KNOWLEDGE_BASE_DIR):
            for filename in sorted(os.listdir(KNOWLEDGE_BASE_DIR)):
                if filename.endswith('.txt'):
                    filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self._bm25_docs.append(content)
                        self._doc_files.append(filename)
                        self._doc_contents.append(content)
    
    def _build_disease_file_mapping(self):
        """构建病害名称到文档文件的映射"""
        self._disease_file_map = {}
        
        if self._neo4j_driver:
            try:
                with self._neo4j_driver.session() as session:
                    result = session.run("MATCH (d:Disease) RETURN d.name as name")
                    diseases = [r['name'] for r in result]
                    
                    for disease_name in diseases:
                        disease_short = disease_name.replace("小麦", "")
                        matched_files = []
                        
                        for filename in self._doc_files:
                            file_disease = extract_disease_name(filename)
                            if fuzzy_match_disease(disease_short, file_disease, threshold=0.8):
                                matched_files.append(filename)
                        
                        self._disease_file_map[disease_name] = list(set(matched_files))
            except Exception:
                pass
    
    def _init_chroma(self):
        """初始化ChromaDB"""
        try:
            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            
            client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            embedding_function = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
            self._chroma_collection = client.get_collection(
                name='wheat_disease_knowledge',
                embedding_function=embedding_function
            )
        except Exception:
            self._chroma_collection = None
    
    def _init_neo4j(self):
        """初始化Neo4j"""
        try:
            from neo4j import GraphDatabase
            self._neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        except Exception:
            pass
    
    def _init_bm25(self):
        """初始化BM25"""
        try:
            from rank_bm25 import BM25Okapi
            import jieba
            
            self._bm25_docs = []
            self._doc_files = []
            self._doc_contents = []
            
            if os.path.exists(KNOWLEDGE_BASE_DIR):
                for filename in os.listdir(KNOWLEDGE_BASE_DIR):
                    if filename.endswith('.txt'):
                        filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            self._bm25_docs.append(content)
                            self._doc_files.append(filename)
                            self._doc_contents.append(content)
            
            if self._bm25_docs:
                tokenized = [list(jieba.cut(doc)) for doc in self._bm25_docs]
                self._bm25_retriever = BM25Okapi(tokenized)
        except Exception:
            pass
    
    def _retrieve_dense(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """向量检索"""
        if not self._chroma_collection:
            return []
        
        try:
            results = self._chroma_collection.query(query_texts=[query], n_results=20)
            file_scores = {}
            
            if results['documents'] and results['documents'][0]:
                for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0])):
                    source_file = None
                    if results.get('metadatas') and results['metadatas'][0]:
                        metadata = results['metadatas'][0][i]
                        source_file = metadata.get('source', '')
                    if not source_file:
                        source_file = self._match_doc_file(doc)
                    if source_file:
                        score = 1 - dist
                        if source_file not in file_scores or score > file_scores[source_file]:
                            file_scores[source_file] = score
            
            sorted_results = sorted(file_scores.items(), key=lambda x: (-x[1], x[0]))
            return sorted_results[:top_k]
        except Exception:
            return []
    
    def _retrieve_bm25(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """BM25检索"""
        if not self._bm25_retriever or not self._bm25_docs:
            return []
        
        try:
            import jieba
            
            tokenized_query = list(jieba.cut(query))
            tokenized_query = [w for w in tokenized_query if len(w) > 1]
            
            english_to_chinese = {
                'leaf': '叶锈',
                'stripe': '条锈',
                'stem': '秆锈',
                'powdery': '白粉',
                'fusarium': '赤霉',
            }
            
            for kw in list(tokenized_query):
                kw_lower = kw.lower()
                if kw_lower in english_to_chinese:
                    tokenized_query.append(english_to_chinese[kw_lower])
            
            if not tokenized_query:
                return []
            
            scores = self._bm25_retriever.get_scores(tokenized_query)
            scored_results = [(idx, scores[idx]) for idx in range(len(scores)) if scores[idx] > 0]
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            return [(self._doc_files[idx], score) for idx, score in scored_results[:top_k]]
        except Exception:
            return []
    
    def _retrieve_kg(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """知识图谱检索"""
        if not self._neo4j_driver:
            return []
        
        results = []
        found_diseases = {}
        
        try:
            import jieba
            
            stop_words = {'什么', '怎么', '如何', '哪些', '主要', '症状', '方法', '防治', 
                         '措施', '特点', '原因', '条件', '时期', '阶段', '进行', '可以',
                         '应该', '需要', '通过', '使用', '采用', '实施', '发生', '出现',
                         '小麦', '药剂', '发病', '用药', '治疗', '诊断', '识别', '特点',
                         '特征', '表现', '情况', '问题', '效果', '作用', '影响', '造成',
                         '引起', '导致', '危害', '损失', '产量', '品质', '品种', '栽培'}
            
            keywords = [w for w in jieba.cut(query) if len(w) > 1 and w not in stop_words]
            
            disease_keywords = []
            for kw in keywords:
                if any(x in kw for x in ['病', '锈', '霉', '腐', '枯', '粉', '矮', '黑', '斑']):
                    disease_keywords.append(kw)
            
            english_to_chinese = {
                'leaf': '叶锈', 'stripe': '条锈', 'stem': '秆锈',
                'powdery': '白粉', 'fusarium': '赤霉', 'sheath': '纹枯',
                'root': '根腐', 'blight': '枯'
            }
            
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in english_to_chinese:
                    disease_keywords.append(english_to_chinese[kw_lower])
            
            for keyword in disease_keywords:
                try:
                    with self._neo4j_driver.session() as session:
                        cypher = "MATCH (d:Disease) WHERE d.name CONTAINS $keyword RETURN d.name as disease LIMIT 5"
                        result = session.run(cypher, keyword=keyword)
                        for record in result:
                            disease_name = record['disease']
                            if disease_name not in found_diseases:
                                found_diseases[disease_name] = 10
                except Exception:
                    pass
                
                sub_keywords = []
                if len(keyword) >= 4:
                    for i in range(len(keyword) - 1):
                        sub = keyword[i:i+2]
                        if any(x in sub for x in ['病', '锈', '霉', '腐', '枯', '粉', '矮', '黑', '斑', '虫', '线']):
                            sub_keywords.append(sub)
                
                for sub_kw in sub_keywords:
                    try:
                        with self._neo4j_driver.session() as session:
                            cypher = "MATCH (d:Disease) WHERE d.name CONTAINS $keyword RETURN d.name as disease LIMIT 3"
                            result = session.run(cypher, keyword=sub_kw)
                            for record in result:
                                disease_name = record['disease']
                                if disease_name not in found_diseases:
                                    found_diseases[disease_name] = 8
                    except Exception:
                        pass
            
            symptom_keywords = [kw for kw in keywords if kw not in disease_keywords and len(kw) >= 2]
            
            for keyword in symptom_keywords[:3]:
                try:
                    with self._neo4j_driver.session() as session:
                        cypher = "MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom) WHERE s.desc CONTAINS $keyword RETURN DISTINCT d.name as disease LIMIT 3"
                        result = session.run(cypher, keyword=keyword)
                        for record in result:
                            disease_name = record['disease']
                            if disease_name not in found_diseases:
                                found_diseases[disease_name] = 5
                except Exception:
                    pass
                
                try:
                    with self._neo4j_driver.session() as session:
                        cypher = "MATCH (d:Disease)-[:CAUSED_BY]->(c:Cause) WHERE c.desc CONTAINS $keyword RETURN DISTINCT d.name as disease LIMIT 3"
                        result = session.run(cypher, keyword=keyword)
                        for record in result:
                            disease_name = record['disease']
                            if disease_name not in found_diseases:
                                found_diseases[disease_name] = 3
                except Exception:
                    pass
                
                try:
                    with self._neo4j_driver.session() as session:
                        cypher = "MATCH (d:Disease)-[:USES_PESTICIDE]->(p:Pesticide) WHERE p.name CONTAINS $keyword RETURN DISTINCT d.name as disease LIMIT 3"
                        result = session.run(cypher, keyword=keyword)
                        for record in result:
                            disease_name = record['disease']
                            if disease_name not in found_diseases:
                                found_diseases[disease_name] = 4
                except Exception:
                    pass
        except Exception:
            pass
        
        sorted_diseases = sorted(found_diseases.items(), key=lambda x: (-x[1], x[0]))
        
        for disease_name, score in sorted_diseases[:top_k]:
            matched_files = self._find_files_by_disease(disease_name)
            matched_files = sorted(matched_files)
            for f in matched_files:
                if f not in [r[0] for r in results]:
                    results.append((f, score / 10.0))
        
        return results[:top_k]
    
    def _match_doc_file(self, doc_content: str) -> Optional[str]:
        """根据文档内容匹配文件名"""
        if not self._doc_files or not self._doc_contents:
            return None
        
        doc_preview = doc_content[:150] if len(doc_content) > 150 else doc_content
        
        matches = []
        for filename, content in zip(self._doc_files, self._doc_contents):
            if doc_preview in content or content[:150] in doc_content:
                matches.append(filename)
        
        if matches:
            return sorted(matches)[0]
        
        best_match = None
        best_score = 0
        
        for filename, content in zip(self._doc_files, self._doc_contents):
            overlap = 0
            check_len = min(len(content), 1000)
            for i in range(0, check_len, 30):
                chunk = content[i:i+30]
                if len(chunk) >= 20 and chunk in doc_content:
                    overlap += 1
            if overlap > best_score or (overlap == best_score and overlap > 0 and (best_match is None or filename < best_match)):
                best_score = overlap
                best_match = filename
        
        if best_score >= 1:
            return best_match
        return None
    
    def _find_files_by_disease(self, disease_name: str) -> List[str]:
        """根据病害名称查找相关文件"""
        if hasattr(self, '_disease_file_map') and disease_name in self._disease_file_map:
            return sorted(self._disease_file_map.get(disease_name, []))
        
        matched = []
        disease_short = disease_name.replace("小麦", "")
        for filename in self._doc_files:
            file_disease = extract_disease_name(filename)
            if fuzzy_match_disease(disease_short, file_disease, threshold=0.8):
                matched.append(filename)
        return sorted(matched)
    
    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        """综合检索 - 加权RRF融合"""
        all_results = []
        k = 60
        
        if "kg" in self.enabled_modules:
            kg_results = self._retrieve_kg(query, top_k=10)
            weight = self.weights.get("kg", 1.0)
            for rank, (doc_id, score) in enumerate(kg_results, 1):
                rrf_score = weight / (k + rank)
                all_results.append((doc_id, rrf_score))
        
        if "dense" in self.enabled_modules:
            dense_results = self._retrieve_dense(query, top_k=10)
            weight = self.weights.get("dense", 1.0)
            for rank, (doc_id, score) in enumerate(dense_results, 1):
                rrf_score = weight / (k + rank)
                all_results.append((doc_id, rrf_score))
        
        if "bm25" in self.enabled_modules:
            bm25_results = self._retrieve_bm25(query, top_k=10)
            weight = self.weights.get("bm25", 1.0)
            for rank, (doc_id, score) in enumerate(bm25_results, 1):
                rrf_score = weight / (k + rank)
                all_results.append((doc_id, rrf_score))
        
        if not all_results:
            return []
        
        merged = {}
        for doc_id, score in all_results:
            if doc_id not in merged:
                merged[doc_id] = 0
            merged[doc_id] += score
        
        sorted_results = sorted(merged.items(), key=lambda x: (-x[1], x[0]))
        
        return [doc_id for doc_id, _ in sorted_results[:top_k]]
    
    def close(self):
        """关闭连接"""
        if self._neo4j_driver:
            self._neo4j_driver.close()


def calculate_metrics(retrieved: List[str], ground_truth: Set[str]) -> EvaluationMetrics:
    """
    计算评估指标
    
    关键改进：按病害名称计算精确率，而不是按文件数量
    
    例如：
    - ground_truth: "1小麦纹枯病.txt" -> 病害名称: "纹枯病"
    - retrieved: ["1小麦纹枯病.txt", "小麦纹枯病.txt", "小麦纹枯病的防治措施_武庆绪.txt", "小麦条锈病.txt", "小麦白粉病.txt"]
    - 涉及病害: ["纹枯病", "纹枯病", "纹枯病", "条锈病", "白粉病"] -> 去重后: ["纹枯病", "条锈病", "白粉病"]
    - 命中病害: "纹枯病"
    - 召回率: 1/1 = 100%
    - 精确率: 1/3 = 33.33%
    """
    if not ground_truth:
        return EvaluationMetrics(0, 0, 0, 0)
    
    if not retrieved:
        return EvaluationMetrics(0, 0, 0, 0)
    
    gt_diseases = set(extract_disease_name(f) for f in ground_truth)
    retrieved_diseases = [extract_disease_name(f) for f in retrieved]
    retrieved_diseases_unique = set(retrieved_diseases)
    
    hit_diseases = gt_diseases & retrieved_diseases_unique
    
    recall = len(hit_diseases) / len(gt_diseases) if gt_diseases else 0
    precision = len(hit_diseases) / len(retrieved_diseases_unique) if retrieved_diseases_unique else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    hit_rate = 1 if len(hit_diseases) > 0 else 0
    
    return EvaluationMetrics(recall, precision, f1, hit_rate)


def load_qa_dataset(filepath: str) -> List[Dict]:
    """加载问答数据集"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_evaluation():
    """运行7种方案的评估"""
    print("=" * 80)
    print("小麦病害诊断系统 - 7种检索方案对比评估（贝叶斯优化权重）")
    print("=" * 80)
    
    dataset_path = os.path.join(PROJECT_ROOT, "data", "evaluation", "qa_dataset_700.json")
    
    print(f"\n[1] 加载问答数据集: {dataset_path}")
    qa_data = load_qa_dataset(dataset_path)
    print(f"    共加载 {len(qa_data)} 个问答对")
    
    optimization_results_path = os.path.join(PROJECT_ROOT, "data", "evaluation", "bayesian_optimization_results.json")
    optimized_weights = None
    if os.path.exists(optimization_results_path):
        with open(optimization_results_path, 'r', encoding='utf-8') as f:
            optimization_results = json.load(f)
            optimized_weights = optimization_results['best_weights']
        print(f"\n[2] 加载贝叶斯优化权重:")
        print(f"    kg={optimized_weights['kg']:.3f}, dense={optimized_weights['dense']:.3f}, bm25={optimized_weights['bm25']:.3f}")
    else:
        print(f"\n[2] 未找到贝叶斯优化结果，使用等权配置")
    
    all_modules = ["kg", "dense", "bm25"]
    module_names = {"kg": "知识图谱", "dense": "向量检索", "bm25": "BM25"}
    
    schemes = []
    for r in range(1, len(all_modules) + 1):
        for combo in combinations(all_modules, r):
            schemes.append(set(combo))
    
    print(f"\n[3] 测试方案: 共 {len(schemes)} 种")
    for i, scheme in enumerate(schemes, 1):
        names = [module_names[m] for m in scheme]
        print(f"    方案{i}: {' + '.join(names)}")
    
    results: List[SchemeResult] = []
    
    print(f"\n[4] 开始评估...")
    
    for scheme_idx, enabled_modules in enumerate(schemes, 1):
        scheme_name = " + ".join([module_names[m] for m in enabled_modules])
        print(f"\n{'='*60}")
        print(f"评估方案 {scheme_idx}/7: {scheme_name}")
        print(f"{'='*60}")
        
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
        
        for i, item in enumerate(qa_data):
            query = item["question"]
            ground_truth = set(item["ground_truth_docs"])
            
            retrieved = retriever.retrieve(query, top_k=5)
            
            metrics = calculate_metrics(retrieved, ground_truth)
            recall_list.append(metrics.recall)
            precision_list.append(metrics.precision)
            f1_list.append(metrics.f1)
            hit_rate_list.append(metrics.hit_rate)
            
            if (i + 1) % 100 == 0:
                print(f"    进度: {i+1}/{len(qa_data)}")
        
        elapsed = time.time() - start_time
        
        retriever.close()
        
        total = len(qa_data)
        avg_recall = sum(recall_list) / total
        avg_precision = sum(precision_list) / total
        avg_f1 = sum(f1_list) / total
        avg_hit_rate = sum(hit_rate_list) / total
        
        result = SchemeResult(
            scheme_name=scheme_name,
            modules=list(enabled_modules),
            weights=scheme_weights if scheme_weights else {m: 1.0 for m in enabled_modules},
            total_queries=total,
            avg_recall=avg_recall,
            avg_precision=avg_precision,
            avg_f1=avg_f1,
            avg_hit_rate=avg_hit_rate,
            time_elapsed=elapsed
        )
        results.append(result)
        
        print(f"\n    结果:")
        print(f"    - 召回率: {avg_recall:.4f} ({avg_recall*100:.2f}%)")
        print(f"    - 精确率: {avg_precision:.4f} ({avg_precision*100:.2f}%)")
        print(f"    - F1分数: {avg_f1:.4f} ({avg_f1*100:.2f}%)")
        print(f"    - 命中率: {avg_hit_rate:.4f} ({avg_hit_rate*100:.2f}%)")
        print(f"    - 耗时: {elapsed:.2f}秒")
    
    print("\n" + "=" * 80)
    print("评估结果汇总")
    print("=" * 80)
    
    print(f"\n{'检索方案':<25} | {'召回率':<10} | {'精确率':<10} | {'F1分数':<10} | {'命中率':<10}")
    print("-" * 80)
    
    for result in results:
        print(f"{result.scheme_name:<25} | {result.avg_recall:<10.4f} | {result.avg_precision:<10.4f} | {result.avg_f1:<10.4f} | {result.avg_hit_rate:<10.4f}")
    
    print("-" * 80)
    
    output_path = os.path.join(PROJECT_ROOT, "data", "evaluation", "evaluation_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    output_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_queries": len(qa_data),
        "results": [asdict(r) for r in results]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_path}")
    
    return results


if __name__ == "__main__":
    run_evaluation()

# -*- coding: utf-8 -*-
"""
RAG检索评估指标
计算召回率、精确率、F1分数、命中率等指标
"""

from dataclasses import dataclass
from typing import List, Set


@dataclass
class RetrievalMetrics:
    """检索指标数据类"""
    recall: float
    precision: float
    f1: float
    hit_rate: float
    
    def to_dict(self):
        return {
            'recall': self.recall,
            'precision': self.precision,
            'f1': self.f1,
            'hit_rate': self.hit_rate
        }


def calculate_metrics(retrieved_docs: List[str], ground_truth: Set[str], k: int = 5) -> RetrievalMetrics:
    """
    计算检索指标
    
    Args:
        retrieved_docs: 检索到的文档列表
        ground_truth: 真实相关文档集合
        k: Top-K值
        
    Returns:
        RetrievalMetrics对象
    """
    retrieved_set = set(retrieved_docs[:k])
    
    if not ground_truth:
        return RetrievalMetrics(recall=0.0, precision=0.0, f1=0.0, hit_rate=0.0)
    
    true_positives = len(retrieved_set & ground_truth)
    
    recall = true_positives / len(ground_truth) if ground_truth else 0.0
    
    precision = true_positives / len(retrieved_set) if retrieved_set else 0.0
    
    if recall + precision > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0
    
    hit_rate = 1.0 if true_positives > 0 else 0.0
    
    return RetrievalMetrics(
        recall=recall,
        precision=precision,
        f1=f1,
        hit_rate=hit_rate
    )


def calculate_mrr(retrieved_docs: List[str], ground_truth: Set[str]) -> float:
    """
    计算MRR (Mean Reciprocal Rank)
    
    Args:
        retrieved_docs: 检索到的文档列表
        ground_truth: 真实相关文档集合
        
    Returns:
        MRR值
    """
    for i, doc in enumerate(retrieved_docs, 1):
        if doc in ground_truth:
            return 1.0 / i
    return 0.0


def calculate_ndcg(retrieved_docs: List[str], ground_truth: Set[str], k: int = 5) -> float:
    """
    计算NDCG (Normalized Discounted Cumulative Gain)
    
    Args:
        retrieved_docs: 检索到的文档列表
        ground_truth: 真实相关文档集合
        k: Top-K值
        
    Returns:
        NDCG值
    """
    import math
    
    dcg = 0.0
    for i, doc in enumerate(retrieved_docs[:k], 1):
        if doc in ground_truth:
            dcg += 1.0 / math.log2(i + 1)
    
    ideal_dcg = 0.0
    for i in range(min(len(ground_truth), k)):
        ideal_dcg += 1.0 / math.log2(i + 2)
    
    if ideal_dcg == 0:
        return 0.0
    
    return dcg / ideal_dcg


if __name__ == "__main__":
    retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
    ground_truth = {"doc1", "doc3", "doc6"}
    
    metrics = calculate_metrics(retrieved, ground_truth)
    print(f"召回率: {metrics.recall:.2%}")
    print(f"精确率: {metrics.precision:.2%}")
    print(f"F1分数: {metrics.f1:.2%}")
    print(f"命中率: {metrics.hit_rate:.2%}")
    
    mrr = calculate_mrr(retrieved, ground_truth)
    print(f"MRR: {mrr:.2f}")
    
    ndcg = calculate_ndcg(retrieved, ground_truth)
    print(f"NDCG: {ndcg:.2f}")

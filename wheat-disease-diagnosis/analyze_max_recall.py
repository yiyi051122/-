# -*- coding: utf-8 -*-
"""分析qa_dataset中每个问题的病害分布"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.evaluation.evaluate_7_schemes import extract_disease_name

# 加载qa_dataset
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/evaluation/qa_dataset_700.json'), 'r', encoding='utf-8') as f:
    qa_data = json.load(f)

# 统计每个问题的病害
from collections import Counter
disease_counter = Counter()

for item in qa_data:
    for doc in item['ground_truth_docs']:
        disease = extract_disease_name(doc)
        disease_counter[disease] += 1

print("qa_dataset中各病害的问题数量:")
for disease, count in disease_counter.most_common(20):
    print(f"  - {disease}: {count}个问题")

print(f"\n总共有 {len(disease_counter)} 种不同的病害")

# 检查Neo4j中的病害
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
with driver.session() as session:
    result = session.run("MATCH (d:Disease) RETURN d.name as name")
    neo4j_diseases = set(r['name'] for r in result)
driver.close()

print(f"\nNeo4j中有 {len(neo4j_diseases)} 种病害")

# 计算理论最大召回率
qa_diseases = set(disease_counter.keys())
matched_diseases = 0
total_questions = len(qa_data)

from src.evaluation.evaluate_7_schemes import fuzzy_match_disease

matched_questions = 0
for item in qa_data:
    for doc in item['ground_truth_docs']:
        disease = extract_disease_name(doc)
        for neo4j_disease in neo4j_diseases:
            neo4j_short = neo4j_disease.replace("小麦", "")
            if fuzzy_match_disease(disease, neo4j_short, threshold=0.6):
                matched_questions += 1
                break

print(f"\n能在Neo4j中找到对应病害的问题数: {matched_questions}/{total_questions}")
print(f"理论最大召回率: {matched_questions/total_questions*100:.2f}%")

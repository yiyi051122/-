# -*- coding: utf-8 -*-
"""分析qa_dataset中的病害分布"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import KNOWLEDGE_BASE_DIR

# 加载qa_dataset
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/evaluation/qa_dataset_700.json'), 'r', encoding='utf-8') as f:
    qa_data = json.load(f)

# 统计ground_truth_docs中的病害
all_docs = set()
for item in qa_data:
    for doc in item['ground_truth_docs']:
        all_docs.add(doc)

print(f"qa_dataset中涉及的文档数量: {len(all_docs)}")
print(f"\n文档列表（前20个）:")
for doc in sorted(all_docs)[:20]:
    print(f"  - {doc}")

# 检查这些文档是否存在于知识库中
kb_files = set(os.listdir(KNOWLEDGE_BASE_DIR))
missing_docs = all_docs - kb_files
print(f"\n知识库中缺失的文档数量: {len(missing_docs)}")
if missing_docs:
    print("缺失的文档:")
    for doc in sorted(missing_docs)[:10]:
        print(f"  - {doc}")

# 检查知识库中多余的文档
extra_docs = kb_files - all_docs
print(f"\n知识库中多余的文档数量: {len(extra_docs)}")

# 分析病害名称
from src.evaluation.evaluate_7_schemes import extract_disease_name

qa_diseases = set()
for doc in all_docs:
    disease = extract_disease_name(doc)
    qa_diseases.add(disease)

print(f"\nqa_dataset涉及的病害数量: {len(qa_diseases)}")
print("病害列表:")
for d in sorted(qa_diseases):
    print(f"  - {d}")

# 检查Neo4j中的病害节点
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
with driver.session() as session:
    result = session.run("MATCH (d:Disease) RETURN d.name as name")
    neo4j_diseases = set(r['name'] for r in result)
driver.close()

print(f"\nNeo4j中的病害数量: {len(neo4j_diseases)}")

# 检查qa_dataset中的病害是否都在Neo4j中
from src.evaluation.evaluate_7_schemes import fuzzy_match_disease

unmatched = []
for qa_disease in qa_diseases:
    found = False
    for neo4j_disease in neo4j_diseases:
        neo4j_short = neo4j_disease.replace("小麦", "")
        if fuzzy_match_disease(qa_disease, neo4j_short, threshold=0.6):
            found = True
            break
    if not found:
        unmatched.append(qa_disease)

print(f"\nqa_dataset中无法匹配到Neo4j的病害数量: {len(unmatched)}")
if unmatched:
    print("无法匹配的病害:")
    for d in sorted(unmatched):
        print(f"  - {d}")

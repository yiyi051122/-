# -*- coding: utf-8 -*-
"""诊断脚本 - 检查知识图谱检索问题"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, KNOWLEDGE_BASE_DIR
from src.evaluation.evaluate_7_schemes import extract_disease_name, fuzzy_match_disease

print("=" * 60)
print("诊断：知识图谱检索问题")
print("=" * 60)

# 1. 检查Neo4j中的病害节点
print("\n[1] Neo4j中的病害节点:")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
with driver.session() as session:
    result = session.run("MATCH (d:Disease) RETURN d.name as name ORDER BY name")
    diseases = [r['name'] for r in result]
    print(f"    病害节点数量: {len(diseases)}")
    for d in diseases[:10]:
        print(f"    - {d}")
    if len(diseases) > 10:
        print(f"    ... 还有 {len(diseases) - 10} 个")

# 2. 检查知识库文件
print("\n[2] 知识库文件:")
files = sorted([f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith('.txt')])
print(f"    文件数量: {len(files)}")
for f in files[:10]:
    print(f"    - {f}")
if len(files) > 10:
    print(f"    ... 还有 {len(files) - 10} 个")

# 3. 检查病害名称到文件的映射
print("\n[3] 病害名称到文件的映射:")
disease_file_map = {}
for disease_name in diseases:
    disease_short = disease_name.replace("小麦", "")
    matched_files = []
    for filename in files:
        file_disease = extract_disease_name(filename)
        if fuzzy_match_disease(disease_short, file_disease, threshold=0.6):
            matched_files.append(filename)
    disease_file_map[disease_name] = matched_files

# 统计映射情况
mapped_count = sum(1 for v in disease_file_map.values() if v)
unmapped = [k for k, v in disease_file_map.items() if not v]
print(f"    有映射的病害: {mapped_count}/{len(diseases)}")
print(f"    无映射的病害: {len(unmapped)}")
if unmapped:
    print("    无映射的病害列表:")
    for d in unmapped[:10]:
        print(f"    - {d}")

# 4. 检查关系类型
print("\n[4] Neo4j中的关系类型:")
with driver.session() as session:
    result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC")
    for r in result:
        print(f"    - {r['type']}: {r['count']} 条")

# 5. 测试一个查询
print("\n[5] 测试查询: '小麦白秆病用什么药剂防治？'")
import jieba
query = "小麦白秆病用什么药剂防治？"
stop_words = {'什么', '怎么', '如何', '哪些', '主要', '症状', '方法', '防治', 
             '措施', '特点', '原因', '条件', '时期', '阶段', '进行', '可以',
             '应该', '需要', '通过', '使用', '采用', '实施', '发生', '出现',
             '小麦', '药剂', '发病', '用药', '治疗', '诊断', '识别', '特点',
             '特征', '表现', '情况', '问题', '效果', '作用', '影响', '造成',
             '引起', '导致', '危害', '损失', '产量', '品质', '品种', '栽培'}
keywords = [w for w in jieba.cut(query) if len(w) > 1 and w not in stop_words]
print(f"    关键词: {keywords}")

disease_keywords = []
for kw in keywords:
    if any(x in kw for x in ['病', '锈', '霉', '腐', '枯', '粉', '矮', '黑', '斑']):
        disease_keywords.append(kw)
print(f"    病害关键词: {disease_keywords}")

# 病害名称匹配
found_diseases = {}
for keyword in disease_keywords:
    with driver.session() as session:
        cypher = "MATCH (d:Disease) WHERE d.name CONTAINS $keyword RETURN d.name as disease LIMIT 5"
        result = session.run(cypher, keyword=keyword)
        for record in result:
            disease_name = record['disease']
            if disease_name not in found_diseases:
                found_diseases[disease_name] = 10
                print(f"    找到病害: {disease_name} (分数: 10)")

# 映射到文件
print("\n[6] 病害映射到文件:")
for disease_name, score in sorted(found_diseases.items(), key=lambda x: -x[1]):
    matched_files = disease_file_map.get(disease_name, [])
    print(f"    {disease_name} -> {len(matched_files)} 个文件")
    for f in matched_files[:3]:
        print(f"        - {f}")

driver.close()
print("\n" + "=" * 60)

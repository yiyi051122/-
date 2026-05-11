# -*- coding: utf-8 -*-
"""检查Neo4j中的白秆病节点"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("检查Neo4j中是否有'白秆病'相关的病害节点:")
with driver.session() as session:
    # 搜索包含"白秆"的病害
    result = session.run("MATCH (d:Disease) WHERE d.name CONTAINS '白秆' RETURN d.name as name")
    diseases = [r['name'] for r in result]
    print(f"包含'白秆'的病害: {diseases}")
    
    # 搜索包含"秆"的病害
    result = session.run("MATCH (d:Disease) WHERE d.name CONTAINS '秆' RETURN d.name as name")
    diseases = [r['name'] for r in result]
    print(f"包含'秆'的病害: {diseases}")

# 测试Cypher查询
print("\n测试Cypher查询:")
test_keywords = ['白秆', '白秆病', '病用']
for kw in test_keywords:
    with driver.session() as session:
        result = session.run("MATCH (d:Disease) WHERE d.name CONTAINS $keyword RETURN d.name as disease LIMIT 5", keyword=kw)
        found = [r['disease'] for r in result]
        print(f"  关键词 '{kw}' -> {found}")

driver.close()

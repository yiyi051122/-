# -*- coding: utf-8 -*-
"""
小麦病害知识图谱检索模块
提供基于Neo4j的知识图谱查询功能
"""

from neo4j import GraphDatabase
import sys
sys.path.append('..')
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class WheatDiseaseKG:
    """小麦病害知识图谱检索类"""
    
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def extract_keywords(self, user_input):
        """从用户输入中提取关键词"""
        stop_words = ["小麦", "的", "出现", "有", "叶片", "麦穗", "茎基部", "植株", 
                      "易", "导致", "和", "等", "是", "什么", "怎么", "如何", "请", "问"]
        keywords = []
        for word in user_input.split():
            if word not in stop_words and len(word) > 1:
                keywords.append(word)
        
        for char in user_input:
            if char not in stop_words and len(char.strip()) > 0:
                keywords.append(char)
        
        return list(set(keywords))
    
    def retrieve_by_symptom(self, keywords):
        """根据症状关键词检索病害信息"""
        with self.driver.session() as session:
            cypher_query = """
            MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom),
                  (d)-[:HAS_CONTROL]->(ctrl:Control),
                  (d)-[:USES_PESTICIDE]->(p:Pesticide),
                  (d)-[:OCCURS_AT]->(st:Stage),
                  (d)-[:AFFECTS_PART]->(pt:Part)
            WHERE any(keyword IN $keywords WHERE s.desc CONTAINS keyword)
            RETURN d.name AS disease, 
                   s.desc AS symptom, 
                   ctrl.desc AS control, 
                   collect(DISTINCT p.name) AS pesticides,
                   st.name AS stage,
                   pt.name AS part
            """
            result = session.run(cypher_query, keywords=keywords)
            return result.data()
    
    def retrieve_all_diseases(self):
        """检索所有病害信息"""
        with self.driver.session() as session:
            cypher_query = """
            MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom),
                  (d)-[:HAS_CONTROL]->(ctrl:Control),
                  (d)-[:USES_PESTICIDE]->(p:Pesticide),
                  (d)-[:OCCURS_AT]->(st:Stage),
                  (d)-[:AFFECTS_PART]->(pt:Part)
            RETURN d.name AS disease, 
                   s.desc AS symptom, 
                   ctrl.desc AS control, 
                   collect(DISTINCT p.name) AS pesticides,
                   st.name AS stage,
                   pt.name AS part
            """
            result = session.run(cypher_query)
            return result.data()
    
    def retrieve_by_disease_name(self, disease_name):
        """根据病害名称检索详细信息"""
        with self.driver.session() as session:
            cypher_query = """
            MATCH (d:Disease {name: $disease_name})
            OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
            OPTIONAL MATCH (d)-[:HAS_CONTROL]->(ctrl:Control)
            OPTIONAL MATCH (d)-[:USES_PESTICIDE]->(p:Pesticide)
            OPTIONAL MATCH (d)-[:OCCURS_AT]->(st:Stage)
            OPTIONAL MATCH (d)-[:AFFECTS_PART]->(pt:Part)
            RETURN d.name AS disease, 
                   s.desc AS symptom, 
                   ctrl.desc AS control, 
                   collect(DISTINCT p.name) AS pesticides,
                   st.name AS stage,
                   pt.name AS part
            """
            result = session.run(cypher_query, disease_name=disease_name)
            return result.single()
    
    def format_retrieved_context(self, records):
        """格式化检索结果为上下文文本"""
        if not records:
            return "未找到匹配的病害信息。"
        
        context_parts = []
        for record in records:
            pesticides_str = "、".join(record['pesticides']) if record['pesticides'] else "无"
            context = f"""
【病害名称】：{record['disease']}
【典型症状】：{record['symptom']}
【发病时期】：{record['stage']}
【危害部位】：{record['part']}
【防治方法】：{record['control']}
【适用药剂】：{pesticides_str}
"""
            context_parts.append(context)
        
        return "\n".join(context_parts)
    
    def retrieve(self, user_input):
        """主检索方法：根据用户输入检索知识图谱"""
        keywords = self.extract_keywords(user_input)
        
        records = self.retrieve_by_symptom(keywords)
        
        if not records:
            records = self.retrieve_all_diseases()
        
        return self.format_retrieved_context(records)
    
    def get_disease_list(self):
        """获取所有病害名称列表"""
        with self.driver.session() as session:
            result = session.run("MATCH (d:Disease) RETURN d.name AS name ORDER BY d.name")
            return [record['name'] for record in result]
    
    def get_statistics(self):
        """获取知识图谱统计信息"""
        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()['count']
            relation_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()['count']
            return {"nodes": node_count, "relations": relation_count}


def retrieve_from_kg(user_input):
    """便捷函数：从知识图谱检索"""
    kg = WheatDiseaseKG()
    try:
        return kg.retrieve(user_input)
    finally:
        kg.close()


if __name__ == "__main__":
    kg = WheatDiseaseKG()
    try:
        print("病害列表:", kg.get_disease_list())
        print("\n统计信息:", kg.get_statistics())
        
        test_input = "叶片出现黄色孢子堆"
        print(f"\n测试检索: {test_input}")
        print(kg.retrieve(test_input))
    finally:
        kg.close()

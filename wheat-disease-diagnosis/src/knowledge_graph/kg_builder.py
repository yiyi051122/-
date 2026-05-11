# -*- coding: utf-8 -*-
"""
小麦病害知识图谱构建器
用于在Neo4j中创建知识图谱
实体类型：Disease, Symptom, Stage, Cause, Control, Pesticide, Part
关系类型：HAS_SYMPTOM, OCCURS_AT, CAUSED_BY, HAS_CONTROL, USES_PESTICIDE, AFFECTS_PART
"""

from neo4j import GraphDatabase
from src.knowledge_graph.disease_data import WHEAT_DISEASE_DATA, ENTITY_TYPES, RELATION_TYPES
import sys
sys.path.append('..')
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """清空数据库"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("数据库已清空")
    
    def create_constraints(self):
        """创建唯一性约束"""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Symptom) REQUIRE s.desc IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (st:Stage) REQUIRE st.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Cause) REQUIRE c.desc IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (ctrl:Control) REQUIRE ctrl.desc IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Pesticide) REQUIRE p.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (pt:Part) REQUIRE pt.name IS UNIQUE"
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"约束创建警告: {e}")
        print("约束创建完成")
    
    def create_disease_node(self, tx, disease_name):
        """创建病害节点"""
        tx.run("MERGE (d:Disease {name: $name})", name=disease_name)
    
    def create_symptom_node(self, tx, symptom_desc):
        """创建症状节点"""
        tx.run("MERGE (s:Symptom {desc: $desc})", desc=symptom_desc)
    
    def create_stage_node(self, tx, stage_name):
        """创建生育期节点"""
        tx.run("MERGE (st:Stage {name: $name})", name=stage_name)
    
    def create_cause_node(self, tx, cause_desc):
        """创建病因节点"""
        tx.run("MERGE (c:Cause {desc: $desc})", desc=cause_desc)
    
    def create_control_node(self, tx, control_desc):
        """创建防治方法节点"""
        tx.run("MERGE (ctrl:Control {desc: $desc})", desc=control_desc)
    
    def create_pesticide_node(self, tx, pesticide_name):
        """创建药剂节点"""
        tx.run("MERGE (p:Pesticide {name: $name})", name=pesticide_name)
    
    def create_part_node(self, tx, part_name):
        """创建危害部位节点"""
        tx.run("MERGE (pt:Part {name: $name})", name=part_name)
    
    def create_relation(self, tx, disease_name, relation_type, target_value, target_type):
        """创建关系"""
        if target_type == "Symptom":
            query = f"""
            MATCH (d:Disease {{name: $disease}})
            MATCH (s:Symptom {{desc: $target}})
            MERGE (d)-[:{relation_type}]->(s)
            """
        elif target_type == "Stage":
            query = f"""
            MATCH (d:Disease {{name: $disease}})
            MATCH (st:Stage {{name: $target}})
            MERGE (d)-[:{relation_type}]->(st)
            """
        elif target_type == "Cause":
            query = f"""
            MATCH (d:Disease {{name: $disease}})
            MATCH (c:Cause {{desc: $target}})
            MERGE (d)-[:{relation_type}]->(c)
            """
        elif target_type == "Control":
            query = f"""
            MATCH (d:Disease {{name: $disease}})
            MATCH (ctrl:Control {{desc: $target}})
            MERGE (d)-[:{relation_type}]->(ctrl)
            """
        elif target_type == "Pesticide":
            query = f"""
            MATCH (d:Disease {{name: $disease}})
            MATCH (p:Pesticide {{name: $target}})
            MERGE (d)-[:{relation_type}]->(p)
            """
        elif target_type == "Part":
            query = f"""
            MATCH (d:Disease {{name: $disease}})
            MATCH (pt:Part {{name: $target}})
            MERGE (d)-[:{relation_type}]->(pt)
            """
        else:
            return
        
        tx.run(query, disease=disease_name, target=target_value)
    
    def build_knowledge_graph(self):
        """构建完整知识图谱"""
        print("开始构建知识图谱...")
        
        with self.driver.session() as session:
            for disease_name, disease_info in WHEAT_DISEASE_DATA.items():
                print(f"处理病害: {disease_name}")
                
                session.execute_write(self.create_disease_node, disease_name)
                
                session.execute_write(self.create_symptom_node, disease_info["symptom"])
                session.execute_write(self.create_relation, disease_name, "HAS_SYMPTOM", 
                                     disease_info["symptom"], "Symptom")
                
                session.execute_write(self.create_stage_node, disease_info["stage"])
                session.execute_write(self.create_relation, disease_name, "OCCURS_AT",
                                     disease_info["stage"], "Stage")
                
                session.execute_write(self.create_cause_node, disease_info["cause"])
                session.execute_write(self.create_relation, disease_name, "CAUSED_BY",
                                     disease_info["cause"], "Cause")
                
                session.execute_write(self.create_control_node, disease_info["control"])
                session.execute_write(self.create_relation, disease_name, "HAS_CONTROL",
                                     disease_info["control"], "Control")
                
                pesticides = [p.strip() for p in disease_info["pesticide"].split("、")]
                for pesticide in pesticides:
                    session.execute_write(self.create_pesticide_node, pesticide)
                    session.execute_write(self.create_relation, disease_name, "USES_PESTICIDE",
                                         pesticide, "Pesticide")
                
                parts = [p.strip() for p in disease_info["part"].split("、")]
                for part in parts:
                    session.execute_write(self.create_part_node, part)
                    session.execute_write(self.create_relation, disease_name, "AFFECTS_PART",
                                         part, "Part")
        
        print("知识图谱构建完成!")
        self.print_statistics()
    
    def print_statistics(self):
        """打印统计信息"""
        with self.driver.session() as session:
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
            print("\n=== 知识图谱统计 ===")
            for record in result:
                print(f"{record['label']}: {record['count']} 个节点")
            
            result = session.run("MATCH ()-[r]->() RETURN type(r) as relation, count(r) as count")
            print("\n=== 关系统计 ===")
            for record in result:
                print(f"{record['relation']}: {record['count']} 条")


def build_knowledge_graph(clear_existing: bool = True):
    """
    构建知识图谱的便捷函数
    
    Args:
        clear_existing: 是否清空现有数据，默认为True
    """
    builder = KnowledgeGraphBuilder()
    try:
        if clear_existing:
            builder.clear_database()
        builder.create_constraints()
        builder.build_knowledge_graph()
    finally:
        builder.close()


if __name__ == "__main__":
    build_knowledge_graph()

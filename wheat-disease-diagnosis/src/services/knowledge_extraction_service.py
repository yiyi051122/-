# -*- coding: utf-8 -*-
"""
知识抽取服务模块
提供知识抽取、存储和查询功能
"""

import sys
import os
from datetime import datetime
sys.path.insert(0, '.')

from typing import List, Dict, Optional
from neo4j import GraphDatabase

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, KNOWLEDGE_BASE_DIR
from src.knowledge_extraction.entity_extractor import EntityExtractor, Entity
from src.knowledge_extraction.relation_extractor import RelationExtractor, Relation
from src.knowledge_extraction.kg_importer import KGImporter


class KnowledgeExtractionService:
    """知识抽取服务类"""
    
    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def extract_knowledge(self, text: str) -> Dict:
        """
        从文本中抽取知识
        
        Args:
            text: 输入文本
            
        Returns:
            抽取结果字典，包含实体和关系
        """
        entities = self.entity_extractor.extract(text)
        entity_list = [e.to_dict() for e in entities]
        
        relations = self.relation_extractor.extract(text, entity_list)
        relation_list = [r.to_dict() for r in relations]
        
        return {
            'text': text,
            'entities': entity_list,
            'relations': relation_list,
            'entity_count': len(entity_list),
            'relation_count': len(relation_list),
            'entity_stats': self.entity_extractor.get_statistics(),
            'relation_stats': self.relation_extractor.get_statistics()
        }
    
    def save_to_neo4j(self, entities: List[Dict], relations: List[Dict], original_text: str = None) -> Dict:
        """
        将抽取的知识保存到Neo4j，并自动保存到knowledge_base
        
        Args:
            entities: 实体列表
            relations: 关系列表
            original_text: 原始文本（用于保存到knowledge_base）
            
        Returns:
            保存结果
        """
        with KGImporter() as importer:
            importer.create_constraints()
            result = importer.import_from_extraction(entities, relations)
        
        if original_text and entities:
            self._save_to_knowledge_base(original_text, entities, relations)
        
        return result
    
    def _save_to_knowledge_base(self, text: str, entities: List[Dict], relations: List[Dict]):
        """
        保存抽取结果到knowledge_base文件夹
        
        Args:
            text: 原始文本
            entities: 实体列表
            relations: 关系列表
        """
        disease_entities = [e for e in entities if e.get('type') == 'Disease']
        
        if not disease_entities:
            return
        
        disease_name = disease_entities[0].get('name', 'unknown')
        safe_name = disease_name.replace(' ', '_').replace('/', '_')
        
        os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)
        
        file_path = os.path.join(KNOWLEDGE_BASE_DIR, f"{safe_name}.txt")
        
        content_lines = [f"# {disease_name}", ""]
        
        content_lines.append("## 原始文本")
        content_lines.append(text)
        content_lines.append("")
        
        content_lines.append("## 抽取的实体")
        for entity in entities:
            content_lines.append(f"- [{entity['type']}] {entity['name']}")
        content_lines.append("")
        
        content_lines.append("## 抽取的关系")
        for relation in relations:
            content_lines.append(f"- {relation['head']} --[{relation['relation']}]--> {relation['tail']}")
        content_lines.append("")
        
        content_lines.append(f"## 抽取时间")
        content_lines.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_lines))
        
        print(f"知识已保存到: {file_path}")
    
    def extract_and_save(self, text: str) -> Dict:
        """
        抽取知识并保存到Neo4j
        
        Args:
            text: 输入文本
            
        Returns:
            完整结果，包含抽取和保存信息
        """
        extraction_result = self.extract_knowledge(text)
        
        save_result = self.save_to_neo4j(
            extraction_result['entities'],
            extraction_result['relations']
        )
        
        return {
            'extraction': extraction_result,
            'save': save_result,
            'success': len(save_result.get('errors', [])) == 0
        }
    
    def get_graph_data(self, limit: int = 100) -> Dict:
        """
        从Neo4j获取知识图谱数据用于前端展示
        
        Args:
            limit: 最大返回节点数
            
        Returns:
            图谱数据，包含nodes和edges
        """
        nodes = []
        edges = []
        node_map = {}
        
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (source)-[r]->(target)
                RETURN id(source) as source_id, 
                       labels(source)[0] as source_type,
                       source.name as source_name,
                       source.desc as source_desc,
                       id(target) as target_id, 
                       labels(target)[0] as target_type,
                       target.name as target_name,
                       target.desc as target_desc,
                       type(r) as relation
                LIMIT {limit * 3}
            """)
            
            for record in result:
                source_id = int(record['source_id'])
                target_id = int(record['target_id'])
                
                if source_id not in node_map:
                    source_name = record['source_name'] or record['source_desc'] or f"Node_{source_id}"
                    node_map[source_id] = {
                        'id': source_id,
                        'label': str(source_name),
                        'type': record['source_type'],
                        'title': f"{record['source_type']}: {source_name}"
                    }
                
                if target_id not in node_map:
                    target_name = record['target_name'] or record['target_desc'] or f"Node_{target_id}"
                    node_map[target_id] = {
                        'id': target_id,
                        'label': str(target_name),
                        'type': record['target_type'],
                        'title': f"{record['target_type']}: {target_name}"
                    }
                
                edges.append({
                    'id': len(edges),
                    'from': source_id,
                    'to': target_id,
                    'label': record['relation'],
                    'relation': record['relation']
                })
            
            if len(node_map) < limit:
                result = session.run(f"""
                    MATCH (n)
                    WHERE NOT (n)-[]-()
                    RETURN id(n) as node_id,
                           labels(n)[0] as node_type,
                           n.name as node_name,
                           n.desc as node_desc
                    LIMIT {limit - len(node_map)}
                """)
                
                for record in result:
                    node_id = int(record['node_id'])
                    if node_id not in node_map:
                        node_name = record['node_name'] or record['node_desc'] or f"Node_{node_id}"
                        node_map[node_id] = {
                            'id': node_id,
                            'label': str(node_name),
                            'type': record['node_type'],
                            'title': f"{record['node_type']}: {node_name}"
                        }
            
            nodes = list(node_map.values())[:limit]
            node_ids = set(n['id'] for n in nodes)
            edges = [e for e in edges if e['from'] in node_ids and e['to'] in node_ids]
        
        return {
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }
    
    def get_statistics(self) -> Dict:
        """获取知识图谱统计信息"""
        with self.driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            
            label_result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            label_counts = {record['label']: record['count'] for record in label_result}
            
            rel_type_result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            rel_type_counts = {record['type']: record['count'] for record in rel_type_result}
            
            return {
                'total_nodes': node_count,
                'total_relations': rel_count,
                'nodes_by_type': label_counts,
                'relations_by_type': rel_type_counts
            }
    
    def clear_all_data(self) -> Dict:
        """清空所有数据"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        return {'success': True, 'message': '所有数据已清空'}
    
    def delete_isolated_nodes(self) -> Dict:
        """删除没有关系的孤立节点"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE NOT (n)--()
                RETURN count(n) as count
            """)
            count_before = result.single()['count']
            
            session.run("""
                MATCH (n)
                WHERE NOT (n)--()
                DELETE n
            """)
            
            return {
                'success': True, 
                'deleted_count': count_before,
                'message': f'已删除 {count_before} 个孤立节点'
            }
    
    def close(self):
        """关闭连接"""
        self.driver.close()


def test_service():
    """测试服务"""
    service = KnowledgeExtractionService()
    
    test_text = """
    小麦条锈病是小麦生产中最重要的病害之一。
    叶片出现鲜黄色疱状孢子堆，沿叶脉排列成行。
    适宜温度为10-15℃，相对湿度80%以上。
    防治方法：选用抗病品种，发病初期喷施三唑酮、丙环唑等药剂。
    """
    
    print("测试知识抽取...")
    result = service.extract_knowledge(test_text)
    print(f"实体数量: {result['entity_count']}")
    print(f"关系数量: {result['relation_count']}")
    
    print("\n实体列表:")
    for entity in result['entities']:
        print(f"  [{entity['type']}] {entity['name']}")
    
    print("\n关系列表:")
    for relation in result['relations']:
        print(f"  {relation['head']} --[{relation['relation']}]--> {relation['tail']}")
    
    print("\n图谱统计:")
    stats = service.get_statistics()
    print(f"节点总数: {stats['total_nodes']}")
    print(f"关系总数: {stats['total_relations']}")
    
    service.close()


if __name__ == "__main__":
    test_service()

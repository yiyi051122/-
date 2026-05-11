# -*- coding: utf-8 -*-
"""
Knowledge Graph Importer Module
Imports extracted entities and relations into Neo4j
"""

import sys
sys.path.insert(0, '.')

from typing import List, Dict
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class KGImporter:
    """Knowledge Graph Importer Class"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.stats = {'nodes_created': 0, 'relations_created': 0, 'errors': []}
    
    def close(self):
        self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def create_constraints(self):
        """Create uniqueness constraints"""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Part) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Pesticide) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Symptom) REQUIRE s.desc IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Control) REQUIRE c.desc IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Cause) REQUIRE c.desc IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (st:Stage) REQUIRE st.name IS UNIQUE",
        ]
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    pass
    
    def import_entities(self, entities: List[Dict]) -> int:
        """Import entities into Neo4j"""
        type_config = {
            'Disease': ('Disease', 'name'),
            'Part': ('Part', 'name'),
            'Pesticide': ('Pesticide', 'name'),
            'Symptom': ('Symptom', 'desc'),
            'Control': ('Control', 'desc'),
            'Cause': ('Cause', 'desc'),
            'Stage': ('Stage', 'name'),
        }
        
        nodes_created = 0
        with self.driver.session() as session:
            for entity in entities:
                entity_type = entity.get('type')
                entity_name = entity.get('name')
                
                if not entity_type or not entity_name:
                    continue
                
                label, prop_name = type_config.get(entity_type, ('Entity', 'name'))
                
                if label:
                    query = f"MERGE (n:{label} {{{prop_name}: $name}}) RETURN n"
                    try:
                        result = session.run(query, name=entity_name)
                        if result.single():
                            nodes_created += 1
                    except Exception as e:
                        self.stats['errors'].append(f"Error creating node {entity_name}: {e}")
        
        self.stats['nodes_created'] = nodes_created
        return nodes_created
    
    def import_relations(self, relations: List[Dict]) -> int:
        """Import relations into Neo4j"""
        type_config = {
            'Disease': ('Disease', 'name'),
            'Part': ('Part', 'name'),
            'Pesticide': ('Pesticide', 'name'),
            'Symptom': ('Symptom', 'desc'),
            'Control': ('Control', 'desc'),
            'Cause': ('Cause', 'desc'),
            'Stage': ('Stage', 'name'),
        }
        
        relations_created = 0
        with self.driver.session() as session:
            for relation in relations:
                head = relation.get('head')
                head_type = relation.get('head_type')
                rel_type = relation.get('relation')
                tail = relation.get('tail')
                tail_type = relation.get('tail_type')
                
                if not all([head, head_type, rel_type, tail, tail_type]):
                    continue
                
                head_label, head_prop = type_config.get(head_type, ('Entity', 'name'))
                tail_label, tail_prop = type_config.get(tail_type, ('Entity', 'name'))
                
                if not head_label or not tail_label:
                    continue
                
                query = f"""
                MATCH (h:{head_label} {{{head_prop}: $head}})
                MATCH (t:{tail_label} {{{tail_prop}: $tail}})
                MERGE (h)-[r:{rel_type}]->(t)
                RETURN r
                """
                
                try:
                    result = session.run(query, head=head, tail=tail)
                    if result.single():
                        relations_created += 1
                except Exception as e:
                    self.stats['errors'].append(f"Error creating relation {head}-{rel_type}->{tail}: {e}")
        
        self.stats['relations_created'] = relations_created
        return relations_created
    
    def import_from_extraction(self, entities: List[Dict], relations: List[Dict]) -> Dict:
        """Import from extraction results"""
        self.create_constraints()
        nodes = self.import_entities(entities)
        rels = self.import_relations(relations)
        
        return {
            'nodes_created': nodes,
            'relations_created': rels,
            'errors': self.stats['errors']
        }


if __name__ == "__main__":
    test_entities = [
        {'name': '小麦条锈病', 'type': 'Disease'},
        {'name': '叶片出现黄色孢子堆', 'type': 'Symptom'},
        {'name': '三唑酮', 'type': 'Pesticide'},
    ]
    
    test_relations = [
        {'head': '小麦条锈病', 'head_type': 'Disease', 'relation': 'HAS_SYMPTOM', 'tail': '叶片出现黄色孢子堆', 'tail_type': 'Symptom'},
        {'head': '小麦条锈病', 'head_type': 'Disease', 'relation': 'USES_PESTICIDE', 'tail': '三唑酮', 'tail_type': 'Pesticide'},
    ]
    
    with KGImporter() as importer:
        result = importer.import_from_extraction(test_entities, test_relations)
        print(f"Nodes created: {result['nodes_created']}")
        print(f"Relations created: {result['relations_created']}")

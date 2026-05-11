# -*- coding: utf-8 -*-
"""
Document Relation Extraction Pipeline
Complete pipeline for extracting entities and relations from documents
"""

import os
import sys
sys.path.insert(0, '.')

from typing import List, Dict, Optional
from dataclasses import dataclass

from src.knowledge_extraction.document_parser import DocumentParser
from src.knowledge_extraction.entity_extractor import EntityExtractor
from src.knowledge_extraction.relation_extractor import RelationExtractor
from src.knowledge_extraction.kg_importer import KGImporter


@dataclass
class ExtractionResult:
    """Extraction result data class"""
    file_name: str
    text_length: int
    entities: List[Dict]
    relations: List[Dict]
    entity_stats: Dict
    relation_stats: Dict


class ExtractionPipeline:
    """
    Complete Extraction Pipeline
    Orchestrates document parsing, entity extraction, relation extraction, and KG import
    """
    
    def __init__(self, import_to_kg: bool = True):
        """
        Initialize Extraction Pipeline
        
        Args:
            import_to_kg: Whether to automatically import to Neo4j
        """
        self.parser = DocumentParser()
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.kg_importer = KGImporter() if import_to_kg else None
        
        self.import_to_kg = import_to_kg
        self.results = []
    
    def process_document(self, file_path: str) -> ExtractionResult:
        """
        Process a single document
        
        Args:
            file_path: Path to the document
            
        Returns:
            ExtractionResult object
        """
        print(f"Processing: {file_path}")
        
        parse_result = self.parser.parse(file_path)
        text = parse_result['text']
        metadata = parse_result['metadata']
        
        entities = self.entity_extractor.extract(text)
        entity_list = [e.to_dict() for e in entities]
        
        relations = self.relation_extractor.extract(text, entity_list)
        relation_list = [r.to_dict() for r in relations]
        
        result = ExtractionResult(
            file_name=metadata['file_name'],
            text_length=metadata['text_length'],
            entities=entity_list,
            relations=relation_list,
            entity_stats=self.entity_extractor.get_statistics(),
            relation_stats=self.relation_extractor.get_statistics()
        )
        
        return result
    
    def process_directory(self, dir_path: str) -> List[ExtractionResult]:
        """
        Process all documents in a directory
        
        Args:
            dir_path: Path to the directory
            
        Returns:
            List of ExtractionResult objects
        """
        if not os.path.isdir(dir_path):
            raise NotADirectoryError(f"Not a directory: {dir_path}")
        
        self.results = []
        
        supported_extensions = ['.txt', '.pdf', '.docx', '.doc']
        
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_extensions:
                    file_path = os.path.join(root, file)
                    try:
                        result = self.process_document(file_path)
                        self.results.append(result)
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
        
        return self.results
    
    def import_to_neo4j(self, result: ExtractionResult = None) -> Dict:
        """
        Import extraction results to Neo4j
        
        Args:
            result: Single extraction result (uses all results if None)
            
        Returns:
            Import statistics
        """
        if not self.kg_importer:
            raise RuntimeError("KG importer not initialized")
        
        if not self.kg_importer.driver:
            self.kg_importer.connect()
        
        self.kg_importer.create_constraints()
        
        if result:
            return self.kg_importer.import_from_extraction(
                result.entities, result.relations
            )
        
        all_entities = []
        all_relations = []
        
        for r in self.results:
            all_entities.extend(r.entities)
            all_relations.extend(r.relations)
        
        return self.kg_importer.import_from_extraction(all_entities, all_relations)
    
    def get_combined_statistics(self) -> Dict:
        """Get combined statistics from all processed documents"""
        total_entities = 0
        total_relations = 0
        entity_by_type = {}
        relation_by_type = {}
        
        for result in self.results:
            total_entities += len(result.entities)
            total_relations += len(result.relations)
            
            for entity in result.entities:
                etype = entity.get('type', entity.get('entity_type'))
                if etype not in entity_by_type:
                    entity_by_type[etype] = 0
                entity_by_type[etype] += 1
            
            for relation in result.relations:
                rtype = relation.get('relation')
                if rtype not in relation_by_type:
                    relation_by_type[rtype] = 0
                relation_by_type[rtype] += 1
        
        return {
            'documents_processed': len(self.results),
            'total_entities': total_entities,
            'total_relations': total_relations,
            'entity_by_type': entity_by_type,
            'relation_by_type': relation_by_type
        }
    
    def close(self):
        """Close all connections"""
        if self.kg_importer:
            self.kg_importer.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def process_document(file_path: str, import_to_kg: bool = True) -> ExtractionResult:
    """
    Convenience function to process a single document
    
    Args:
        file_path: Path to the document
        import_to_kg: Whether to import to Neo4j
        
    Returns:
        ExtractionResult object
    """
    with ExtractionPipeline(import_to_kg=import_to_kg) as pipeline:
        result = pipeline.process_document(file_path)
        if import_to_kg:
            pipeline.import_to_neo4j(result)
        return result


def process_directory(dir_path: str, import_to_kg: bool = True) -> List[ExtractionResult]:
    """
    Convenience function to process all documents in a directory
    
    Args:
        dir_path: Path to the directory
        import_to_kg: Whether to import to Neo4j
        
    Returns:
        List of ExtractionResult objects
    """
    with ExtractionPipeline(import_to_kg=import_to_kg) as pipeline:
        results = pipeline.process_directory(dir_path)
        if import_to_kg:
            pipeline.import_to_neo4j()
        return results


if __name__ == "__main__":
    print("Starting pipeline...")
    import argparse
    
    print("Parsing arguments...")
    parser = argparse.ArgumentParser(description='Document Relation Extraction Pipeline')
    parser.add_argument('path', help='Path to document or directory')
    parser.add_argument('--no-import', action='store_true', help='Skip Neo4j import')
    
    args = parser.parse_args()
    print(f"Arguments parsed: path={args.path}, no_import={args.no_import}")
    
    import_to_kg = not args.no_import
    print(f"Import to KG: {import_to_kg}")
    
    if os.path.isfile(args.path):
        print(f"Processing file: {args.path}")
        result = process_document(args.path, import_to_kg)
        print(f"\n=== Extraction Result ===")
        print(f"File: {result.file_name}")
        print(f"Text length: {result.text_length}")
        print(f"Entities: {len(result.entities)}")
        print(f"Relations: {len(result.relations)}")
        
        if result.entities:
            print("\nSample entities:")
            for i, entity in enumerate(result.entities[:3]):
                print(f"  {i+1}. {entity.get('type')}: {entity.get('name')}")
        
        if result.relations:
            print("\nSample relations:")
            for i, relation in enumerate(result.relations[:3]):
                print(f"  {i+1}. {relation.get('head')} -[{relation.get('relation')}]-> {relation.get('tail')}")
        
    elif os.path.isdir(args.path):
        print(f"Processing directory: {args.path}")
        results = process_directory(args.path, import_to_kg)
        print(f"\n=== Extraction Results ===")
        print(f"Documents processed: {len(results)}")
        
        total_entities = sum(len(r.entities) for r in results)
        total_relations = sum(len(r.relations) for r in results)
        print(f"Total entities: {total_entities}")
        print(f"Total relations: {total_relations}")
    else:
        print(f"Path not found: {args.path}")
    
    print("Pipeline completed.")

# -*- coding: utf-8 -*-
"""
知识提取模块
"""

from src.knowledge_extraction.entity_extractor import EntityExtractor, Entity, extract_entities
from src.knowledge_extraction.relation_extractor import RelationExtractor, Relation, extract_relations
from src.knowledge_extraction.document_parser import DocumentParser
from src.knowledge_extraction.kg_importer import KGImporter
from src.knowledge_extraction.pipeline import ExtractionPipeline, process_document, process_directory

__all__ = [
    'EntityExtractor',
    'Entity',
    'extract_entities',
    'RelationExtractor',
    'Relation',
    'extract_relations',
    'DocumentParser',
    'KGImporter',
    'ExtractionPipeline',
    'process_document',
    'process_directory'
]

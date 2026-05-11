# -*- coding: utf-8 -*-
"""
Entity Extractor Module - 优化版
5类核心实体：病害、症状、生育期、病因、防治方法
支持从混杂文本中准确抽取相关实体
"""

import re
from typing import List, Dict, Set
from dataclasses import dataclass

from .extraction_rules import (
    TARGET_DISEASES,
    DISEASE_ALIASES,
    VALID_PARTS,
    VALID_STAGES,
    PESTICIDE_KEYWORDS,
    SYMPTOM_KEYWORDS,
    SYMPTOM_PATTERNS,
    CAUSE_KEYWORDS,
    CAUSE_PATTERNS,
    CONTROL_KEYWORDS,
    CONTROL_PATTERNS,
    CONTEXT_INDICATORS,
    normalize_disease_name,
    is_valid_symptom,
    is_context_relevant
)


@dataclass
class Entity:
    """Entity data class"""
    name: str
    type: str
    confidence: float = 1.0
    evidence: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'type': self.type,
            'confidence': self.confidence,
            'evidence': self.evidence
        }


class EntityExtractor:
    """Entity Extractor - 优化版，支持从混杂文本中准确抽取"""
    
    def __init__(self):
        self.entities: List[Entity] = []
        self.disease_found: Set[str] = set()
        self.relevant_sentences: List[str] = []
    
    def extract(self, text: str) -> List[Entity]:
        """Extract entities from text"""
        self.entities = []
        self.disease_found = set()
        self.relevant_sentences = []
        
        sentences = self._split_into_sentences(text)
        
        self._filter_relevant_sentences(sentences)
        
        relevant_text = ' '.join(self.relevant_sentences) if self.relevant_sentences else text
        
        self._extract_diseases(relevant_text)
        self._extract_symptoms(relevant_text)
        self._extract_stages(relevant_text)
        self._extract_causes(relevant_text)
        self._extract_controls(relevant_text)
        self._extract_pesticides(relevant_text)
        self._extract_parts(relevant_text)
        
        self.entities = self._remove_duplicates(self.entities)
        return self.entities
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        sentences = re.split(r'[。！？\n]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _filter_relevant_sentences(self, sentences: List[str]) -> None:
        """过滤出与病害相关的句子"""
        positive_indicators = CONTEXT_INDICATORS["positive"]
        disease_indicators = TARGET_DISEASES + list(DISEASE_ALIASES.keys())
        for alias_list in DISEASE_ALIASES.values():
            disease_indicators.extend(alias_list)
        
        for sentence in sentences:
            is_relevant = False
            
            for disease in disease_indicators:
                if disease in sentence:
                    is_relevant = True
                    break
            
            if not is_relevant:
                for indicator in positive_indicators:
                    if indicator in sentence:
                        is_relevant = True
                        break
            
            if is_relevant:
                self.relevant_sentences.append(sentence)
    
    def _extract_diseases(self, text: str) -> None:
        """抽取病害实体 - 5种目标病害"""
        for disease in TARGET_DISEASES:
            if disease in text:
                self.entities.append(Entity(
                    name=disease,
                    type="Disease",
                    confidence=1.0,
                    evidence=text
                ))
                self.disease_found.add(disease)
        
        for standard_name, aliases in DISEASE_ALIASES.items():
            for alias in aliases:
                if alias in text and standard_name not in self.disease_found:
                    self.entities.append(Entity(
                        name=standard_name,
                        type="Disease",
                        confidence=0.9,
                        evidence=text
                    ))
                    self.disease_found.add(standard_name)
                    break
    
    def _extract_symptoms(self, text: str) -> None:
        """抽取症状实体 - 使用关键词和正则表达式"""
        extracted_symptoms = set()
        
        for pattern in SYMPTOM_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else (match[1] if len(match) > 1 else "")
                
                match = match.strip()
                if match and is_valid_symptom(match) and match not in extracted_symptoms:
                    if not self._is_negative_context(text, match):
                        self.entities.append(Entity(
                            name=match,
                            type="Symptom",
                            confidence=0.85,
                            evidence=text
                        ))
                        extracted_symptoms.add(match)
        
        for keyword in SYMPTOM_KEYWORDS:
            if keyword in text and keyword not in extracted_symptoms:
                if not self._is_negative_context(text, keyword):
                    self.entities.append(Entity(
                        name=keyword,
                        type="Symptom",
                        confidence=0.7,
                        evidence=text
                    ))
                    extracted_symptoms.add(keyword)
    
    def _extract_stages(self, text: str) -> None:
        """抽出生育期实体"""
        for stage in VALID_STAGES:
            if stage in text:
                self.entities.append(Entity(
                    name=stage,
                    type="Stage",
                    confidence=1.0,
                    evidence=text
                ))
    
    def _extract_causes(self, text: str) -> None:
        """抽取病因实体"""
        extracted_causes = set()
        
        for pattern in CAUSE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                match = match.strip()
                if match and len(match) >= 4 and match not in extracted_causes:
                    self.entities.append(Entity(
                        name=match,
                        type="Cause",
                        confidence=0.9,
                        evidence=text
                    ))
                    extracted_causes.add(match)
        
        for keyword in CAUSE_KEYWORDS:
            if keyword in text and keyword not in extracted_causes:
                context = self._get_context(text, keyword, window=20)
                if context and not self._is_negative_context(context, keyword):
                    self.entities.append(Entity(
                        name=keyword,
                        type="Cause",
                        confidence=0.6,
                        evidence=text
                    ))
                    extracted_causes.add(keyword)
    
    def _extract_controls(self, text: str) -> None:
        """抽取防治方法实体"""
        extracted_controls = set()
        
        for pattern in CONTROL_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                match = match.strip()
                if match and 4 <= len(match) <= 30 and match not in extracted_controls:
                    self.entities.append(Entity(
                        name=match,
                        type="Control",
                        confidence=0.9,
                        evidence=text
                    ))
                    extracted_controls.add(match)
        
        for keyword in CONTROL_KEYWORDS:
            if keyword in text and keyword not in extracted_controls:
                context = self._get_context(text, keyword, window=15)
                if context:
                    self.entities.append(Entity(
                        name=keyword,
                        type="Control",
                        confidence=0.5,
                        evidence=text
                    ))
                    extracted_controls.add(keyword)
    
    def _extract_pesticides(self, text: str) -> None:
        """抽取药剂实体"""
        for pesticide in PESTICIDE_KEYWORDS:
            if pesticide in text:
                self.entities.append(Entity(
                    name=pesticide,
                    type="Pesticide",
                    confidence=1.0,
                    evidence=text
                ))
    
    def _extract_parts(self, text: str) -> None:
        """抽取危害部位实体"""
        for part in VALID_PARTS:
            if part in text:
                self.entities.append(Entity(
                    name=part,
                    type="Part",
                    confidence=1.0,
                    evidence=text
                ))
    
    def _get_context(self, text: str, keyword: str, window: int = 20) -> str:
        """获取关键词周围的上下文"""
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        return text[start:end]
    
    def _is_negative_context(self, text: str, keyword: str) -> bool:
        """检查是否为否定上下文"""
        negative_words = CONTEXT_INDICATORS["negative"]
        idx = text.find(keyword)
        if idx == -1:
            return False
        
        start = max(0, idx - 10)
        context_before = text[start:idx]
        
        for neg in negative_words:
            if neg in context_before:
                return True
        return False
    
    def _remove_duplicates(self, entities: List[Entity]) -> List[Entity]:
        """去除重复实体，保留置信度最高的"""
        seen = {}
        for entity in entities:
            key = (entity.name, entity.type)
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity
        return list(seen.values())
    
    def get_statistics(self) -> Dict:
        stats = {'total': len(self.entities), 'by_type': {}}
        for entity in self.entities:
            stats['by_type'][entity.type] = stats['by_type'].get(entity.type, 0) + 1
        return stats


def extract_entities(text: str) -> List[Dict]:
    extractor = EntityExtractor()
    entities = extractor.extract(text)
    return [e.to_dict() for e in entities]


if __name__ == "__main__":
    test_text = """
    今天天气不错，我去超市买了点菜。回来路上看到一片麦田，
    听老农说今年小麦条锈病挺严重的，叶片上出现鲜黄色疱状孢子堆，
    沿叶脉排列成行。适宜温度10-15℃，相对湿度80%以上。
    返青拔节期至抽穗扬花期易发病。发病初期喷施三唑酮、丙环唑防治。
    选用抗病品种，合理密植。晚上回家做了个红烧肉，味道不错。
    """
    extractor = EntityExtractor()
    entities = extractor.extract(test_text)
    print(f"实体数量: {len(entities)}")
    for e in entities:
        print(f"  [{e.type}] {e.name} (置信度: {e.confidence:.2f})")

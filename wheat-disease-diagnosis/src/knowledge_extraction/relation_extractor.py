# -*- coding: utf-8 -*-
"""
Relation Extractor Module - 优化版
6种关键关系：HAS_SYMPTOM, OCCURS_AT, CAUSED_BY, HAS_CONTROL, USES_PESTICIDE, AFFECTS_PART
支持从混杂文本中准确抽取关系
"""

import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

from .extraction_rules import (
    TARGET_DISEASES,
    DISEASE_ALIASES,
    VALID_PARTS,
    VALID_STAGES,
    PESTICIDE_KEYWORDS,
    SYMPTOM_KEYWORDS,
    SYMPTOM_PATTERNS,
    CAUSE_PATTERNS,
    CONTROL_PATTERNS,
    RELATION_KEYWORDS,
    normalize_disease_name,
    is_valid_symptom
)


@dataclass
class Relation:
    """Relation data class"""
    head_entity: str
    head_type: str
    relation_type: str
    tail_entity: str
    tail_type: str
    confidence: float = 1.0
    evidence: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'head': self.head_entity,
            'head_type': self.head_type,
            'relation': self.relation_type,
            'tail': self.tail_entity,
            'tail_type': self.tail_type,
            'confidence': self.confidence,
            'evidence': self.evidence
        }


class RelationExtractor:
    """Relation Extractor - 优化版，支持从混杂文本中准确抽取关系"""
    
    def __init__(self):
        self.relations: List[Relation] = []
        self.disease_name: Optional[str] = None
    
    def extract(self, text: str, entities: List[Dict] = None) -> List[Relation]:
        """Extract relations from text"""
        self.relations = []
        
        self.disease_name = self._find_disease(text, entities)
        if not self.disease_name:
            return self.relations
        
        relevant_text = self._get_relevant_text(text)
        
        self._extract_symptom_relations(relevant_text)
        self._extract_stage_relations(relevant_text)
        self._extract_cause_relations(relevant_text)
        self._extract_control_relations(relevant_text)
        self._extract_pesticide_relations(relevant_text)
        self._extract_part_relations(relevant_text)
        
        self.relations = self._remove_duplicates(self.relations)
        return self.relations
    
    def _find_disease(self, text: str, entities: List[Dict] = None) -> Optional[str]:
        """找出文本中的目标病害"""
        if entities:
            for entity in entities:
                if entity.get('type') == 'Disease':
                    return entity['name']
        
        for disease in TARGET_DISEASES:
            if disease in text:
                return disease
        
        for standard_name, aliases in DISEASE_ALIASES.items():
            for alias in aliases:
                if alias in text:
                    return standard_name
        
        return None
    
    def _get_relevant_text(self, text: str) -> str:
        """获取与当前病害相关的文本片段"""
        sentences = re.split(r'[。！？\n]+', text)
        relevant_sentences = []
        
        disease_indicators = [self.disease_name]
        if self.disease_name in DISEASE_ALIASES:
            disease_indicators.extend(DISEASE_ALIASES[self.disease_name])
        
        relation_keywords = []
        for rel_info in RELATION_KEYWORDS.values():
            relation_keywords.extend(rel_info["keywords"])
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            is_relevant = False
            
            for indicator in disease_indicators:
                if indicator and indicator in sentence:
                    is_relevant = True
                    break
            
            if not is_relevant:
                for keyword in relation_keywords:
                    if keyword in sentence:
                        is_relevant = True
                        break
            
            if is_relevant:
                relevant_sentences.append(sentence)
        
        return ' '.join(relevant_sentences) if relevant_sentences else text
    
    def _add_relation(self, head: str, head_type: str, relation: str,
                      tail: str, tail_type: str, evidence: str, confidence: float = 1.0):
        """添加关系"""
        tail = tail.strip()
        if len(tail) < 2:
            return
        
        self.relations.append(Relation(
            head_entity=head,
            head_type=head_type,
            relation_type=relation,
            tail_entity=tail,
            tail_type=tail_type,
            confidence=confidence,
            evidence=evidence
        ))
    
    def _extract_symptom_relations(self, text: str) -> None:
        """抽取症状关系 HAS_SYMPTOM"""
        extracted = set()
        
        for pattern in SYMPTOM_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else (match[1] if len(match) > 1 else "")
                
                match = match.strip()
                if match and is_valid_symptom(match) and match not in extracted:
                    if not self._is_negative_context(text, match):
                        self._add_relation(
                            self.disease_name, "Disease", "HAS_SYMPTOM",
                            match, "Symptom", text, confidence=0.85
                        )
                        extracted.add(match)
        
        for keyword in SYMPTOM_KEYWORDS:
            if keyword in text and keyword not in extracted:
                if not self._is_negative_context(text, keyword):
                    self._add_relation(
                        self.disease_name, "Disease", "HAS_SYMPTOM",
                        keyword, "Symptom", text, confidence=0.7
                    )
                    extracted.add(keyword)
    
    def _extract_stage_relations(self, text: str) -> None:
        """抽出生育期关系 OCCURS_AT"""
        stage_keywords = RELATION_KEYWORDS["OCCURS_AT"]["keywords"]
        
        for stage in VALID_STAGES:
            if stage in text:
                context = self._get_context(text, stage, window=30)
                has_relation_keyword = any(kw in context for kw in stage_keywords)
                
                self._add_relation(
                    self.disease_name, "Disease", "OCCURS_AT",
                    stage, "Stage", text,
                    confidence=0.95 if has_relation_keyword else 0.8
                )
    
    def _extract_cause_relations(self, text: str) -> None:
        """抽取病因关系 CAUSED_BY"""
        extracted = set()
        
        for pattern in CAUSE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                match = match.strip()
                if match and len(match) >= 4 and match not in extracted:
                    self._add_relation(
                        self.disease_name, "Disease", "CAUSED_BY",
                        match, "Cause", text, confidence=0.9
                    )
                    extracted.add(match)
    
    def _extract_control_relations(self, text: str) -> None:
        """抽取防治方法关系 HAS_CONTROL"""
        extracted = set()
        
        for pattern in CONTROL_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                match = match.strip()
                if match and 4 <= len(match) <= 30 and match not in extracted:
                    self._add_relation(
                        self.disease_name, "Disease", "HAS_CONTROL",
                        match, "Control", text, confidence=0.9
                    )
                    extracted.add(match)
    
    def _extract_pesticide_relations(self, text: str) -> None:
        """抽取药剂关系 USES_PESTICIDE"""
        pesticide_keywords = RELATION_KEYWORDS["USES_PESTICIDE"]["keywords"]
        
        for pesticide in PESTICIDE_KEYWORDS:
            if pesticide in text:
                context = self._get_context(text, pesticide, window=30)
                has_relation_keyword = any(kw in context for kw in pesticide_keywords)
                
                self._add_relation(
                    self.disease_name, "Disease", "USES_PESTICIDE",
                    pesticide, "Pesticide", text,
                    confidence=0.95 if has_relation_keyword else 0.8
                )
    
    def _extract_part_relations(self, text: str) -> None:
        """抽取危害部位关系 AFFECTS_PART"""
        part_keywords = RELATION_KEYWORDS["AFFECTS_PART"]["keywords"]
        
        for part in VALID_PARTS:
            if part in text:
                context = self._get_context(text, part, window=30)
                has_relation_keyword = any(kw in context for kw in part_keywords)
                
                if has_relation_keyword:
                    self._add_relation(
                        self.disease_name, "Disease", "AFFECTS_PART",
                        part, "Part", text, confidence=0.95
                    )
    
    def _get_context(self, text: str, keyword: str, window: int = 30) -> str:
        """获取关键词周围的上下文"""
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        return text[start:end]
    
    def _is_negative_context(self, text: str, keyword: str) -> bool:
        """检查是否为否定上下文"""
        negative_words = ["不", "无", "未", "正常", "健康", "抗病"]
        idx = text.find(keyword)
        if idx == -1:
            return False
        
        start = max(0, idx - 10)
        context_before = text[start:idx]
        
        for neg in negative_words:
            if neg in context_before:
                return True
        return False
    
    def _remove_duplicates(self, relations: List[Relation]) -> List[Relation]:
        """去除重复关系，保留置信度最高的"""
        seen = {}
        for relation in relations:
            key = (relation.head_entity, relation.relation_type, relation.tail_entity)
            if key not in seen or relation.confidence > seen[key].confidence:
                seen[key] = relation
        return list(seen.values())
    
    def get_statistics(self) -> Dict:
        stats = {
            'total': len(self.relations),
            'by_type': {},
            'by_head': {}
        }
        for relation in self.relations:
            stats['by_type'][relation.relation_type] = stats['by_type'].get(relation.relation_type, 0) + 1
            stats['by_head'][relation.head_entity] = stats['by_head'].get(relation.head_entity, 0) + 1
        return stats


def extract_relations(text: str, entities: List[Dict] = None) -> List[Dict]:
    extractor = RelationExtractor()
    relations = extractor.extract(text, entities)
    return [r.to_dict() for r in relations]


if __name__ == "__main__":
    test_text = """
    今天天气不错，我去超市买了点菜。回来路上看到一片麦田，
    听老农说今年小麦条锈病挺严重的，主要危害叶片和叶鞘。
    叶片上出现鲜黄色疱状孢子堆，沿叶脉排列成行。
    适宜温度10-15℃，相对湿度80%以上。
    返青拔节期至抽穗扬花期易发病。
    发病初期喷施三唑酮、丙环唑防治。
    选用抗病品种，合理密植。
    晚上回家做了个红烧肉，味道不错。
    """
    extractor = RelationExtractor()
    relations = extractor.extract(test_text)
    print(f"关系数量: {len(relations)}")
    for r in relations:
        print(f"  {r.head_entity} --[{r.relation_type}]--> {r.tail_entity} (置信度: {r.confidence:.2f})")

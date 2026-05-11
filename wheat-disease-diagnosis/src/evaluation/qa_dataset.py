# -*- coding: utf-8 -*-
"""
问答对数据集模块
用于评估检索效果
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import random


@dataclass
class QAPair:
    """问答对数据类"""
    question: str
    answer: str
    ground_truth_docs: List[str] = field(default_factory=list)
    disease_type: str = ""
    difficulty: str = "medium"
    source: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QAPair':
        return cls(
            question=data.get('question', ''),
            answer=data.get('answer', ''),
            ground_truth_docs=data.get('ground_truth_docs', []),
            disease_type=data.get('disease_type', ''),
            difficulty=data.get('difficulty', 'medium'),
            source=data.get('source', '')
        )


class QADataset:
    """问答数据集类"""
    
    def __init__(self, qa_pairs: List[QAPair] = None):
        self.qa_pairs = qa_pairs or []
    
    def add_qa_pair(self, qa_pair: QAPair):
        """添加问答对"""
        self.qa_pairs.append(qa_pair)
    
    def get_questions(self) -> List[str]:
        """获取所有问题"""
        return [qa.question for qa in self.qa_pairs]
    
    def get_ground_truth_docs(self) -> List[set]:
        """获取所有真实文档集合"""
        return [set(qa.ground_truth_docs) for qa in self.qa_pairs]
    
    def filter_by_disease(self, disease_type: str) -> 'QADataset':
        """按病害类型过滤"""
        filtered = [qa for qa in self.qa_pairs if qa.disease_type == disease_type]
        return QADataset(filtered)
    
    def filter_by_difficulty(self, difficulty: str) -> 'QADataset':
        """按难度过滤"""
        filtered = [qa for qa in self.qa_pairs if qa.difficulty == difficulty]
        return QADataset(filtered)
    
    def shuffle(self, seed: int = None):
        """随机打乱"""
        if seed:
            random.seed(seed)
        random.shuffle(self.qa_pairs)
    
    def split(self, ratio: float = 0.8, seed: int = None) -> tuple:
        """分割数据集"""
        if seed:
            random.seed(seed)
        
        shuffled = self.qa_pairs.copy()
        random.shuffle(shuffled)
        
        split_idx = int(len(shuffled) * ratio)
        train = QADataset(shuffled[:split_idx])
        test = QADataset(shuffled[split_idx:])
        
        return train, test
    
    def save(self, filepath: str):
        """保存数据集"""
        data = {
            'qa_pairs': [qa.to_dict() for qa in self.qa_pairs],
            'total': len(self.qa_pairs)
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'QADataset':
        """加载数据集"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        qa_pairs = [QAPair.from_dict(qa) for qa in data.get('qa_pairs', [])]
        return cls(qa_pairs)
    
    def __len__(self):
        return len(self.qa_pairs)
    
    def __getitem__(self, idx):
        return self.qa_pairs[idx]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            'total': len(self.qa_pairs),
            'by_disease': {},
            'by_difficulty': {}
        }
        
        for qa in self.qa_pairs:
            stats['by_disease'][qa.disease_type] = stats['by_disease'].get(qa.disease_type, 0) + 1
            stats['by_difficulty'][qa.difficulty] = stats['by_difficulty'].get(qa.difficulty, 0) + 1
        
        return stats


def generate_synthetic_qa_dataset(disease_data: Dict, num_per_disease: int = 20) -> QADataset:
    """生成合成问答数据集"""
    qa_pairs = []
    
    symptom_templates = [
        "小麦{part}出现{symptom}，是什么病害？",
        "{symptom}症状，可能是哪种病害？",
        "发现小麦{part}有{symptom}的表现，如何诊断？",
        "田间发现小麦{symptom}，请问是什么病？",
        "小麦{part}{symptom}，这是什么病害？"
    ]
    
    parts = ["叶片", "茎秆", "穗部", "叶鞘", "茎基部", "根系"]
    
    for disease_name, info in disease_data.items():
        symptoms = info.get('symptom', '').split('，')
        
        for i in range(num_per_disease):
            template = random.choice(symptom_templates)
            symptom = random.choice(symptoms) if symptoms else "病斑"
            part = random.choice(parts)
            
            question = template.format(part=part, symptom=symptom)
            
            qa = QAPair(
                question=question,
                answer=disease_name,
                ground_truth_docs=[disease_name],
                disease_type=disease_name,
                difficulty=random.choice(['easy', 'medium', 'hard']),
                source='synthetic'
            )
            qa_pairs.append(qa)
    
    return QADataset(qa_pairs)


if __name__ == "__main__":
    disease_data = {
        "小麦条锈病": {
            "symptom": "叶片出现鲜黄色疱状孢子堆，沿叶脉排列成行，呈虚线状"
        },
        "小麦白粉病": {
            "symptom": "叶片表面出现白色粉状霉斑，逐渐扩大融合"
        }
    }
    
    dataset = generate_synthetic_qa_dataset(disease_data, num_per_disease=10)
    print(f"生成 {len(dataset)} 个问答对")
    
    stats = dataset.get_statistics()
    print(f"统计信息: {stats}")
    
    dataset.save("test_qa_dataset.json")
    print("数据集已保存")

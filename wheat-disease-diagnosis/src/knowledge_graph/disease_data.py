# -*- coding: utf-8 -*-
"""
小麦病害知识图谱数据定义
实体类型：Disease, Symptom, Stage, Cause, Control, Pesticide, Part
关系类型：HAS_SYMPTOM, OCCURS_AT, CAUSED_BY, HAS_CONTROL, USES_PESTICIDE, AFFECTS_PART
"""

WHEAT_DISEASE_DATA = {
    "小麦条锈病": {
        "symptom": "叶片出现鲜黄色疱状孢子堆，沿叶脉排列成行，呈虚线状；严重时孢子堆融合，叶片枯黄；后期出现黑色冬孢子堆",
        "stage": "返青拔节期至抽穗扬花期",
        "cause": "温度10-15℃，相对湿度80%以上；春季多雨、露水重、气温偏低；品种抗性差、氮肥过量施用",
        "control": "选用抗病品种；发病初期喷施三唑类杀菌剂；合理密植，避免氮肥过量；清除田间病残体",
        "pesticide": "三唑酮、丙环唑、戊唑醇、氟环唑",
        "part": "叶片、叶鞘、茎秆"
    },
    "小麦白粉病": {
        "symptom": "叶片、叶鞘表面出现白色粉状霉斑，逐渐扩大融合；后期霉层变为灰白色至浅褐色，散生黑色小粒点；病叶枯黄卷曲",
        "stage": "分蘖期至灌浆期",
        "cause": "温度15-20℃，相对湿度70%以上；种植密度大、通风透光差、氮肥过量；春季温暖少雨天气易流行",
        "control": "种植抗病品种；合理密植，改善田间通风；发病初期喷施杀菌剂；控制氮肥用量",
        "pesticide": "三唑酮、腈菌唑、丙环唑、氟硅唑",
        "part": "叶片、叶鞘、茎秆、穗部"
    },
    "小麦赤霉病": {
        "symptom": "小穗出现水渍状淡褐色病斑，后扩展至全穗；潮湿条件下病部出现粉红色霉层；籽粒干瘪皱缩，呈粉红色",
        "stage": "扬花期至灌浆期",
        "cause": "温度25-28℃，相对湿度85%以上；扬花期遇连续阴雨天气；前茬作物残体多、田间湿度大",
        "control": "选用抗病品种；扬花期喷药预防；清除田间病残体；合理轮作，降低田间湿度",
        "pesticide": "多菌灵、甲基硫菌灵、戊唑醇、咪鲜胺",
        "part": "穗部、茎秆"
    },
    "小麦纹枯病": {
        "symptom": "茎基部出现椭圆形褐色病斑，后扩展成云纹状；病斑绕茎一周时植株枯死；叶鞘内侧可见白色菌丝和褐色菌核",
        "stage": "分蘖期至抽穗期",
        "cause": "温度20-25℃，土壤湿度大；播种过早、密度过大、氮肥过量；排水不良的低洼田块",
        "control": "选用抗病品种；适期播种，合理密植；加强田间排水；发病初期喷药防治",
        "pesticide": "井冈霉素、噻呋酰胺、戊唑醇、苯醚甲环唑",
        "part": "茎基部、叶鞘、根系"
    },
    "小麦叶锈病": {
        "symptom": "叶片出现橙褐色圆形夏孢子堆，散生不排列成行；孢子堆表皮破裂后散出褐色粉末；后期出现黑色冬孢子堆",
        "stage": "拔节期至灌浆期",
        "cause": "温度18-22℃，相对湿度70%以上；春季温暖多雨；品种抗性差、田间湿度大",
        "control": "选用抗病品种；发病初期喷施三唑类杀菌剂；合理施肥，增强植株抗性；清除田间病残体",
        "pesticide": "三唑酮、丙环唑、戊唑醇、氟环唑",
        "part": "叶片、叶鞘"
    }
}

TARGET_DISEASES = list(WHEAT_DISEASE_DATA.keys())

ENTITY_TYPES = ["Disease", "Symptom", "Stage", "Cause", "Control", "Pesticide", "Part"]

RELATION_TYPES = [
    ("Disease", "HAS_SYMPTOM", "Symptom", "病害 — 表现为 → 症状"),
    ("Disease", "OCCURS_AT", "Stage", "病害 — 发生于 → 生育期"),
    ("Disease", "CAUSED_BY", "Cause", "病害 — 由 → 病因"),
    ("Disease", "HAS_CONTROL", "Control", "病害 — 防治方法 → 防治方法"),
    ("Disease", "USES_PESTICIDE", "Pesticide", "病害 — 使用药剂 → 药剂"),
    ("Disease", "AFFECTS_PART", "Part", "病害 — 危害部位 → 部位")
]


def get_disease_data():
    return WHEAT_DISEASE_DATA

def get_disease_names():
    return TARGET_DISEASES

def get_entity_types():
    return ENTITY_TYPES

def get_relation_types():
    return RELATION_TYPES

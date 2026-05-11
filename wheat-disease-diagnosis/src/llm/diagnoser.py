# -*- coding: utf-8 -*-
"""
大模型诊断生成模块
调用DeepSeek API进行病害诊断
"""

import requests
import sys
sys.path.append('..')
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL, MAX_TOKENS, TEMPERATURE


class LLMdiagnoser:
    """大模型诊断器"""
    
    def __init__(self, api_key=DEEPSEEK_API_KEY, api_url=DEEPSEEK_API_URL, model=DEEPSEEK_MODEL):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def build_prompt(self, retrieved_context, user_input):
        """构建诊断提示词"""
        prompt = f"""
你是一位资深的小麦病害诊断专家。请根据以下检索到的小麦病害知识信息，对用户的症状描述进行诊断分析。

【检索到的知识信息】
{retrieved_context}

【用户描述的症状】
{user_input}

【诊断要求】
1. 诊断结果：明确给出病害名称，如果症状不明确，给出最可能的病害并说明原因；
2. 匹配依据：结合症状特征、发病条件等详细说明诊断依据；
3. 完整建议：包含传播途径、发病时期、危害部位、防治方法、适用药剂的完整建议；
4. 预防措施：给出针对性的预防建议；
5. 注意事项：提醒用户需要注意的问题。

【输出格式】
请按照以下结构输出诊断结果：

## 诊断结果
[病害名称]

## 诊断依据
[详细说明症状匹配情况]

## 病害详情
- 发病时期：[...]
- 危害部位：[...]

## 防治建议
[详细的防治方法]

## 推荐药剂
[药剂名称及使用方法]

## 预防措施
[预防建议]

## 注意事项
[需要特别注意的问题]

请确保语言通俗易懂，符合农业生产实际，避免过多专业术语堆砌。
"""
        return prompt
    
    def diagnose(self, retrieved_context, user_input, temperature=TEMPERATURE, max_tokens=MAX_TOKENS):
        """执行诊断"""
        prompt = self.build_prompt(retrieved_context, user_input)
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            return "诊断失败：API请求超时，请稍后重试"
        except requests.exceptions.RequestException as e:
            return f"诊断失败：网络请求错误 - {str(e)}"
        except KeyError:
            return "诊断失败：API返回格式异常"
        except Exception as e:
            return f"诊断失败：{str(e)}"
    
    def simple_chat(self, message):
        """简单对话接口"""
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"对话失败：{str(e)}"


def diagnose_disease(retrieved_context, user_input):
    """便捷函数：诊断病害"""
    diagnoser = LLMdiagnoser()
    return diagnoser.diagnose(retrieved_context, user_input)


if __name__ == "__main__":
    test_context = """
【病害名称】：小麦条锈病
【典型症状】：叶片出现鲜黄色疱状孢子堆，沿叶脉排列成行
【发病条件】：适宜温度10-15℃，相对湿度80%以上
"""
    test_input = "小麦叶片上出现黄色的斑点，排列成行"
    print(diagnose_disease(test_context, test_input))

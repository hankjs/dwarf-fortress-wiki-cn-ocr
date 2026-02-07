# -*- coding: utf-8 -*-
"""
句子翻译模块 - 使用 MyMemory Translation API
整句翻译OCR识别的文本，保护游戏术语
"""

import re
import requests
from typing import Dict, Optional


class SentenceTranslator:
    """句子翻译器，使用 MyMemory API + 术语保护"""

    API_URL = "https://api.mymemory.translated.net/get"

    def __init__(self, term_dict: Dict[str, str] = None):
        """
        Args:
            term_dict: 游戏术语字典 (EN -> CN)
        """
        self.term_dict = term_dict or {}

    def is_ready(self) -> bool:
        """检查翻译器是否就绪（总是就绪，只需网络）"""
        return True

    def should_translate(self, text: str) -> bool:
        """判断是否应该翻译（多个单词才翻译）"""
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        return len(words) > 1

    def translate(self, text: str) -> Optional[str]:
        """
        翻译文本，保护游戏术语

        策略：
        1. 在原文中将术语替换为中文
        2. 调用 MyMemory API 翻译
        3. 清理和后处理

        Returns:
            翻译后的文本，失败返回None
        """
        if not text or not text.strip():
            return None

        try:
            # 1. 预处理：将术语替换为中文
            preprocessed = self._preprocess_replace_terms(text)

            # 2. 调用 MyMemory API
            translated = self._call_mymemory_api(preprocessed)

            if not translated:
                return None

            # 3. 后处理：清理翻译结果
            result = self._post_process(translated)

            return result

        except Exception as e:
            print(f"翻译失败: {e}")
            return None

    def _preprocess_replace_terms(self, text: str) -> str:
        """
        预处理：将术语替换为中文

        例如：
        "The dwarf miner" -> "The 矮人 矿工"
        """
        result = text

        # 按术语长度排序（长的优先，避免部分匹配）
        sorted_terms = sorted(
            self.term_dict.items(), key=lambda x: len(x[0]), reverse=True
        )

        # 记录已替换的位置，避免重复替换
        replacements = []

        for en_term, zh_term in sorted_terms:
            # 查找所有匹配位置（忽略大小写）
            pattern = r"\b" + re.escape(en_term) + r"\b"
            matches = list(re.finditer(pattern, result, re.IGNORECASE))

            for match in reversed(matches):  # 从后往前替换，避免位置偏移
                # 检查是否已被其他术语覆盖
                start, end = match.start(), match.end()
                if any(
                    r_start <= start < r_end or r_start < end <= r_end
                    for r_start, r_end in replacements
                ):
                    continue

                # 直接替换为中文术语
                result = result[:start] + zh_term + result[end:]
                replacements.append((start, start + len(zh_term)))

        return result

    def _call_mymemory_api(self, text: str) -> Optional[str]:
        """
        调用 MyMemory Translation API

        Args:
            text: 待翻译文本

        Returns:
            翻译后的文本，失败返回None
        """
        try:
            params = {
                'q': text,
                'langpair': 'en|zh-CN'
            }

            response = requests.get(
                self.API_URL,
                params=params,
                timeout=10  # 10秒超时
            )

            if response.status_code != 200:
                print(f"API 请求失败: HTTP {response.status_code}")
                return None

            data = response.json()

            # 检查响应状态
            if data.get('responseStatus') != 200:
                print(f"翻译失败: {data.get('responseDetails', 'Unknown error')}")
                return None

            # 提取翻译结果
            translated = data.get('responseData', {}).get('translatedText')

            if not translated:
                print("翻译结果为空")
                return None

            return translated

        except requests.Timeout:
            print("API 请求超时")
            return None
        except requests.RequestException as e:
            print(f"网络请求失败: {e}")
            return None
        except Exception as e:
            print(f"API 调用异常: {e}")
            return None

    def _post_process(self, text: str) -> str:
        """
        后处理：清理翻译结果

        - 移除多余空格
        - 清理特殊标记
        """
        result = text

        # 移除多余空格
        result = re.sub(r'\s+', ' ', result)

        # 清理可能的翻译噪音
        result = re.sub(r'\([^)]*单位[^)]*\)', '', result)  # (单位:千美元)

        return result.strip()


# 全局单例
_translator_instance = None


def get_sentence_translator(term_dict: Dict[str, str] = None) -> SentenceTranslator:
    """获取全局翻译器单例"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = SentenceTranslator(term_dict)
    return _translator_instance

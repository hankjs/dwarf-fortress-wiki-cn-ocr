"""
翻译相关功能模块
包括翻译映射表加载和词汇替换翻译
"""

import json
import os
import re


def load_translation_map():
    """加载翻译映射表"""
    # 获取项目根目录（src 的父目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    map_path = os.path.join(project_root, "translation_map.json")
    if os.path.exists(map_path):
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"title_map": {}, "vocabulary_map": {}}


def translate_content_by_vocab(content, vocab_map):
    """
    使用词汇映射表进行简单文本替换翻译
    按词长度降序排列，避免短词替换干扰长词
    保护 Wiki 语法（[[File:...]]、[[link]] 等）不被破坏
    """
    # 先提取并保护 Wiki 语法
    placeholders = {}
    placeholder_id = 0

    def protect_wiki_syntax(match):
        nonlocal placeholder_id
        placeholder = f"__WIKI_PROTECT_{placeholder_id}__"
        placeholder_id += 1
        placeholders[placeholder] = match.group(0)
        return placeholder

    # 保护 [[File:...]] 和 [[Image:...]] 语法
    content = re.sub(
        r"\[\[(File|Image):[^\]]+\]\]",
        protect_wiki_syntax,
        content,
        flags=re.IGNORECASE,
    )
    # 保护 [[link|display]] 和 [[link]] 语法
    content = re.sub(
        r"\[\[[^\]]+\]\]",
        protect_wiki_syntax,
        content,
    )
    # 保护模板语法 {{...}}
    content = re.sub(
        r"\{\{[^}]+\}\}",
        protect_wiki_syntax,
        content,
    )
    # 保护 URL
    content = re.sub(
        r"https?://[^\s\]]+",
        protect_wiki_syntax,
        content,
    )

    # 按词长度降序排序，确保长词先被替换
    sorted_vocab = sorted(vocab_map.items(), key=lambda x: len(x[0]), reverse=True)

    result = content
    for en_word, cn_word in sorted_vocab:
        # 使用正则表达式进行整词匹配（忽略大小写）
        pattern = r"\b" + re.escape(en_word) + r"\b"
        result = re.sub(pattern, cn_word, result, flags=re.IGNORECASE)

    # 还原受保护的 Wiki 语法
    for placeholder, original in placeholders.items():
        result = result.replace(placeholder, original)

    return result

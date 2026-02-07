#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试翻译功能
"""

import sys
import os
import unittest

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ocr_tool import load_translation_map, translate_content_by_vocab


class TestTranslation(unittest.TestCase):
    """测试翻译功能"""

    def test_load_translation_map(self):
        """测试加载翻译映射表"""
        trans_map = load_translation_map()
        self.assertIn('title_map', trans_map)
        self.assertIn('vocabulary_map', trans_map)
        self.assertIsInstance(trans_map['title_map'], dict)
        self.assertIsInstance(trans_map['vocabulary_map'], dict)

    def test_translate_content_by_vocab(self):
        """测试词汇替换翻译"""
        vocab_map = {
            'dwarf': '矮人',
            'fortress': '要塞',
            'axe': '斧头'
        }
        content = "The dwarf lives in a fortress with an axe."
        result = translate_content_by_vocab(content, vocab_map)
        
        # 检查翻译结果
        self.assertIn('矮人', result)
        self.assertIn('要塞', result)
        self.assertIn('斧头', result)
        
    def test_translate_with_wiki_syntax(self):
        """测试翻译时保护 Wiki 语法"""
        vocab_map = {
            'dwarf': '矮人',
            'fortress': '要塞'
        }
        content = "The [[dwarf]] lives in a [[fortress]]."
        result = translate_content_by_vocab(content, vocab_map)
        
        # 链接语法应该被保护，不会被破坏
        self.assertIn('[[dwarf]]', result)
        self.assertIn('[[fortress]]', result)

    def test_translate_empty_vocab(self):
        """测试空词汇表"""
        content = "Some text"
        result = translate_content_by_vocab(content, {})
        self.assertEqual(result, content)

    def test_translate_longer_words_first(self):
        """测试长词优先替换"""
        vocab_map = {
            'dwarf': '矮人',
            'dwarven': '矮人的',
            'dwarven fortress': '矮人要塞'
        }
        content = "A dwarven fortress"
        result = translate_content_by_vocab(content, vocab_map)
        
        # "dwarven fortress" 应该作为一个整体被替换
        self.assertIn('矮人要塞', result)


if __name__ == '__main__':
    unittest.main()

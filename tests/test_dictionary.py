"""
测试英语词典模块
"""

import os
import sys
import unittest

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dictionary import DictionaryManager


class TestDictionary(unittest.TestCase):
    """测试词典功能"""

    @classmethod
    def setUpClass(cls):
        """初始化测试"""
        cls.dict_manager = DictionaryManager()
        if not cls.dict_manager.is_available():
            print("\n⚠️  警告: ECDICT数据库未找到")
            print("请运行: python scripts/download_ecdict.py")
            print("部分测试将被跳过\n")

    def test_database_available(self):
        """测试数据库是否可用"""
        print(f"数据库可用: {self.dict_manager.is_available()}")
        # 不强制要求数据库存在，只是报告状态
        self.assertIsNotNone(self.dict_manager)

    def test_lookup_simple_word(self):
        """测试简单单词查询"""
        if not self.dict_manager.is_available():
            self.skipTest("数据库不可用")

        result = self.dict_manager.lookup_word("hello")
        self.assertIsNotNone(result, "应该能查询到 'hello'")
        self.assertEqual(result['word'], 'hello')
        self.assertIn('translation', result)
        print(f"\n'hello' 的释义: {result.get('translation', '')[:50]}...")

    def test_lookup_with_lemma(self):
        """测试词形还原查询"""
        if not self.dict_manager.is_available():
            self.skipTest("数据库不可用")

        # 测试现在分词
        result = self.dict_manager.lookup_with_lemma("running")
        self.assertIsNotNone(result, "应该能查询到 'running' 或其原型 'run'")
        print(f"\n'running' 查询结果: {result.get('word', '')}")

        # 测试复数
        result = self.dict_manager.lookup_with_lemma("babies")
        self.assertIsNotNone(result, "应该能查询到 'babies' 或其原型 'baby'")
        print(f"'babies' 查询结果: {result.get('word', '')}")

        # 测试过去式
        result = self.dict_manager.lookup_with_lemma("walked")
        self.assertIsNotNone(result, "应该能查询到 'walked' 或其原型 'walk'")
        print(f"'walked' 查询结果: {result.get('word', '')}")

    def test_fuzzy_search(self):
        """测试模糊搜索"""
        if not self.dict_manager.is_available():
            self.skipTest("数据库不可用")

        results = self.dict_manager.fuzzy_search("hap", limit=5)
        self.assertGreater(len(results), 0, "应该能搜索到以 'hap' 开头的单词")
        words = [r['word'] for r in results]
        print(f"\n以 'hap' 开头的单词: {words}")
        self.assertIn('happy', words, "'happy' 应该在结果中")

    def test_batch_lookup(self):
        """测试批量查询"""
        if not self.dict_manager.is_available():
            self.skipTest("数据库不可用")

        words = ["cat", "dog", "running", "nonexistentword123"]
        results = self.dict_manager.batch_lookup(words)
        self.assertEqual(len(results), len(words), "结果数量应该与输入相同")

        found_count = sum(1 for _, entry in results if entry is not None)
        print(f"\n批量查询: {found_count}/{len(words)} 个单词找到")

    def test_format_html(self):
        """测试HTML格式化"""
        if not self.dict_manager.is_available():
            self.skipTest("数据库不可用")

        entry = self.dict_manager.lookup_word("test")
        if entry:
            html = self.dict_manager.format_entry_as_html(entry)
            self.assertIn('<h2', html, "应该包含标题标签")
            self.assertIn('test', html.lower(), "应该包含单词本身")
            print(f"\nHTML长度: {len(html)} 字符")

    def test_lemma_candidates(self):
        """测试词形候选生成"""
        candidates = self.dict_manager._get_lemma_candidates("running")
        self.assertIn("run", candidates, "'running' 应该生成候选 'run'")
        print(f"\n'running' 的候选词根: {candidates}")

        candidates = self.dict_manager._get_lemma_candidates("babies")
        self.assertIn("baby", candidates, "'babies' 应该生成候选 'baby'")
        print(f"'babies' 的候选词根: {candidates}")

        candidates = self.dict_manager._get_lemma_candidates("biggest")
        self.assertIn("big", candidates, "'biggest' 应该生成候选 'big'")
        print(f"'biggest' 的候选词根: {candidates}")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)

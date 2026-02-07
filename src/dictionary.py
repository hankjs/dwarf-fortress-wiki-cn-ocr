"""
英语词典查询模块（基于ECDICT）
支持词形还原和模糊匹配
"""

import os
import re
import sqlite3
from typing import List, Optional, Tuple


class DictionaryManager:
    """ECDICT词典管理器"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化词典管理器

        Args:
            db_path: ecdict.db文件路径，默认为项目根目录下的ecdict.db
        """
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            db_path = os.path.join(project_root, "stardict.db")

        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        """连接数据库"""
        if os.path.exists(self.db_path):
            try:
                self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row  # 支持字典式访问
            except Exception as e:
                print(f"词典数据库连接失败: {e}")
                self.conn = None
        else:
            print(f"词典数据库不存在: {self.db_path}")
            self.conn = None

    def is_available(self) -> bool:
        """检查词典是否可用"""
        return self.conn is not None

    def lookup_word(self, word: str) -> Optional[dict]:
        """
        精确查询单词

        Args:
            word: 要查询的单词（会自动转小写）

        Returns:
            词典条目字典，包含 word, phonetic, definition, translation 等字段
            如果没找到则返回 None
        """
        if not self.conn:
            return None

        word = word.lower().strip()
        if not word:
            return None

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM stardict WHERE word = ? LIMIT 1", (word,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            print(f"查询单词失败: {e}")
            return None

    def lookup_with_lemma(self, word: str) -> Optional[dict]:
        """
        查询单词，如果找不到则尝试查询原型

        Args:
            word: 要查询的单词

        Returns:
            词典条目字典或 None
        """
        # 先尝试精确匹配
        result = self.lookup_word(word)
        if result:
            return result

        # 尝试使用ECDICT的lemma字段查询原型
        if not self.conn:
            return None

        word = word.lower().strip()
        try:
            cursor = self.conn.cursor()
            # 查询lemma字段包含该词的词条（可能是变形）
            cursor.execute(
                "SELECT * FROM stardict WHERE word LIKE ? OR word LIKE ? LIMIT 5",
                (f"{word}%", f"{word[:-1]}%"),  # 支持running->run, goes->go等
            )
            rows = cursor.fetchall()

            # 简单的词形还原规则
            candidates = self._get_lemma_candidates(word)
            for candidate in candidates:
                for row in rows:
                    if dict(row)["word"] == candidate:
                        return dict(row)

            # 如果没有找到原型，返回第一个相似结果
            if rows:
                return dict(rows[0])

            return None
        except Exception as e:
            print(f"词形还原查询失败: {e}")
            return None

    def _get_lemma_candidates(self, word: str) -> List[str]:
        """
        根据简单规则生成可能的词根候选

        Args:
            word: 要查询的单词

        Returns:
            可能的词根列表
        """
        candidates = [word]

        # 处理复数：-s, -es, -ies
        if word.endswith("ies") and len(word) > 4:
            candidates.append(word[:-3] + "y")  # babies -> baby
        elif word.endswith("es") and len(word) > 3:
            candidates.append(word[:-2])  # boxes -> box
            candidates.append(word[:-1])  # goes -> go
        elif word.endswith("s") and len(word) > 2:
            candidates.append(word[:-1])  # cats -> cat

        # 处理过去式/分词：-ed, -ing
        if word.endswith("ed") and len(word) > 3:
            candidates.append(word[:-2])  # walked -> walk
            candidates.append(word[:-1])  # liked -> like
        elif word.endswith("ing") and len(word) > 4:
            candidates.append(word[:-3])  # walking -> walk
            if not word[:-3].endswith(("a", "e", "i", "o", "u")):
                candidates.append(word[:-4])  # running -> run

        # 处理比较级/最高级：-er, -est
        if word.endswith("est") and len(word) > 4:
            candidates.append(word[:-3])  # biggest -> big
        elif word.endswith("er") and len(word) > 3:
            candidates.append(word[:-2])  # bigger -> big

        return candidates

    def fuzzy_search(self, word: str, limit: int = 5) -> List[dict]:
        """
        模糊搜索单词（基于前缀匹配）

        Args:
            word: 要搜索的单词
            limit: 最多返回结果数

        Returns:
            词典条目字典列表
        """
        if not self.conn:
            return []

        word = word.lower().strip()
        if not word:
            return []

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM stardict WHERE word LIKE ? LIMIT ?", (f"{word}%", limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"模糊搜索失败: {e}")
            return []

    def batch_lookup(self, words: List[str]) -> List[Tuple[str, Optional[dict]]]:
        """
        批量查询单词

        Args:
            words: 单词列表

        Returns:
            [(word, dict_entry)] 列表，未找到的词条为None
        """
        results = []
        for word in words:
            entry = self.lookup_with_lemma(word)
            results.append((word, entry))
        return results

    def format_entry_as_html(self, entry: dict, word_query: str = "") -> str:
        """
        将词典条目格式化为HTML

        Args:
            entry: 词典条目字典
            word_query: 用户查询的原始单词（用于高亮显示变形）

        Returns:
            HTML格式的词典内容
        """
        if not entry:
            return "<p>未找到释义</p>"

        html_parts = []

        # 标题：单词 + 音标
        word = entry.get("word", "")
        phonetic = entry.get("phonetic", "")

        title = f"<h2 style='color: #2c3e50; margin-bottom: 10px;'>{word}"
        if word_query and word_query.lower() != word.lower():
            title += f" <span style='color: #7f8c8d; font-size: 0.8em;'>(原型: {word_query})</span>"
        title += "</h2>"
        html_parts.append(title)

        if phonetic:
            html_parts.append(
                f"<p style='color: #7f8c8d; margin: 5px 0;'>[{phonetic}]</p>"
            )

        # 翻译
        translation = entry.get("translation", "")
        if translation:
            html_parts.append("<div style='margin: 15px 0;'>")
            html_parts.append("<h3 style='color: #34495e; font-size: 1.1em;'>释义</h3>")
            # 将换行符转换为<br>，保持格式
            trans_html = translation.replace("\n", "<br>")
            html_parts.append(f"<p style='line-height: 1.6;'>{trans_html}</p>")
            html_parts.append("</div>")

        # 定义（英文）
        definition = entry.get("definition", "")
        if definition:
            html_parts.append("<div style='margin: 15px 0;'>")
            html_parts.append(
                "<h3 style='color: #34495e; font-size: 1.1em;'>Definition</h3>"
            )
            def_html = definition.replace("\n", "<br>")
            html_parts.append(
                f"<p style='line-height: 1.6; color: #555;'>{def_html}</p>"
            )
            html_parts.append("</div>")

        # 词性
        pos = entry.get("pos", "")
        if pos:
            html_parts.append(
                f"<p style='color: #7f8c8d; font-size: 0.9em;'><strong>词性:</strong> {pos}</p>"
            )

        # Collins星级
        collins = entry.get("collins", 0)
        if collins and int(collins) > 0:
            stars = "⭐" * int(collins)
            html_parts.append(
                f"<p style='color: #f39c12; font-size: 0.9em;'>柯林斯: {stars}</p>"
            )

        # 牛津3000/5000词汇标记
        oxford = entry.get("oxford", "")
        if oxford:
            html_parts.append(
                f"<p style='color: #3498db; font-size: 0.9em;'>📚 牛津词汇</p>"
            )

        # 词源
        etymology = entry.get("etymology", "")
        if etymology:
            html_parts.append(
                "<div style='margin: 15px 0; padding: 10px; background: #ecf0f1; border-radius: 5px;'>"
            )
            html_parts.append("<h3 style='color: #34495e; font-size: 1.0em;'>词源</h3>")
            html_parts.append(f"<p style='font-size: 0.9em;'>{etymology}</p>")
            html_parts.append("</div>")

        # 变形
        exchange = entry.get("exchange", "")
        if exchange:
            html_parts.append("<div style='margin: 15px 0;'>")
            html_parts.append(
                "<h3 style='color: #34495e; font-size: 1.0em;'>词形变化</h3>"
            )
            # exchange格式: "p:walked/d:walked/i:walking/3:walks"
            exchange_items = []
            for item in exchange.split("/"):
                if ":" in item:
                    key, val = item.split(":", 1)
                    label_map = {
                        "p": "过去式",
                        "d": "过去分词",
                        "i": "现在分词",
                        "3": "第三人称单数",
                        "r": "比较级",
                        "t": "最高级",
                        "s": "复数",
                        "0": "原型",
                        "1": "原型变化",
                    }
                    label = label_map.get(key, key)
                    exchange_items.append(
                        f"<span style='margin-right: 15px;'><strong>{label}:</strong> {val}</span>"
                    )
            html_parts.append(
                f"<p style='font-size: 0.9em;'>{' '.join(exchange_items)}</p>"
            )
            html_parts.append("</div>")

        return "\n".join(html_parts)

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None


# 全局单例
_dict_manager = None


def get_dictionary_manager() -> DictionaryManager:
    """获取全局词典管理器单例"""
    global _dict_manager
    if _dict_manager is None:
        _dict_manager = DictionaryManager()
    return _dict_manager

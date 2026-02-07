#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 wiki_to_html 模块
"""

import sys
import os
import unittest

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wiki_to_html import wiki_to_html


class TestWikiToHtml(unittest.TestCase):
    """测试 wiki_to_html 转换功能"""

    def test_wiki_link(self):
        """测试 Wiki 链接转换 [[Link]]"""
        content = "See [[Dwarf]] for more info"
        html, _ = wiki_to_html(content)
        self.assertIn('href="wiki:Dwarf"', html)
        self.assertIn('>Dwarf<', html)

    def test_wiki_link_with_display(self):
        """测试带显示文本的 Wiki 链接 [[Link|Display]]"""
        content = "See [[Dwarf|dwarves]] for more info"
        html, _ = wiki_to_html(content)
        self.assertIn('href="wiki:Dwarf"', html)
        self.assertIn('>dwarves<', html)

    def test_bold_text(self):
        """测试粗体文本 '''bold'''"""
        content = "This is '''bold''' text"
        html, _ = wiki_to_html(content)
        self.assertIn('<b>bold</b>', html)

    def test_code_inline(self):
        """测试行内代码 `code`"""
        content = "Use `dwarffortress.exe` to start"
        html, _ = wiki_to_html(content)
        self.assertIn('<code', html)
        self.assertIn('dwarffortress.exe', html)

    def test_external_link(self):
        """测试外部链接 [http://...]"""
        content = "Visit [http://example.com Example] for more"
        html, _ = wiki_to_html(content)
        self.assertIn('href="http://example.com"', html)
        self.assertIn('>Example<', html)

    def test_markdown_bold(self):
        """测试 Markdown 粗体 **bold**"""
        content = "This is **bold** text"
        html, _ = wiki_to_html(content)
        self.assertIn('<b>bold</b>', html)

    def test_markdown_italic(self):
        """测试 Markdown 斜体 *italic*"""
        content = "This is *italic* text"
        html, _ = wiki_to_html(content)
        self.assertIn('<i>italic</i>', html)

    def test_markdown_italic_underscore(self):
        """测试下划线斜体 _italic_"""
        content = "This is _italic_ text"
        html, _ = wiki_to_html(content)
        self.assertIn('<i>italic</i>', html)

    def test_markdown_link(self):
        """测试 Markdown 链接 [text](url)"""
        content = "Click [here](http://example.com) to visit"
        html, _ = wiki_to_html(content)
        self.assertIn('href="http://example.com"', html)
        self.assertIn('>here<', html)

    def test_h2_heading(self):
        """测试 H2 标题 ==text=="""
        content = "==Section Title=="
        html, _ = wiki_to_html(content)
        self.assertIn('<h2', html)
        self.assertIn('Section Title', html)

    def test_h3_heading(self):
        """测试 H3 标题 =text="""
        content = "=Subsection Title="
        html, _ = wiki_to_html(content)
        self.assertIn('<h3', html)
        self.assertIn('Subsection Title', html)

    def test_url_to_filename_dict(self):
        """测试返回的 URL 到文件名映射"""
        content = "[[File:example.png|200px]]"
        html, url_map = wiki_to_html(content)
        # MediaWiki 首字母大写
        self.assertIn('Example.png', url_map.values())


class TestWikiToHtmlEdgeCases(unittest.TestCase):
    """测试边界情况"""

    def test_empty_content(self):
        """测试空内容"""
        content = ""
        html, url_map = wiki_to_html(content)
        self.assertEqual(html, "")
        self.assertEqual(url_map, {})

    def test_plain_text(self):
        """测试纯文本"""
        content = "Just plain text without any markup"
        html, url_map = wiki_to_html(content)
        self.assertIn("Just plain text", html)

    def test_special_chars(self):
        """测试特殊字符转义"""
        content = "Text with <b>tags</b> & \"quotes\""
        html, _ = wiki_to_html(content)
        # HTML 标签被保护不转义，& 和 " 被转义
        self.assertIn('<b>tags</b>', html)  # 已有 HTML 标签被保护
        self.assertNotIn('"', html)  # 双引号被转义
        self.assertIn('&amp;', html)  # & 被转义


if __name__ == '__main__':
    unittest.main()

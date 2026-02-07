# -*- coding: utf-8 -*-
"""
内容显示组件
封装WikiTextBrowser，管理词典/Wiki内容的显示和语言切换
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal, QUrl
from typing import Optional, List, Tuple
import os

from result_dialog import WikiTextBrowser
from wiki_to_html import wiki_to_html
from translation import translate_content_by_vocab


class ContentDisplayWidget(QWidget):
    """内容显示组件，管理词典和Wiki内容的显示"""

    # 信号：Wiki内链被点击
    wiki_link_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 内部状态
        self._current_type = None  # 'translation', 'dict' 或 'wiki'
        self._current_lang = "en"  # 'en' 或 'cn'
        self._current_data = None  # 缓存当前显示数据

        # 依赖注入属性（由MainWindow设置）
        self.translation_map = None
        self.vocab_map = None
        self.wiki_cn_entries = []
        self.dict_manager = None

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建WikiTextBrowser
        self.browser = WikiTextBrowser()
        self.browser.setOpenLinks(False)  # 禁用自动打开链接，使用信号处理
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(self._on_anchor_clicked)

        layout.addWidget(self.browser)
        self.setLayout(layout)

    def show_translation(self, original: str, translated: str):
        """
        显示整句翻译

        Args:
            original: 原文
            translated: 译文
        """
        self._current_type = "translation"
        self._current_lang = "cn"  # 翻译默认显示中文
        self._current_data = {"original": original, "translated": translated}

        # 格式化HTML
        html = f"""
        <div style="padding: 20px;">
            <h2 style="color: #cc6600; border-bottom: 2px solid #cc6600; padding-bottom: 5px;">
                🈯 句子翻译
            </h2>
            <div style="margin-top: 20px;">
                <h3 style="color: #666;">原文：</h3>
                <p style="font-size: 14px; line-height: 1.6; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #ccc;">
                    {original}
                </p>
            </div>
            <div style="margin-top: 20px;">
                <h3 style="color: #666;">译文：</h3>
                <p style="font-size: 16px; line-height: 1.8; padding: 10px; background-color: #fff8f0; border-left: 3px solid #cc6600;">
                    {translated}
                </p>
            </div>
            <div style="margin-top: 20px; padding: 10px; background-color: #e3f2fd; border: 1px solid #90caf9; border-radius: 4px;">
                <p style="font-size: 12px; color: #1565c0; margin: 0; line-height: 1.6;">
                    💡 翻译由 <strong>MyMemory API</strong> 提供（免费额度：500次/天）<br>
                    🔖 游戏术语已自动替换为标准译名
                </p>
            </div>
        </div>
        """

        self.browser.setHtml(html)

    def show_dict_entry(self, word: str, dict_entry: dict):
        """
        显示词典词条

        Args:
            word: 单词
            dict_entry: 词典条目
        """
        self._current_type = "dict"
        self._current_lang = "en"  # 词典不支持语言切换
        self._current_data = {"word": word, "dict_entry": dict_entry}

        # 格式化HTML
        if self.dict_manager:
            # Note: format_entry_as_html expects (entry, word_query) order
            html = self.dict_manager.format_entry_as_html(dict_entry, word)
        else:
            html = f"<h2>{word}</h2><p>词典管理器未初始化</p>"

        self.browser.setHtml(html)

    def show_wiki_entry(
        self,
        entry_name: str,
        content: str,
        cn_content: str = None,
        lang: str = None
    ):
        """
        显示Wiki词条

        Args:
            entry_name: 词条名称
            content: 英文内容
            cn_content: 中文内容（可选）
            lang: 指定语言 'en' 或 'cn'（可选，默认使用当前语言）
        """
        self._current_type = "wiki"
        self._current_data = {
            "entry_name": entry_name,
            "content": content,
            "cn_content": cn_content
        }

        # 确定显示语言
        if lang:
            self._current_lang = lang
        # 如果没有真正的中文翻译且没有词汇表，强制显示英文
        has_real_cn_translation = cn_content and cn_content != content
        if not has_real_cn_translation and not self.vocab_map:
            self._current_lang = "en"

        # 选择内容
        # 检查 cn_content 是否真的是中文翻译（而不是英文 fallback）
        has_real_cn_translation = cn_content and cn_content != content

        if self._current_lang == "cn":
            if has_real_cn_translation:
                display_content = cn_content
                warning = ""
            elif self.vocab_map:
                # 使用vocabulary_map临时翻译
                display_content = translate_content_by_vocab(content, self.vocab_map)
                warning = '<p style="color: orange; font-weight: bold;">⚠️ [临时翻译] 此词条暂无人工翻译，使用词汇表自动翻译</p>'
            else:
                # 无法翻译，显示英文
                display_content = content
                warning = '<p style="color: orange; font-weight: bold;">⚠️ 此词条暂无中文翻译</p>'
                self._current_lang = "en"
        else:
            display_content = content
            warning = ""

        # 转换为HTML
        html_content, url_to_filename = wiki_to_html(display_content)

        # 设置URL映射（用于图片404降级）
        self.browser._url_to_filename = url_to_filename

        # 添加标题和警告
        full_html = f"<h1>{entry_name}</h1>{warning}{html_content}"

        self.browser.setHtml(full_html)

    def toggle_language(self):
        """切换中英文（仅对Wiki词条和翻译有效）"""
        if self._current_type == "translation":
            # 翻译类型：切换原文/译文显示
            self._current_lang = "cn" if self._current_lang == "en" else "en"
            data = self._current_data

            if self._current_lang == "en":
                # 显示原文
                html = f"""
                <div style="padding: 20px;">
                    <h2 style="color: #cc6600; border-bottom: 2px solid #cc6600; padding-bottom: 5px;">
                        🈯 句子翻译 - 原文
                    </h2>
                    <div style="margin-top: 20px;">
                        <p style="font-size: 16px; line-height: 1.8; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #ccc;">
                            {data["original"]}
                        </p>
                    </div>
                </div>
                """
            else:
                # 显示译文（完整视图）
                html = f"""
                <div style="padding: 20px;">
                    <h2 style="color: #cc6600; border-bottom: 2px solid #cc6600; padding-bottom: 5px;">
                        🈯 句子翻译
                    </h2>
                    <div style="margin-top: 15px; padding: 10px; background-color: #e3f2fd; border-left: 4px solid #2196f3;">
                        <p style="font-size: 12px; color: #1565c0; margin: 0;">
                            💡 翻译由 MyMemory API 提供，已保护游戏术语
                        </p>
                    </div>
                    <div style="margin-top: 20px;">
                        <h3 style="color: #666;">原文：</h3>
                        <p style="font-size: 14px; line-height: 1.6; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #ccc;">
                            {data["original"]}
                        </p>
                    </div>
                    <div style="margin-top: 20px;">
                        <h3 style="color: #666;">译文：</h3>
                        <p style="font-size: 16px; line-height: 1.8; padding: 10px; background-color: #fff8f0; border-left: 3px solid #cc6600;">
                            {data["translated"]}
                        </p>
                    </div>
                </div>
                """

            self.browser.setHtml(html)
            return

        if self._current_type != "wiki":
            return

        # 切换语言
        self._current_lang = "cn" if self._current_lang == "en" else "en"

        # 重新显示（使用缓存数据）
        data = self._current_data
        self.show_wiki_entry(
            data["entry_name"],
            data["content"],
            data["cn_content"],
            self._current_lang
        )

    def get_current_lang(self) -> str:
        """获取当前语言"""
        return self._current_lang

    def can_toggle_language(self) -> bool:
        """是否可以切换语言（翻译和Wiki都支持）"""
        if self._current_type == "translation":
            return True

        if self._current_type != "wiki":
            return False

        data = self._current_data
        # 检查是否有真正的中文翻译（而不是英文 fallback）
        cn_content = data.get("cn_content")
        en_content = data.get("content")
        has_real_cn = cn_content and cn_content != en_content
        has_vocab = self.vocab_map is not None and len(self.vocab_map) > 0

        return has_real_cn or has_vocab

    def clear(self):
        """清空显示"""
        self._current_type = None
        self._current_lang = "en"
        self._current_data = None
        self.browser.setHtml("")

    def _on_anchor_clicked(self, url: QUrl):
        """处理链接点击事件"""
        url_str = url.toString()

        # 外部链接 → 浏览器打开
        if url_str.startswith("http://") or url_str.startswith("https://"):
            import webbrowser
            webbrowser.open(url_str)
            return

        # Wiki内链 → 发送信号
        if url_str.startswith("wiki:"):
            target = url_str[5:]  # 去掉 "wiki:" 前缀
            self.wiki_link_clicked.emit(target)

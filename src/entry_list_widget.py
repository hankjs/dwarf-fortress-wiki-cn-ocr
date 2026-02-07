# -*- coding: utf-8 -*-
"""
词条列表组件
显示词典和Wiki词条的分组列表，管理选中状态
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt
from typing import List, Tuple


class EntryListWidget(QWidget):
    """词条列表组件，分组显示翻译、词典和Wiki词条"""

    # 信号：(index, type) type 为 "translation", "dict" 或 "wiki"
    entry_selected = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._translation_entry = None  # (原文, 译文)
        self._dict_entries = []
        self._wiki_entries = []
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 翻译区域
        self.translation_label = QLabel("🈯 翻译")
        self.translation_label.setFixedHeight(25)
        self.translation_label.setStyleSheet("""
            font-weight: bold;
            color: #cc6600;
            padding: 2px 5px;
            background-color: #fff8f0;
        """)
        layout.addWidget(self.translation_label)

        self.translation_list = QListWidget()
        self.translation_list.setFixedHeight(60)  # 固定高度，只显示一个条目
        self.translation_list.setStyleSheet("""
            QListWidget::item:selected {
                background-color: #ffe5cc;
                color: #000;
            }
            QListWidget::item:hover {
                background-color: #fff0e0;
            }
        """)
        self.translation_list.itemClicked.connect(self._on_translation_item_clicked)
        layout.addWidget(self.translation_list)

        # 分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        separator1.setFixedHeight(2)
        layout.addWidget(separator1)

        # 词典区域
        self.dict_label = QLabel("📚 字典")
        self.dict_label.setFixedHeight(25)
        self.dict_label.setStyleSheet("""
            font-weight: bold;
            color: #0066cc;
            padding: 2px 5px;
            background-color: #f0f8ff;
        """)
        layout.addWidget(self.dict_label)

        self.dict_list = QListWidget()
        self.dict_list.setStyleSheet("""
            QListWidget::item:selected {
                background-color: #cce5ff;
                color: #000;
            }
            QListWidget::item:hover {
                background-color: #e6f2ff;
            }
        """)
        self.dict_list.itemClicked.connect(self._on_dict_item_clicked)
        layout.addWidget(self.dict_list, stretch=2)  # 调整比例

        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        separator2.setFixedHeight(2)
        layout.addWidget(separator2)

        # Wiki区域
        self.wiki_label = QLabel("📖 Wiki")
        self.wiki_label.setFixedHeight(25)
        self.wiki_label.setStyleSheet("""
            font-weight: bold;
            color: #009900;
            padding: 2px 5px;
            background-color: #f0fff0;
        """)
        layout.addWidget(self.wiki_label)

        self.wiki_list = QListWidget()
        self.wiki_list.setStyleSheet("""
            QListWidget::item:selected {
                background-color: #ccffcc;
                color: #000;
            }
            QListWidget::item:hover {
                background-color: #e6ffe6;
            }
        """)
        self.wiki_list.itemClicked.connect(self._on_wiki_item_clicked)
        layout.addWidget(self.wiki_list, stretch=5)  # 调整比例

        self.setLayout(layout)

        # 初始隐藏翻译区域
        self.translation_label.hide()
        self.translation_list.hide()

    def set_entries(self, translation_entry: Tuple = None, dict_entries: List[Tuple] = None, wiki_entries: List[Tuple] = None):
        """
        设置词条列表

        Args:
            translation_entry: 翻译条目 (原文, 译文)，仅当OCR文本是多个单词时提供
            dict_entries: 词典词条列表 [(word, dict_entry), ...]
            wiki_entries: Wiki词条列表 [(entry_name, content), ...]
        """
        self._translation_entry = translation_entry
        self._dict_entries = dict_entries or []
        self._wiki_entries = wiki_entries or []

        # 清空列表
        self.translation_list.clear()
        self.dict_list.clear()
        self.wiki_list.clear()

        # 填充翻译列表
        if self._translation_entry:
            original, translated = self._translation_entry
            # 显示翻译预览（最多50字符）
            preview = translated[:50] + "..." if len(translated) > 50 else translated
            item = QListWidgetItem(f"{preview}")
            item.setData(Qt.UserRole, "translation")
            item.setToolTip(f"原文：{original}\n译文：{translated}")
            self.translation_list.addItem(item)

            self.translation_list.show()
            self.translation_label.show()
        else:
            self.translation_list.hide()
            self.translation_label.hide()

        # 填充词典列表
        if self._dict_entries:
            for word, _ in self._dict_entries:
                item = QListWidgetItem(word)
                item.setData(Qt.UserRole, "dict")
                item.setToolTip(word)  # 完整名称工具提示
                self.dict_list.addItem(item)

            self.dict_list.show()
            self.dict_label.show()
        else:
            self.dict_list.hide()
            self.dict_label.hide()

        # 填充Wiki列表
        if self._wiki_entries:
            for entry_name, _ in self._wiki_entries:
                item = QListWidgetItem(entry_name)
                item.setData(Qt.UserRole, "wiki")
                item.setToolTip(entry_name)  # 完整名称工具提示
                self.wiki_list.addItem(item)

            self.wiki_list.show()
            self.wiki_label.show()
        else:
            self.wiki_list.hide()
            self.wiki_label.hide()

    def select_first(self):
        """自动选中第一项（优先顺序：翻译 > Wiki > 字典）"""
        if self._translation_entry:
            self.translation_list.setCurrentRow(0)
            self._emit_selection(0, "translation")
        elif self._wiki_entries:
            self.wiki_list.setCurrentRow(0)
            self._emit_selection(0, "wiki")
        elif self._dict_entries:
            self.dict_list.setCurrentRow(0)
            self._emit_selection(0, "dict")

    def clear(self):
        """清空所有列表"""
        self._translation_entry = None
        self._dict_entries = []
        self._wiki_entries = []
        self.translation_list.clear()
        self.dict_list.clear()
        self.wiki_list.clear()
        self.translation_list.hide()
        self.translation_label.hide()
        self.dict_list.hide()
        self.dict_label.hide()
        self.wiki_list.hide()
        self.wiki_label.hide()

    def _on_translation_item_clicked(self, item: QListWidgetItem):
        """翻译条目被点击"""
        # 清除其他列表选中状态
        self.dict_list.clearSelection()
        self.wiki_list.clearSelection()

        # 发送选中信号
        self._emit_selection(0, "translation")

    def _on_dict_item_clicked(self, item: QListWidgetItem):
        """词典词条被点击"""
        # 清除其他列表选中状态
        self.translation_list.clearSelection()
        self.wiki_list.clearSelection()

        # 发送选中信号
        index = self.dict_list.row(item)
        self._emit_selection(index, "dict")

    def _on_wiki_item_clicked(self, item: QListWidgetItem):
        """Wiki词条被点击"""
        # 清除其他列表选中状态
        self.translation_list.clearSelection()
        self.dict_list.clearSelection()

        # 发送选中信号
        index = self.wiki_list.row(item)
        self._emit_selection(index, "wiki")

    def _emit_selection(self, index: int, entry_type: str):
        """发送选中信号"""
        self.entry_selected.emit(index, entry_type)

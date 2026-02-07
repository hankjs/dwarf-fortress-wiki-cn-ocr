"""
Windows English OCR Tool
截图后识别英文文字，弹窗显示识别结果
"""

import os
import re
import sys

import pytesseract
from PIL import Image
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

from result_dialog import ResultDialog
from screenshot import ScreenshotWindow
from dictionary import get_dictionary_manager
from entry_list_widget import EntryListWidget
from content_display_widget import ContentDisplayWidget
from translation import load_translation_map
from sentence_translator import get_sentence_translator


class TranslationWorker(QThread):
    """后台翻译线程"""

    # 信号：翻译完成 (原文, 译文)
    translation_finished = pyqtSignal(str, str)

    def __init__(self, text, translator):
        super().__init__()
        self.text = text
        self.translator = translator

    def run(self):
        """在后台线程执行翻译"""
        try:
            translated = self.translator.translate(self.text)
            if translated:
                self.translation_finished.emit(self.text, translated)
        except Exception as e:
            print(f"翻译线程错误: {e}")


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DFWiki识别")
        self.setMinimumSize(800, 600)
        # 默认置顶
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # 构建wiki索引
        self.build_wiki_index()

        # 加载翻译映射
        translation_data = load_translation_map()
        self.translation_map = translation_data.get("title_map", {})
        self.vocab_map = translation_data.get("vocabulary_map", {})

        # 初始化句子翻译器（使用词汇表作为术语字典）
        self.sentence_translator = get_sentence_translator(self.vocab_map)

        # 初始化词典管理器
        self.dict_manager = get_dictionary_manager()

        # 翻译线程
        self._translation_worker = None
        self._pending_ocr_data = None  # 等待翻译完成的 OCR 数据

        # 缓存查询结果（用于词条切换和弹窗）
        self._last_query_result = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Header区域：搜索框 + 按钮
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入wiki词条名或英文单词...")
        self.search_input.setFixedHeight(30)
        self.search_input.setStyleSheet("""
            QLineEdit {
                font-size: 12px;
                padding: 0 10px;
                border: 2px solid #ddd;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
            }
        """)
        self.search_input.returnPressed.connect(self.search_wiki)
        header_layout.addWidget(self.search_input, stretch=1)

        # 搜索按钮
        search_btn = QPushButton("搜索")
        search_btn.setFixedHeight(30)
        search_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        search_btn.clicked.connect(self.search_wiki)
        header_layout.addWidget(search_btn)

        # 识别按钮
        capture_btn = QPushButton("识别")
        capture_btn.setFixedHeight(30)
        capture_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        capture_btn.clicked.connect(self.start_capture)
        header_layout.addWidget(capture_btn)

        # 置顶按钮
        self.pin_btn = QPushButton("置顶")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(True)  # 默认置顶
        self.pin_btn.setFixedHeight(30)
        self.pin_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #e0e0e0;
                color: #333;
                padding: 0 12px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
                border: none;
            }
        """)
        self.pin_btn.clicked.connect(self.toggle_pin)
        header_layout.addWidget(self.pin_btn)

        # 语言切换按钮
        self.lang_btn = QPushButton("中/EN")
        self.lang_btn.setFixedHeight(30)
        self.lang_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #e0e0e0;
                color: #333;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #999;
            }
        """)
        self.lang_btn.setEnabled(False)
        self.lang_btn.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.lang_btn)

        # 弹窗按钮
        self.reopen_btn = QPushButton("弹窗")
        self.reopen_btn.setFixedHeight(30)
        self.reopen_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #e0e0e0;
                color: #333;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
        self.reopen_btn.clicked.connect(self.open_result_dialog)
        self.reopen_btn.hide()
        header_layout.addWidget(self.reopen_btn)

        main_layout.addLayout(header_layout)

        # Content区域：三栏布局（左侧词条列表 + 右侧内容显示）
        content_splitter = QSplitter(Qt.Horizontal)

        # 左侧：词条列表
        self.entry_list = EntryListWidget()
        self.entry_list.setFixedWidth(200)
        content_splitter.addWidget(self.entry_list)

        # 右侧：内容显示
        self.content_display = ContentDisplayWidget()
        content_splitter.addWidget(self.content_display)

        # 设置比例（左:右 = 1:4）
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 4)

        main_layout.addWidget(content_splitter)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setFixedHeight(25)
        self.status_label.setStyleSheet("""
            font-size: 12px;
            color: #666;
            padding: 0 5px;
            background-color: #f5f5f5;
            border-top: 1px solid #ddd;
        """)
        main_layout.addWidget(self.status_label)

        # 连接信号
        self.entry_list.entry_selected.connect(self.on_entry_selected)
        self.content_display.wiki_link_clicked.connect(self.on_wiki_link_clicked)

        # 注入依赖到ContentDisplayWidget
        self.content_display.translation_map = self.translation_map
        self.content_display.vocab_map = self.vocab_map
        self.content_display.dict_manager = self.dict_manager

    @staticmethod
    def _normalize(text):
        """只保留英文字母和数字并转小写，用于匹配比对"""
        return re.sub(r"[^a-zA-Z0-9]", "", text).lower()

    def build_wiki_index(self):
        """扫描wiki目录，构建词条名到文件路径的索引"""
        # 获取项目根目录（src 的父目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        wiki_dir = os.path.join(project_root, "wiki")
        self.wiki_index = {}  # {normalized_key: (display_name, file_path)}
        if not os.path.isdir(wiki_dir):
            return
        for filename in os.listdir(wiki_dir):
            if filename.endswith(".txt"):
                name = filename[:-4]
                normalized = self._normalize(name)
                if normalized:
                    self.wiki_index[normalized] = (
                        name,
                        os.path.join(wiki_dir, filename),
                    )

        # 构建中文wiki索引
        wiki_cn_dir = os.path.join(project_root, "wiki_cn")
        self.wiki_cn_index = {}  # {normalized_key: (display_name, file_path)}
        if os.path.isdir(wiki_cn_dir):
            for filename in os.listdir(wiki_cn_dir):
                if filename.endswith("-CN.txt"):
                    # 去掉 -CN 后缀获取英文名
                    name = filename[:-7]  # 去掉 -CN.txt
                    normalized = self._normalize(name)
                    if normalized:
                        self.wiki_cn_index[normalized] = (
                            name,
                            os.path.join(wiki_cn_dir, filename),
                        )

    def match_wiki_entries(self, ocr_text):
        """从OCR文本中匹配wiki词条，支持截断查询（子串匹配）"""
        matches = []
        seen = set()

        # 收集所有待匹配的片段：每行 + 每个单词
        # 遇到点号截断后面的部分（如 "Yourfirstfortress.txt" -> "Yourfirstfortress"）
        raw_candidates = []
        lines = ocr_text.strip().splitlines()
        for line in lines:
            line = line.strip()
            if line:
                raw_candidates.append(line)
        for word in ocr_text.split():
            raw_candidates.append(word)

        candidates = []
        for c in raw_candidates:
            dot_pos = c.find(".")
            if dot_pos != -1:
                candidates.append(c[:dot_pos])
            else:
                candidates.append(c)

        for candidate in candidates:
            normalized = self._normalize(candidate)
            if len(normalized) < 2:
                continue
            # 精确匹配
            if normalized in self.wiki_index and normalized not in seen:
                seen.add(normalized)
                matches.append(self.wiki_index[normalized])
            # 截断查询：OCR文本是词条名的前缀，或词条名包含OCR文本
            if len(normalized) >= 3:
                for key, value in self.wiki_index.items():
                    if key in seen:
                        continue
                    if key.startswith(normalized) or normalized in key:
                        seen.add(key)
                        matches.append(value)
        return matches

    def read_wiki_content(self, file_path, max_redirects=10):
        """读取wiki文件内容，支持多次重定向链"""
        visited = set()
        current_path = file_path
        for _ in range(max_redirects):
            with open(current_path, "r", encoding="utf-8") as f:
                content = f.read()
            redirect_match = re.match(
                r"#redirect\s*\[\[(.+?)\]\]", content, re.IGNORECASE
            )
            if not redirect_match:
                return None, content
            target = redirect_match.group(1)
            normalized = self._normalize(target)
            if normalized in visited or normalized not in self.wiki_index:
                return target, content
            visited.add(normalized)
            display_name, current_path = self.wiki_index[normalized]
        # 超过最大重定向次数，返回最后内容
        return None, content

    def toggle_pin(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def search_wiki(self):
        """从输入框搜索wiki词条和英语单词"""
        query_text = self.search_input.text().strip()
        if not query_text:
            self.status_label.setText("请输入搜索内容")
            return

        self.status_label.setText("搜索中...")
        QApplication.processEvents()

        # 1. 匹配wiki词条
        matches = self.match_wiki_entries(query_text)
        wiki_entries = []
        wiki_cn_entries = []

        if matches:
            # 读取匹配到的wiki内容（按词条名去重）
            seen_names = set()
            for display_name, file_path in matches:
                redirected_name, content = self.read_wiki_content(file_path)
                entry_name = redirected_name if redirected_name else display_name
                dedup_key = self._normalize(entry_name)
                if dedup_key in seen_names:
                    continue
                seen_names.add(dedup_key)
                wiki_entries.append((entry_name, content))
                # 查找对应的中文内容
                if dedup_key in self.wiki_cn_index:
                    cn_file_path = self.wiki_cn_index[dedup_key][1]
                    try:
                        with open(cn_file_path, "r", encoding="utf-8") as f:
                            cn_content = f.read()
                        wiki_cn_entries.append((entry_name, cn_content))
                    except Exception:
                        wiki_cn_entries.append((entry_name, content))
                else:
                    wiki_cn_entries.append((entry_name, content))

        # 2. 启动异步翻译（仅当是多个单词时）
        should_translate = (
            self.sentence_translator.is_ready()
            and self.sentence_translator.should_translate(query_text)
        )

        # 3. 查询英语词典
        dict_entries = []
        if self.dict_manager.is_available():
            # 提取查询文本中的单词
            words = re.findall(r'\b[a-zA-Z]+\b', query_text)
            seen_words = set()
            for word in words:
                word_lower = word.lower()
                if word_lower in seen_words or len(word_lower) < 2:
                    continue
                seen_words.add(word_lower)

                # 尝试查询（支持词形还原）
                entry = self.dict_manager.lookup_with_lemma(word)
                if entry:
                    dict_entries.append((word, entry))

        # 4. 先显示 Wiki 和字典结果（不等翻译）
        wiki_count = len(wiki_entries)
        dict_count = len(dict_entries)

        if not should_translate and wiki_count == 0 and dict_count == 0:
            self.status_label.setText("未找到匹配结果")
            return

        # 4.1 缓存结果（翻译稍后异步添加）
        self._last_query_result = {
            "query": query_text,
            "translation_entry": None,  # 翻译完成后更新
            "dict_entries": dict_entries,
            "wiki_entries": wiki_entries,
            "wiki_cn_entries": wiki_cn_entries,
        }

        # 4.2 注入中文内容到 ContentDisplayWidget
        self.content_display.wiki_cn_entries = wiki_cn_entries

        # 4.3 填充左侧列表（暂不包含翻译）
        self.entry_list.set_entries(None, dict_entries, wiki_entries)
        self.entry_list.select_first()

        # 4.4 显示"弹窗"按钮
        self.reopen_btn.show()

        # 4.5 更新状态标签
        status_parts = []
        if should_translate:
            status_parts.append("翻译中...")
        if wiki_count > 0:
            status_parts.append(f"{wiki_count} 条 Wiki")
        if dict_count > 0:
            status_parts.append(f"{dict_count} 个单词")
        self.status_label.setText(f"找到 {' + '.join(status_parts)}")

        # 4.6 启动后台翻译
        if should_translate:
            self._start_translation(query_text)

    def on_entry_selected(self, index: int, entry_type: str):
        """词条选中事件"""
        if not self._last_query_result:
            return

        try:
            if entry_type == "translation":
                # 显示翻译
                translation_entry = self._last_query_result.get("translation_entry")
                if not translation_entry:
                    return

                original, translated = translation_entry
                self.content_display.show_translation(original, translated)
                self.lang_btn.setEnabled(True)  # 翻译支持切换原文/译文

            elif entry_type == "dict":
                # 显示词典词条
                dict_entries = self._last_query_result["dict_entries"]
                if index >= len(dict_entries):
                    return

                word, dict_entry = dict_entries[index]
                self.content_display.show_dict_entry(word, dict_entry)
                self.lang_btn.setEnabled(False)  # 词典不支持语言切换

            elif entry_type == "wiki":
                # 显示Wiki词条
                wiki_entries = self._last_query_result["wiki_entries"]
                wiki_cn_entries = self._last_query_result.get("wiki_cn_entries", [])

                if index >= len(wiki_entries):
                    return

                entry_name, content = wiki_entries[index]
                cn_content = None
                if wiki_cn_entries and index < len(wiki_cn_entries):
                    cn_content = wiki_cn_entries[index][1]

                self.content_display.show_wiki_entry(entry_name, content, cn_content)

                # 根据是否有中文内容决定是否启用语言切换
                has_cn = self.content_display.can_toggle_language()
                self.lang_btn.setEnabled(has_cn)

        except Exception as e:
            self.status_label.setText(f"显示词条出错: {str(e)}")

    def toggle_language(self):
        """切换中英文"""
        self.content_display.toggle_language()

    def _start_translation(self, text: str):
        """启动后台翻译"""
        # 停止之前的翻译线程
        if self._translation_worker and self._translation_worker.isRunning():
            self._translation_worker.quit()
            self._translation_worker.wait()

        # 创建新的翻译线程
        self._translation_worker = TranslationWorker(text, self.sentence_translator)
        self._translation_worker.translation_finished.connect(self._on_translation_finished)
        self._translation_worker.start()

    def _on_translation_finished(self, original: str, translated: str):
        """翻译完成回调"""
        # 检查是否还是当前查询
        if not self._last_query_result or self._last_query_result["query"] != original:
            return

        # 更新翻译结果
        translation_entry = (original, translated)
        self._last_query_result["translation_entry"] = translation_entry

        # 获取当前的词典和 Wiki 结果
        dict_entries = self._last_query_result.get("dict_entries", [])
        wiki_entries = self._last_query_result.get("wiki_entries", [])

        # 更新左侧列表（添加翻译）
        self.entry_list.set_entries(translation_entry, dict_entries, wiki_entries)

        # 如果当前没有选中任何条目，自动选中翻译
        # （优先显示刚完成的翻译）
        if self.entry_list._translation_entry:
            self.entry_list.select_first()

        # 更新状态标签
        status_parts = ["整句翻译"]
        wiki_count = len(wiki_entries)
        dict_count = len(dict_entries)
        if wiki_count > 0:
            status_parts.append(f"{wiki_count} 条 Wiki")
        if dict_count > 0:
            status_parts.append(f"{dict_count} 个单词")
        self.status_label.setText(f"识别到 {' + '.join(status_parts)}!")

    def on_wiki_link_clicked(self, target: str):
        """Wiki内链点击处理（弹出ResultDialog）"""
        normalized = self._normalize(target)
        if normalized not in self.wiki_index:
            return

        display_name, file_path = self.wiki_index[normalized]
        redirected_name, content = self.read_wiki_content(file_path)
        entry_name = redirected_name if redirected_name else display_name

        # 查找中文内容
        wiki_cn_entries = None
        if self.wiki_cn_index and normalized in self.wiki_cn_index:
            cn_file_path = self.wiki_cn_index[normalized][1]
            try:
                with open(cn_file_path, "r", encoding="utf-8") as f:
                    cn_content = f.read()
                wiki_cn_entries = [(entry_name, cn_content)]
            except Exception:
                wiki_cn_entries = [(entry_name, content)]

        # 弹出ResultDialog
        dialog = ResultDialog(
            "",
            self,
            wiki_entries=[(entry_name, content)],
            wiki_cn_entries=wiki_cn_entries,
            wiki_index=self.wiki_index,
            wiki_cn_index=self.wiki_cn_index,
            read_wiki_func=self.read_wiki_content,
        )
        dialog.show()

    def open_result_dialog(self):
        """打开ResultDialog（使用缓存的查询结果）"""
        if not self._last_query_result:
            return

        result = self._last_query_result
        dialog = ResultDialog(
            result["query"],
            self,
            wiki_entries=result["wiki_entries"],
            wiki_cn_entries=result["wiki_cn_entries"],
            dict_entries=result["dict_entries"],
            wiki_index=self.wiki_index,
            wiki_cn_index=self.wiki_cn_index,
            read_wiki_func=self.read_wiki_content,
            dict_manager=self.dict_manager,
        )
        dialog.show()

    def start_capture(self):
        self.hide()
        # 稍微延迟以确保主窗口隐藏
        QApplication.processEvents()

        self.screenshot_window = ScreenshotWindow(
            self.process_screenshot, cancel_callback=self.show
        )
        self.screenshot_window.show()

    def process_screenshot(self, pixmap):
        """处理截图并进行OCR"""
        self.show()

        # 将QPixmap转换为PIL Image
        image = pixmap.toImage()
        buffer = image.bits().asstring(image.sizeInBytes())
        pil_image = Image.frombuffer(
            "RGBA", (image.width(), image.height()), buffer, "raw", "BGRA", 0, 1
        )

        # 转换为RGB模式（Tesseract需要）
        pil_image = pil_image.convert("RGB")

        # 执行OCR
        try:
            self.status_label.setText("识别中...")
            QApplication.processEvents()

            # 使用Tesseract进行英文OCR
            text = pytesseract.image_to_string(pil_image, lang="eng")
            text = text.strip()

            # 智能处理点号：
            # - 单个单词（如 "Fortress.txt"）→ 删除 . 后面（文件名）
            # - 多个单词（如 "He strikes. He wins."）→ 保留完整（句子）
            if "." in text:
                # 获取第一个点号前的文本
                before_dot = text.split(".")[0].strip()
                # 统计点号前有多少个单词
                words = re.findall(r'\b[a-zA-Z]+\b', before_dot)
                if len(words) == 1:
                    # 只有一个单词，是文件名，删除点号后面的内容
                    text = before_dot
                # 否则是句子，保留完整文本

            if not text:
                self.status_label.setText("未识别到文字")
                return

            # 1. 匹配wiki词条
            matches = self.match_wiki_entries(text)
            wiki_entries = []
            wiki_cn_entries = []

            if matches:
                # 读取匹配到的wiki内容（按词条名去重）
                seen_names = set()
                for display_name, file_path in matches:
                    redirected_name, content = self.read_wiki_content(file_path)
                    entry_name = redirected_name if redirected_name else display_name
                    dedup_key = self._normalize(entry_name)
                    if dedup_key in seen_names:
                        continue
                    seen_names.add(dedup_key)
                    wiki_entries.append((entry_name, content))
                    # 查找对应的中文内容
                    if dedup_key in self.wiki_cn_index:
                        cn_file_path = self.wiki_cn_index[dedup_key][1]
                        try:
                            with open(cn_file_path, "r", encoding="utf-8") as f:
                                cn_content = f.read()
                            wiki_cn_entries.append((entry_name, cn_content))
                        except Exception:
                            wiki_cn_entries.append((entry_name, content))
                    else:
                        wiki_cn_entries.append((entry_name, content))

            # 2. 启动异步翻译（仅当是多个单词时）
            should_translate = (
                self.sentence_translator.is_ready()
                and self.sentence_translator.should_translate(text)
            )

            # 3. 查询英语词典
            dict_entries = []
            if self.dict_manager.is_available():
                # 提取OCR文本中的单词
                words = re.findall(r'\b[a-zA-Z]+\b', text)
                seen_words = set()
                for word in words:
                    word_lower = word.lower()
                    if word_lower in seen_words or len(word_lower) < 2:
                        continue
                    seen_words.add(word_lower)

                    # 尝试查询（支持词形还原）
                    entry = self.dict_manager.lookup_with_lemma(word)
                    if entry:
                        dict_entries.append((word, entry))

            # 4. 先显示 Wiki 和字典结果（不等翻译）
            wiki_count = len(wiki_entries)
            dict_count = len(dict_entries)

            if not should_translate and wiki_count == 0 and dict_count == 0:
                self.status_label.setText(f"识别成功「{text}」，但未找到匹配词条")
                return

            # 4.1 缓存结果（翻译稍后异步添加）
            self._last_query_result = {
                "query": text,
                "translation_entry": None,  # 翻译完成后更新
                "dict_entries": dict_entries,
                "wiki_entries": wiki_entries,
                "wiki_cn_entries": wiki_cn_entries,
            }

            # 4.2 注入中文内容到 ContentDisplayWidget
            self.content_display.wiki_cn_entries = wiki_cn_entries

            # 4.3 填充左侧列表（暂不包含翻译）
            self.entry_list.set_entries(None, dict_entries, wiki_entries)
            self.entry_list.select_first()

            # 4.4 显示"弹窗"按钮
            self.reopen_btn.show()

            # 4.5 更新状态标签
            status_parts = []
            if should_translate:
                status_parts.append("翻译中...")
            if wiki_count > 0:
                status_parts.append(f"{wiki_count} 条 Wiki")
            if dict_count > 0:
                status_parts.append(f"{dict_count} 个单词")
            self.status_label.setText(f"识别到 {' + '.join(status_parts)}!")

            # 4.6 启动后台翻译
            if should_translate:
                self._start_translation(text)

        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")


def main():
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

"""
Windows English OCR Tool
截图后识别英文文字，弹窗显示识别结果
"""

import os
import re
import sys

import pytesseract
from PIL import Image
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from result_dialog import ResultDialog
from screenshot import ScreenshotWindow
from dictionary import get_dictionary_manager


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DFWiki识别")
        self.setMinimumSize(300, 150)
        # 默认置顶
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # 构建wiki索引
        self.build_wiki_index()

        # 初始化词典管理器
        self.dict_manager = get_dictionary_manager()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 第一行：置顶 + 重新打开 + 识别按钮
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

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
        top_layout.addWidget(self.pin_btn)

        self.reopen_btn = QPushButton("重新打开")
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
        self.reopen_btn.clicked.connect(self.reopen_result)
        self.reopen_btn.hide()
        top_layout.addWidget(self.reopen_btn)

        top_layout.addStretch()

        # 截图识别按钮
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
        top_layout.addWidget(capture_btn)

        layout.addWidget(top_widget)

        # 第二行：输入框 + 搜索按钮
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(6)

        # 输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入wiki词条名...")
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
        search_layout.addWidget(self.search_input, stretch=1)

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
        search_layout.addWidget(search_btn)

        layout.addWidget(search_widget)

        # 第三行：状态标签
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(self.status_label)

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

        # 2. 查询英语词典
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

        # 3. 显示结果
        wiki_count = len(wiki_entries)
        dict_count = len(dict_entries)

        if wiki_count == 0 and dict_count == 0:
            self.status_label.setText("未找到匹配结果")
            return

        # 构建状态信息
        status_parts = []
        if wiki_count > 0:
            status_parts.append(f"{wiki_count} 条 Wiki")
        if dict_count > 0:
            status_parts.append(f"{dict_count} 个单词")
        self.status_label.setText(f"找到 {' + '.join(status_parts)}!")

        # 打开结果对话框
        dialog = ResultDialog(
            query_text,
            self,
            wiki_entries=wiki_entries,
            wiki_cn_entries=wiki_cn_entries if self.wiki_cn_index else None,
            dict_entries=dict_entries,
            wiki_index=self.wiki_index,
            wiki_cn_index=self.wiki_cn_index,
            read_wiki_func=self.read_wiki_content,
            dict_manager=self.dict_manager,
        )
        self._result_dialog = dialog
        self.reopen_btn.show()
        dialog.show()

    def reopen_result(self):
        if hasattr(self, "_result_dialog") and self._result_dialog:
            self._result_dialog.show()
            self._result_dialog.raise_()

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
            self.status_label.setText("Processing...")
            QApplication.processEvents()

            # 使用Tesseract进行英文OCR
            text = pytesseract.image_to_string(pil_image, lang="eng")
            text = text.strip()

            if text:
                # 匹配wiki词条
                matches = self.match_wiki_entries(text)
                if matches:
                    # 读取匹配到的wiki内容（按词条名去重）
                    wiki_entries = []
                    wiki_cn_entries = []
                    seen_names = set()
                    for display_name, file_path in matches:
                        redirected_name, content = self.read_wiki_content(file_path)
                        entry_name = (
                            redirected_name if redirected_name else display_name
                        )
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
                    self.status_label.setText(f"识别到 {len(wiki_entries)} 条 wiki!")
                    dialog = ResultDialog(
                        text,
                        self,
                        wiki_entries=wiki_entries,
                        wiki_cn_entries=wiki_cn_entries if self.wiki_cn_index else None,
                        wiki_index=self.wiki_index,
                        wiki_cn_index=self.wiki_cn_index,
                        read_wiki_func=self.read_wiki_content,
                    )
                else:
                    self.status_label.setText("识别成功")
                    dialog = ResultDialog(
                        text,
                        self,
                        wiki_index=self.wiki_index,
                        wiki_cn_index=self.wiki_cn_index,
                        read_wiki_func=self.read_wiki_content,
                    )
                self._result_dialog = dialog
                self.reopen_btn.show()
                dialog.show()
            else:
                self.status_label.setText("未识别到文字")

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

"""
Windows English OCR Tool
截图后识别英文文字，弹窗显示识别结果
"""

import hashlib
import os
import re
import sys
import urllib.request
import webbrowser

import pytesseract
from PIL import Image, ImageGrab
from PyQt5.QtCore import QPoint, QRect, Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPixmap, QScreen
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QRubberBand,
    QScrollArea,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ScreenshotWindow(QWidget):
    """全屏截图选择窗口"""

    def __init__(self, callback, cancel_callback=None):
        super().__init__()
        self.callback = callback
        self.cancel_callback = cancel_callback
        self.start_pos = None
        self.end_pos = None
        self.rubber_band = None

        # 设置全屏透明窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        self.setCursor(Qt.CrossCursor)

        # 获取整个屏幕
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.setGeometry(screen_geometry)

        # 截取整个屏幕作为背景
        self.screenshot = screen.grabWindow(0)

        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)

    def paintEvent(self, event):
        painter = QPainter(self)
        # 绘制半透明背景
        painter.drawPixmap(0, 0, self.screenshot)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.rubber_band.setGeometry(QRect(self.start_pos, self.start_pos))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.rubber_band.setGeometry(
                QRect(self.start_pos, event.pos()).normalized()
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos:
            self.end_pos = event.pos()
            rect = QRect(self.start_pos, self.end_pos).normalized()

            if rect.width() > 10 and rect.height() > 10:
                # 截取选中区域
                cropped = self.screenshot.copy(rect)
                self.callback(cropped)

            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.cancel_callback:
                self.cancel_callback()
            self.close()


class ImageDownloader(QThread):
    """后台下载图片的线程"""

    finished = pyqtSignal(str, bytes)  # url, data

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(
                self.url, headers={"User-Agent": "Mozilla/5.0"}
            )
            data = urllib.request.urlopen(req, timeout=10).read()
            self.finished.emit(self.url, data)
        except Exception:
            self.finished.emit(self.url, b"")


# 全局图片缓存，所有窗口共享
_image_cache = {}


class WikiTextBrowser(QTextBrowser):
    """支持异步加载远程图片的QTextBrowser"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._downloaders = []

    def loadResource(self, type, url):
        if type == 2:  # QTextDocument.ImageResource
            url_str = url.toString()
            if url_str in _image_cache:
                return _image_cache[url_str]
            if url_str.startswith("http") and url_str not in _image_cache:
                _image_cache[url_str] = None  # 标记为下载中
                downloader = ImageDownloader(url_str, self)
                downloader.finished.connect(self._on_image_downloaded)
                self._downloaders.append(downloader)
                downloader.start()
                return QPixmap()  # 返回空占位
        return super().loadResource(type, url)

    def _on_image_downloaded(self, url_str, data):
        if data:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                _image_cache[url_str] = pixmap
                self.document().addResource(2, QUrl(url_str), pixmap)
                # 刷新显示
                self.setHtml(self.toHtml())


class ResultDialog(QDialog):
    """OCR结果显示弹窗"""

    def __init__(
        self,
        text,
        parent=None,
        wiki_entries=None,
        wiki_index=None,
        read_wiki_func=None,
        wiki_cn_entries=None,
        wiki_cn_index=None,
    ):
        super().__init__(parent)
        self.setMinimumSize(600, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setModal(False)
        self.ocr_text = text
        self.wiki_entries = wiki_entries or []
        self.wiki_cn_entries = wiki_cn_entries or []
        self.wiki_index = wiki_index or {}
        self.wiki_cn_index = wiki_cn_index or {}
        self.read_wiki_func = read_wiki_func
        self.current_entry_index = 0
        self.entry_buttons = []
        self._child_dialogs = []
        self.current_lang = "en"  # 'en' 或 'cn'

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # 最顶部：OCR文本和语言切换按钮在同一行
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        ocr_label = QLabel(text)
        ocr_label.setWordWrap(True)
        ocr_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        ocr_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                padding: 6px 10px;
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #333;
            }
        """)
        top_layout.addWidget(ocr_label, 1)  # stretch=1，占据剩余空间

        # 语言切换按钮（根据当前词条是否有中文动态显示）
        self.lang_btn = QPushButton("中/EN")
        self.lang_btn.setFixedHeight(25)
        self.lang_btn.setFixedWidth(50)
        self.lang_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; border: 1px solid #ccc; border-radius: 3px;
                background-color: #2196F3; color: white;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.lang_btn.clicked.connect(self.toggle_language)
        top_layout.addWidget(self.lang_btn)

        layout.addLayout(top_layout)

        if self.wiki_entries:
            self.setWindowTitle(f"Wiki Match ({len(self.wiki_entries)} entries)")

            # 顶部词条按钮列表（可滚动）
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(36)
            scroll.setStyleSheet("QScrollArea { border: none; }")
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            btn_container = QWidget()
            self.entry_btn_layout = QHBoxLayout(btn_container)
            self.entry_btn_layout.setContentsMargins(2, 2, 2, 2)
            self.entry_btn_layout.setSpacing(4)
            for i, (entry_name, _content) in enumerate(self.wiki_entries):
                btn = QPushButton(entry_name.replace("_", " "))
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(self._entry_btn_style(selected=(i == 0)))
                btn.clicked.connect(lambda checked, idx=i: self.switch_entry(idx))
                self.entry_btn_layout.addWidget(btn)
                self.entry_buttons.append(btn)
            self.entry_btn_layout.addStretch()
            scroll.setWidget(btn_container)
            layout.addWidget(scroll)

        # 内容区域
        self.text_browser = WikiTextBrowser()
        self.text_browser.setOpenLinks(False)
        self.text_browser.anchorClicked.connect(self.on_wiki_link_clicked)
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                font-size: 14px;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.text_browser)

        if self.wiki_entries:
            self._show_entry(0)
        else:
            self.setWindowTitle("识别结果")
            self.text_browser.setText(text)
            self.lang_btn.hide()  # 没有匹配到词条时隐藏语言切换按钮

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self.pin_btn = QPushButton("置顶")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(True)
        self.pin_btn.setFixedSize(40, 25)
        self.pin_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; border: 1px solid #ccc; border-radius: 3px;
                background-color: #e0e0e0; color: #333;
            }
            QPushButton:checked {
                background-color: #4CAF50; color: white; border: none;
            }
        """)
        self.pin_btn.clicked.connect(self.toggle_pin)
        btn_layout.addWidget(self.pin_btn)

        copy_btn = QPushButton("复制识别文本")
        copy_btn.setFixedHeight(25)
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)

        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(25)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    @staticmethod
    def _entry_btn_style(selected=False):
        if selected:
            return """
                QPushButton {
                    font-size: 12px; padding: 4px 10px;
                    background-color: #4CAF50; color: white;
                    border: none; border-radius: 3px;
                }
            """
        return """
            QPushButton {
                font-size: 12px; padding: 4px 10px;
                background-color: #e0e0e0; color: #333;
                border: none; border-radius: 3px;
            }
            QPushButton:hover { background-color: #c0c0c0; }
        """

    @staticmethod
    def _wiki_to_html(content):
        """将wiki格式内容转为HTML，[[link]] 变为可点击链接，[[File:...]] 变为图片"""
        import html

        # 先提取 [[File:...]] 替换为占位符（避免被 html.escape 和后续正则干扰）
        file_placeholders = {}

        def replace_file(m):
            parts = m.group(1).split("|")
            filename = parts[0].replace(" ", "_")
            # MediaWiki 首字母大写
            if filename:
                filename = filename[0].upper() + filename[1:]
            # 解析宽度参数
            width = ""
            for p in parts[1:]:
                p = p.strip()
                if p.endswith("px") and p[:-2].isdigit():
                    width = p[:-2]
            # 基于MD5哈希构造真实图片URL
            h = hashlib.md5(filename.encode()).hexdigest()
            base = f"https://dwarffortresswiki.org/images"
            # 始终使用原始图片URL，用HTML width属性控制显示大小
            # (缩略图路径/thumb/对某些图片不存在，会返回404)
            img_url = f"{base}/{h[0]}/{h[:2]}/{filename}"
            w_attr = f' width="{width}"' if width else ""
            placeholder = f"__FILE_PLACEHOLDER_{len(file_placeholders)}__"
            file_placeholders[placeholder] = f'<br><img src="{img_url}"{w_attr}><br>'
            return placeholder

        content = re.sub(
            r"\[\[File:([^\]]+)\]\]", replace_file, content, flags=re.IGNORECASE
        )

        content = html.escape(content)

        # 还原图片占位符
        for placeholder, img_html in file_placeholders.items():
            content = content.replace(placeholder, img_html)

        # [[display|link]] 格式
        content = re.sub(
            r"\[\[([^\]|]+)\|([^\]]+)\]\]",
            r'<a href="wiki:\1" style="color:#1a73e8;text-decoration:none;">\2</a>',
            content,
        )
        # [[link]] 格式
        content = re.sub(
            r"\[\[([^\]]+)\]\]",
            r'<a href="wiki:\1" style="color:#1a73e8;text-decoration:none;">\1</a>',
            content,
        )
        # '''bold''' 格式
        content = re.sub(
            r"&#x27;&#x27;&#x27;(.+?)&#x27;&#x27;&#x27;", r"<b>\1</b>", content
        )
        # 保留换行
        content = content.replace("\n", "<br>")
        return content

    def _has_cn_content(self, index):
        """判断指定索引的词条是否有中文内容"""
        if not self.wiki_cn_entries or index >= len(self.wiki_cn_entries):
            return False
        # 获取英文内容作为对比
        en_content = (
            self.wiki_entries[index][1] if index < len(self.wiki_entries) else ""
        )
        cn_content = self.wiki_cn_entries[index][1]
        # 如果中文内容与英文内容不同，则认为有中文
        return cn_content != en_content

    def _show_entry(self, index):
        # 根据当前词条是否有中文来显示/隐藏语言切换按钮
        has_cn = self._has_cn_content(index)
        self.lang_btn.setVisible(has_cn)
        # 如果当前是中文模式但没有中文内容，自动切回英文
        if self.current_lang == "cn" and not has_cn:
            self.current_lang = "en"

        if self.current_lang == "cn" and has_cn:
            entry_name, content = self.wiki_cn_entries[index]
        else:
            entry_name, content = self.wiki_entries[index]
        html_content = self._wiki_to_html(content)
        self.text_browser.setHtml(html_content)
        self.text_browser.moveCursor(self.text_browser.textCursor().Start)
        self.setWindowTitle(f"Wiki: {entry_name.replace('_', ' ')}")

    def switch_entry(self, index):
        # 更新按钮样式
        for i, btn in enumerate(self.entry_buttons):
            btn.setStyleSheet(self._entry_btn_style(selected=(i == index)))
        self.current_entry_index = index
        self._show_entry(index)

    def toggle_language(self):
        """切换中英文显示"""
        if self.current_lang == "en":
            self.current_lang = "cn"
        else:
            self.current_lang = "en"
        self._show_entry(self.current_entry_index)

    def toggle_pin(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def on_wiki_link_clicked(self, url):
        """点击wiki内链时弹出新窗口展示对应词条"""
        scheme = url.scheme()
        if scheme != "wiki":
            return
        target = url.path() or url.toString().replace("wiki:", "", 1)
        normalized = re.sub(r"[^a-zA-Z0-9]", "", target).lower()
        if normalized not in self.wiki_index:
            return
        display_name, file_path = self.wiki_index[normalized]
        if self.read_wiki_func:
            redirected_name, content = self.read_wiki_func(file_path)
            entry_name = redirected_name if redirected_name else display_name
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            entry_name = display_name

        # 准备中文内容
        wiki_cn_entries = None
        if self.wiki_cn_index and normalized in self.wiki_cn_index:
            cn_file_path = self.wiki_cn_index[normalized][1]
            try:
                with open(cn_file_path, "r", encoding="utf-8") as f:
                    cn_content = f.read()
                wiki_cn_entries = [(entry_name, cn_content)]
            except Exception:
                wiki_cn_entries = [(entry_name, content)]

        dialog = ResultDialog(
            "",
            self,
            wiki_entries=[(entry_name, content)],
            wiki_cn_entries=wiki_cn_entries,
            wiki_index=self.wiki_index,
            wiki_cn_index=self.wiki_cn_index,
            read_wiki_func=self.read_wiki_func,
        )
        self._child_dialogs.append(dialog)
        dialog.show()

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.ocr_text)

    def open_wiki(self):
        if self.wiki_entries:
            entry_name = self.wiki_entries[self.current_entry_index][0]
            url = f"https://dwarffortresswiki.org/index.php/{entry_name}"
            webbrowser.open(url)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DFWiki识别")
        self.setMinimumSize(300, 150)

        # 构建wiki索引
        self.build_wiki_index()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 截图按钮
        capture_btn = QPushButton("截图并识别词条")
        capture_btn.setMinimumHeight(50)
        capture_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(capture_btn)

        pin_widget = QWidget()
        pin_widget.setFixedHeight(30)
        pin_layout = QHBoxLayout(pin_widget)
        pin_layout.setContentsMargins(0, 0, 0, 0)
        pin_layout.setSpacing(4)

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.pin_btn = QPushButton("置顶")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setFixedSize(40, 25)
        self.pin_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px; border: 1px solid #ccc; border-radius: 3px;
                background-color: #e0e0e0; color: #333;
            }
            QPushButton:checked {
                background-color: #4CAF50; color: white; border: none;
            }
        """)
        self.pin_btn.clicked.connect(self.toggle_pin)
        pin_layout.addWidget(self.pin_btn)

        self.reopen_btn = QPushButton("重新打开")
        self.reopen_btn.setFixedHeight(25)
        self.reopen_btn.setFixedWidth(self.reopen_btn.sizeHint().width())
        self.reopen_btn.clicked.connect(self.reopen_result)
        self.reopen_btn.hide()
        pin_layout.addWidget(self.reopen_btn)

        pin_layout.addWidget(self.status_label)
        layout.addWidget(pin_widget)

    @staticmethod
    def _normalize(text):
        """只保留英文字母和数字并转小写，用于匹配比对"""
        return re.sub(r"[^a-zA-Z0-9]", "", text).lower()

    def build_wiki_index(self):
        """扫描wiki目录，构建词条名到文件路径的索引"""
        wiki_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki")
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
        wiki_cn_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "wiki_cn"
        )
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

"""
结果显示对话框模块
包括 Wiki 内容浏览器和图片异步加载功能
"""

import json
import re
import urllib.request
import webbrowser

from PyQt5.QtCore import QThread, QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from translation import load_translation_map, translate_content_by_vocab
from wiki_to_html import wiki_to_html


# 全局图片缓存，所有窗口共享
_image_cache = {}


class ImageUrlResolver(QThread):
    """后台解析图片真实URL的线程（处理Wikimedia Commons等外部图片）"""

    finished = pyqtSignal(str, str)  # original_url, resolved_url

    def __init__(self, filename, parent=None):
        super().__init__(parent)
        # filename 已经是 MediaWiki 格式（空格转为下划线，首字母大写）
        self.filename = filename

    def run(self):
        """查询 MediaWiki API 获取真实图片 URL"""
        try:
            # 使用 MediaWiki API 查询图片信息
            # filename 中可能包含引号等特殊字符，需要 URL 编码
            from urllib.parse import quote

            encoded_name = quote(self.filename)
            api_url = f"https://dwarffortresswiki.org/api.php?action=query&titles=File:{encoded_name}&prop=imageinfo&iiprop=url&format=json"

            print(f"[DEBUG] 查询API: {api_url}")
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())

            # 解析 API 响应
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                imageinfo = page_info.get("imageinfo", [])
                if imageinfo:
                    real_url = imageinfo[0].get("url", "")
                    if real_url:
                        print(f"[DEBUG] 解析到真实URL: {real_url}")
                        self.finished.emit(self.filename, real_url)
                        return

            # 如果 API 没有返回 URL，使用本地构造的 URL
            print(f"[DEBUG] API未返回URL，使用本地URL")
            self.finished.emit(self.filename, "")
        except Exception as e:
            print(f"[DEBUG] 解析URL失败: {e}")
            self.finished.emit(self.filename, "")


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
            # 增加超时时间，SSL 握手可能需要更长时间
            data = urllib.request.urlopen(req, timeout=30).read()
            print(f"[DEBUG] 下载成功: {self.url}, 大小: {len(data)} bytes")
            self.finished.emit(self.url, data)
        except Exception as e:
            print(f"[DEBUG] 下载失败: {self.url}, 错误: {e}")
            self.finished.emit(self.url, b"")


class WikiTextBrowser(QTextBrowser):
    """支持异步加载远程图片的QTextBrowser"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._downloaders = []
        self._url_resolvers = []
        # 存储原始URL到文件名的映射，用于404后解析
        self._url_to_filename = {}
        self._pending_resolved_urls = {}  # 解析后的真实URL -> 原URL

    def loadResource(self, type, url):
        if type == 2:  # QTextDocument.ImageResource
            url_str = url.toString()
            if url_str in _image_cache:
                cached = _image_cache[url_str]
                if cached is None:
                    return QPixmap()
                print(f"[DEBUG] 使用缓存图片: {url_str}")
                return cached
            if url_str.startswith("http") and url_str not in _image_cache:
                _image_cache[url_str] = None  # 标记为下载中
                downloader = ImageDownloader(url_str, self)
                downloader.finished.connect(self._on_image_downloaded)
                self._downloaders.append(downloader)
                downloader.start()
                return QPixmap()  # 返回空占位
        return super().loadResource(type, url)

    def _on_image_downloaded(self, url_str, data):
        print(f"[DEBUG] 图片下载完成: {url_str}, 数据大小: {len(data)} bytes")
        if data:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                print(
                    f"[DEBUG] 图片加载成功: {url_str}, 尺寸: {pixmap.width()}x{pixmap.height()}"
                )
                _image_cache[url_str] = pixmap
                self.document().addResource(2, QUrl(url_str), pixmap)
                # 刷新显示
                self.setHtml(self.toHtml())
            else:
                print(f"[DEBUG] 图片加载失败 (pixmap.isNull()): {url_str}")
        else:
            print(f"[DEBUG] 图片下载失败 (无数据): {url_str}")
            # 下载失败，尝试通过 API 解析真实 URL（可能是 Wikimedia Commons 图片）
            if url_str in self._url_to_filename:
                filename = self._url_to_filename[url_str]
                print(f"[DEBUG] 尝试解析真实URL: {filename}")
                resolver = ImageUrlResolver(filename, self)
                resolver.finished.connect(self._on_url_resolved)
                self._url_resolvers.append(resolver)
                resolver.start()

    def _on_url_resolved(self, filename, real_url):
        """当通过 API 解析到真实 URL 后的回调"""
        if real_url:
            # 找到原 URL（用于文档资源）
            original_url = None
            for url, fn in self._url_to_filename.items():
                if fn == filename:
                    original_url = url
                    break
            if original_url:
                self._pending_resolved_urls[real_url] = original_url
            # 更新缓存和下载
            _image_cache[real_url] = None
            downloader = ImageDownloader(real_url, self)
            # 注意：finished 信号是 (url, data) 顺序
            downloader.finished.connect(
                lambda url, data, orig=original_url: self._on_real_image_downloaded(
                    url, data, orig
                )
            )
            self._downloaders.append(downloader)
            downloader.start()

    def _on_real_image_downloaded(self, url_str, data, original_url=None):
        """从真实 URL 下载完成后的回调"""
        if data:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                # 同时缓存到真实 URL 和原 URL
                _image_cache[url_str] = pixmap
                if original_url:
                    _image_cache[original_url] = pixmap
                    # 使用原 URL 注册资源，这样 HTML 中的 img src 才能匹配
                    self.document().addResource(2, QUrl(original_url), pixmap)
                else:
                    self.document().addResource(2, QUrl(url_str), pixmap)
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

        # 加载翻译映射表
        self.translation_map = load_translation_map()
        self.vocab_map = self.translation_map.get("vocabulary_map", {})

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


    def _has_cn_content(self, index):
        """判断指定索引的词条是否有中文内容（有翻译文件或可进行临时翻译）"""
        if not self.wiki_entries or index >= len(self.wiki_entries):
            return False

        # 检查是否有翻译文件
        if self.wiki_cn_entries and index < len(self.wiki_cn_entries):
            en_content = self.wiki_entries[index][1]
            cn_content = self.wiki_cn_entries[index][1]
            # 如果中文内容与英文内容不同，则有翻译文件
            if cn_content != en_content:
                return True

        # 即使没有翻译文件，只要有词汇映射表，也可以进行临时翻译
        return bool(self.vocab_map)

    def _show_entry(self, index):
        # 语言切换按钮始终显示（只要有词条）
        has_cn = self._has_cn_content(index)
        self.lang_btn.setVisible(bool(self.wiki_entries))

        # 如果当前是中文模式但没有中文内容，自动切回英文
        if self.current_lang == "cn" and not has_cn:
            self.current_lang = "en"

        entry_name, content = self.wiki_entries[index]

        if self.current_lang == "cn":
            # 优先使用翻译文件
            has_translation_file = (
                self.wiki_cn_entries
                and index < len(self.wiki_cn_entries)
                and self.wiki_cn_entries[index][1] != content
            )

            if has_translation_file:
                # 使用现有的翻译文件
                entry_name, content = self.wiki_cn_entries[index]
            else:
                # 使用词汇映射表进行临时翻译
                content = translate_content_by_vocab(content, self.vocab_map)
                # 添加临时翻译提示
                content = "⚠️ [临时翻译]\n\n" + content

        html_content, url_to_filename = wiki_to_html(content)
        # 将 URL 映射传递给 text_browser，用于 404 后解析真实 URL
        self.text_browser._url_to_filename = url_to_filename
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
        """点击链接时的处理：wiki内链弹出新窗口，外部链接用浏览器打开"""
        scheme = url.scheme()
        url_str = url.toString()

        # 处理外部链接 http:// 或 https://
        if scheme in ("http", "https"):
            webbrowser.open(url_str)
            return

        # 处理 wiki: 内链
        if scheme != "wiki":
            return
        target = url.path() or url_str.replace("wiki:", "", 1)
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

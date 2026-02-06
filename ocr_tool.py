"""
Windows English OCR Tool
截图后识别英文文字，弹窗显示识别结果
"""

import sys
import pytesseract
from PIL import Image, ImageGrab
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QRubberBand, QDialog
)
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QScreen, QPixmap, QPainter, QColor


class ScreenshotWindow(QWidget):
    """全屏截图选择窗口"""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
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
            self.rubber_band.setGeometry(QRect(self.start_pos, event.pos()).normalized())

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
            self.close()


class ResultDialog(QDialog):
    """OCR结果显示弹窗"""

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OCR Result")
        self.setMinimumSize(400, 300)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        # 显示识别结果
        self.text_edit = QTextEdit()
        self.text_edit.setText(text)
        self.text_edit.setReadOnly(False)  # 允许编辑/复制
        self.text_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.text_edit)

        # 按钮区域
        btn_layout = QHBoxLayout()

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("English OCR Tool")
        self.setMinimumSize(300, 150)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 说明标签
        label = QLabel("Click the button below to capture screen area")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # 截图按钮
        capture_btn = QPushButton("Capture & OCR")
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

        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

    def start_capture(self):
        self.hide()
        # 稍微延迟以确保主窗口隐藏
        QApplication.processEvents()

        self.screenshot_window = ScreenshotWindow(self.process_screenshot)
        self.screenshot_window.show()

    def process_screenshot(self, pixmap):
        """处理截图并进行OCR"""
        self.show()

        # 将QPixmap转换为PIL Image
        image = pixmap.toImage()
        buffer = image.bits().asstring(image.sizeInBytes())
        pil_image = Image.frombuffer(
            'RGBA',
            (image.width(), image.height()),
            buffer,
            'raw',
            'BGRA',
            0,
            1
        )

        # 转换为RGB模式（Tesseract需要）
        pil_image = pil_image.convert('RGB')

        # 执行OCR
        try:
            self.status_label.setText("Processing...")
            QApplication.processEvents()

            # 使用Tesseract进行英文OCR
            text = pytesseract.image_to_string(pil_image, lang='eng')
            text = text.strip()

            if text:
                self.status_label.setText("OCR completed!")
                # 显示结果弹窗
                dialog = ResultDialog(text, self)
                dialog.exec_()
            else:
                self.status_label.setText("No text detected")

        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")


def main():
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

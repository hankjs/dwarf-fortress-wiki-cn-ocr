"""
截图功能模块
提供全屏截图区域选择窗口
"""

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QApplication, QRubberBand, QWidget


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

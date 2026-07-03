import sys
import os
from pathlib import Path

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    sys.path.insert(0, base_path)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)

    style_path = Path(base_path) / 'resources' / 'style.qss'
    if style_path.exists():
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    icon_path = Path(base_path) / 'resources' / 'icon.ico'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
import sys
import os

# Proje dizinini Python yoluna ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase, QIcon
from PyQt5.QtCore import Qt

from gui.main_window import MainWindow, get_global_stylesheet


def main():
    """Uygulamayı başlatır."""
    # Yüksek DPI (High-DPI) ekran desteğini etkinleştir
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    
    # Global stilleri uygula
    app.setStyleSheet(get_global_stylesheet())

    # İkon ayarı (varsa)
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

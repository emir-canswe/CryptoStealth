"""
CryptoStealth — Ana Pencere (main_window.py)
=============================================
PyQt5 tabanlı 4 sekmeli ana uygulama penceresi.

Sekmeler:
1. Gömme (Embed) — Mesajı görsele göm
2. Çıkarma (Extract) — Görselden mesaj çıkar
3. Anahtar Yönetimi (Keygen) — RSA anahtar üretme/yönetme
4. Piksel Analizi (Analysis) — Steganografik analiz araçları

Tema: Koyu tema, terminal estetiği, monospace fontlar

Yazar: CryptoStealth Projesi
"""

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStatusBar, QFrame, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QFontDatabase

from gui.embed_tab import EmbedTab
from gui.extract_tab import ExtractTab
from gui.keygen_tab import KeygenTab
from gui.analysis_tab import AnalysisTab


# ========================================================================
# Tema Renkleri
# ========================================================================
COLORS = {
    "bg_primary": "#0d1117",       # Ana arka plan (derin siyah)
    "bg_secondary": "#161b22",     # Kart arka planı
    "bg_tertiary": "#1a1a2e",      # Sekme arka planı
    "accent_primary": "#0f3460",   # Vurgu (koyu mavi)
    "accent_blue": "#1e90ff",      # Parlak mavi
    "accent_green": "#00ff88",     # Başarı yeşili (neon)
    "accent_red": "#ff4757",       # Hata kırmızısı
    "accent_orange": "#ffa502",    # Uyarı turuncusu
    "accent_purple": "#a855f7",    # Mor vurgu
    "text_primary": "#e6edf3",     # Ana metin
    "text_secondary": "#8b949e",   # İkincil metin
    "text_muted": "#484f58",       # Soluk metin
    "border": "#30363d",           # Kenarlık
    "border_active": "#58a6ff",    # Aktif kenarlık
}


def get_global_stylesheet() -> str:
    """Uygulamanın global CSS stil sayfasını döndürür."""
    return f"""
    /* ===== GENEL STILLER ===== */
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}

    QWidget {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
    }}

    /* ===== SEKME WIDGETI ===== */
    QTabWidget::pane {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        background-color: {COLORS['bg_secondary']};
        padding: 10px;
    }}

    QTabBar::tab {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_secondary']};
        padding: 12px 28px;
        margin-right: 3px;
        border: 1px solid {COLORS['border']};
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: bold;
        font-size: 13px;
        min-width: 140px;
    }}

    QTabBar::tab:selected {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['accent_green']};
        border-color: {COLORS['accent_green']};
        border-bottom: 2px solid {COLORS['bg_secondary']};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {COLORS['accent_primary']};
        color: {COLORS['text_primary']};
    }}

    /* ===== BUTONLAR ===== */
    QPushButton {{
        background-color: {COLORS['accent_primary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: bold;
        font-size: 13px;
        min-height: 20px;
    }}

    QPushButton:hover {{
        background-color: #1a4a80;
        border-color: {COLORS['accent_blue']};
    }}

    QPushButton:pressed {{
        background-color: #0a2a50;
    }}

    QPushButton:disabled {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_muted']};
        border-color: {COLORS['border']};
    }}

    QPushButton#primaryBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0f3460, stop:1 #1e90ff);
        border: none;
        color: white;
        padding: 12px 30px;
        font-size: 14px;
    }}

    QPushButton#primaryBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #1a4a80, stop:1 #3aa0ff);
    }}

    QPushButton#successBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #00cc66, stop:1 #00ff88);
        border: none;
        color: #0d1117;
        font-weight: bold;
    }}

    QPushButton#successBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #00dd77, stop:1 #33ff99);
    }}

    QPushButton#dangerBtn {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #cc3344, stop:1 #ff4757);
        border: none;
        color: white;
    }}

    QPushButton#dangerBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #dd4455, stop:1 #ff6677);
    }}

    /* ===== METİN GİRİŞLERİ ===== */
    QTextEdit, QPlainTextEdit {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['accent_green']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 10px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
        selection-background-color: {COLORS['accent_primary']};
    }}

    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {COLORS['accent_blue']};
    }}

    QLineEdit {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 10px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
    }}

    QLineEdit:focus {{
        border-color: {COLORS['accent_blue']};
    }}

    QLineEdit:disabled {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_muted']};
    }}

    /* ===== ETIKETLER ===== */
    QLabel {{
        color: {COLORS['text_primary']};
        font-size: 13px;
        background: transparent;
    }}

    QLabel#titleLabel {{
        color: {COLORS['accent_green']};
        font-size: 16px;
        font-weight: bold;
    }}

    QLabel#subtitleLabel {{
        color: {COLORS['text_secondary']};
        font-size: 12px;
    }}

    QLabel#successLabel {{
        color: {COLORS['accent_green']};
        font-weight: bold;
    }}

    QLabel#errorLabel {{
        color: {COLORS['accent_red']};
        font-weight: bold;
    }}

    /* ===== İLERLEME ÇUBUĞU ===== */
    QProgressBar {{
        background-color: {COLORS['bg_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        text-align: center;
        color: {COLORS['text_primary']};
        font-weight: bold;
        min-height: 24px;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0f3460, stop:1 #00ff88);
        border-radius: 5px;
    }}

    /* ===== CHECKBOX ===== */
    QCheckBox {{
        color: {COLORS['text_primary']};
        spacing: 8px;
        font-size: 13px;
        background: transparent;
    }}

    QCheckBox::indicator {{
        width: 20px;
        height: 20px;
        border: 2px solid {COLORS['border']};
        border-radius: 4px;
        background-color: {COLORS['bg_primary']};
    }}

    QCheckBox::indicator:checked {{
        background-color: {COLORS['accent_green']};
        border-color: {COLORS['accent_green']};
    }}

    QCheckBox::indicator:hover {{
        border-color: {COLORS['accent_blue']};
    }}

    /* ===== KAYDIRMA ÇUBUĞU ===== */
    QScrollBar:vertical {{
        background-color: {COLORS['bg_primary']};
        width: 10px;
        border: none;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {COLORS['border']};
        border-radius: 5px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['text_muted']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {COLORS['bg_primary']};
        height: 10px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {COLORS['border']};
        border-radius: 5px;
        min-width: 30px;
    }}

    /* ===== FRAME ===== */
    QFrame#cardFrame {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 15px;
    }}

    /* ===== DURUM ÇUBUĞU ===== */
    QStatusBar {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        border-top: 1px solid {COLORS['border']};
        font-size: 12px;
        padding: 4px;
    }}

    /* ===== GRUP KUTUSU ===== */
    QGroupBox {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 20px;
        font-weight: bold;
        color: {COLORS['accent_blue']};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 15px;
        padding: 0 8px;
    }}

    /* ===== ARAÇ İPUCU ===== */
    QToolTip {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['accent_blue']};
        border-radius: 4px;
        padding: 6px;
        font-size: 12px;
    }}
    """


class MainWindow(QMainWindow):
    """
    CryptoStealth ana penceresi.

    4 sekmeli arayüz:
    - Gömme: Mesajı şifreleyip görsele gömer
    - Çıkarma: Görselden şifreli mesajı çıkarır
    - Anahtar Yönetimi: RSA anahtar çifti üretir/yönetir
    - Piksel Analizi: Steganografik analiz araçları
    """

    def __init__(self):
        super().__init__()
        self._init_window()
        self._init_ui()
        self._init_statusbar()

    def _init_window(self):
        """Pencere özelliklerini ayarlar."""
        self.setWindowTitle("🔐 CryptoStealth — Kriptografi + Steganografi")
        self.setMinimumSize(1100, 780)
        self.resize(1200, 850)

        # Pencereyi ekranın ortasına konumla
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _init_ui(self):
        """Ana arayüzü oluşturur."""
        # Merkez widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(10)

        # Başlık alanı
        header = self._create_header()
        main_layout.addWidget(header)

        # Sekme widget'ı
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(False)

        # Sekmeleri oluştur
        self.embed_tab = EmbedTab(self)
        self.extract_tab = ExtractTab(self)
        self.keygen_tab = KeygenTab(self)
        self.analysis_tab = AnalysisTab(self)

        # Sekmeleri ekle (ikon + etiket)
        self.tab_widget.addTab(self.embed_tab, "🔒 Gömme")
        self.tab_widget.addTab(self.extract_tab, "🔓 Çıkarma")
        self.tab_widget.addTab(self.keygen_tab, "🔑 Anahtar Yönetimi")
        self.tab_widget.addTab(self.analysis_tab, "📊 Piksel Analizi")

        main_layout.addWidget(self.tab_widget)

    def _create_header(self) -> QFrame:
        """Uygulama başlık alanını oluşturur."""
        header_frame = QFrame()
        header_frame.setObjectName("cardFrame")
        header_frame.setMaximumHeight(80)
        header_layout = QHBoxLayout(header_frame)

        # Başlık metni
        title_layout = QVBoxLayout()

        title_label = QLabel("⬡ CryptoStealth")
        title_label.setObjectName("titleLabel")
        title_font = QFont("Consolas", 20, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(
            f"color: {COLORS['accent_green']}; "
            f"background: transparent;"
        )

        subtitle_label = QLabel("Hibrit Şifreleme + LSB Steganografi  •  v1.0")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; "
            f"font-size: 12px; background: transparent;"
        )

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Sağ taraf — güvenlik rozeti
        badge_label = QLabel("🛡️ AES-256 + RSA-2048")
        badge_label.setStyleSheet(
            f"color: {COLORS['accent_blue']}; "
            f"background-color: {COLORS['bg_primary']}; "
            f"border: 1px solid {COLORS['accent_blue']}; "
            f"border-radius: 12px; "
            f"padding: 6px 14px; "
            f"font-size: 12px; font-weight: bold;"
        )
        header_layout.addWidget(badge_label)

        return header_frame

    def _init_statusbar(self):
        """Durum çubuğunu başlatır."""
        self.statusBar().showMessage("🟢 Hazır — İşlem bekleniyor")

    def update_status(self, message: str, is_error: bool = False):
        """
        Durum çubuğu mesajını günceller.

        Args:
            message: Gösterilecek durum mesajı.
            is_error: Hata mesajı ise True (kırmızı gösterilir).
        """
        prefix = "🔴" if is_error else "🟢"
        self.statusBar().showMessage(f"{prefix} {message}")

        if is_error:
            self.statusBar().setStyleSheet(
                f"background-color: {COLORS['bg_secondary']}; "
                f"color: {COLORS['accent_red']}; "
                f"border-top: 1px solid {COLORS['accent_red']};"
            )
            # 5 saniye sonra normal renge dön
            QTimer.singleShot(5000, self._reset_statusbar_style)
        else:
            self._reset_statusbar_style()

    def _reset_statusbar_style(self):
        """Durum çubuğu stilini varsayılana döndürür."""
        self.statusBar().setStyleSheet(
            f"background-color: {COLORS['bg_secondary']}; "
            f"color: {COLORS['text_secondary']}; "
            f"border-top: 1px solid {COLORS['border']};"
        )

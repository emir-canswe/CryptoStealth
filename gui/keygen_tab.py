"""
CryptoStealth — Anahtar Yönetimi Sekmesi (keygen_tab.py)
=========================================================
RSA-2048 anahtar çifti üretme, yükleme ve yönetme işlemleri.
Public key'i QR kod olarak dışa aktarma özelliği.

Yazar: CryptoStealth Projesi
"""

import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFileDialog, QGroupBox, QMessageBox,
    QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

from core.crypto_engine import (
    generate_rsa_keypair, save_keypair, load_public_key,
    load_private_key, get_key_fingerprint
)
from utils.qr_utils import public_key_to_qr
from core.exceptions import InvalidKeyError


class KeygenTab(QWidget):
    """Anahtar üretimi ve yönetimi sekmesi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_public_key = None
        self.current_private_key = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Üst kısım: Aksiyon butonları
        action_group = self._create_action_section()
        layout.addWidget(action_group)

        # Orta kısım: Anahtar bilgileri ve önizleme
        info_layout = QHBoxLayout()

        # Sol: Metin görünümü
        text_group = self._create_text_section()
        info_layout.addWidget(text_group, 2)

        # Sağ: QR Kod görünümü
        qr_group = self._create_qr_section()
        info_layout.addWidget(qr_group, 1)

        layout.addLayout(info_layout)

    def _create_action_section(self) -> QGroupBox:
        group = QGroupBox("🛠️ Anahtar İşlemleri")
        layout = QHBoxLayout(group)

        # Yeni anahtar üret butonu
        self.generate_btn = QPushButton("✨ Yeni RSA-2048 Anahtar Çifti Üret")
        self.generate_btn.setObjectName("primaryBtn")
        self.generate_btn.clicked.connect(self._generate_keys)
        layout.addWidget(self.generate_btn)

        # Mevcut anahtarı yükle
        self.load_btn = QPushButton("📂 Mevcut Public Key Yükle")
        self.load_btn.clicked.connect(self._load_public_key)
        layout.addWidget(self.load_btn)

        # QR Kod oluştur
        self.qr_btn = QPushButton("📲 Public Key'i QR Kod Olarak Kaydet")
        self.qr_btn.clicked.connect(self._save_as_qr)
        self.qr_btn.setEnabled(False)
        layout.addWidget(self.qr_btn)

        return group

    def _create_text_section(self) -> QGroupBox:
        group = QGroupBox("📄 Anahtar Bilgileri")
        layout = QVBoxLayout(group)

        # Bilgi etiketleri
        info_layout = QHBoxLayout()

        self.algo_label = QLabel("Algoritma: -")
        info_layout.addWidget(self.algo_label)

        self.size_label = QLabel("Boyut: -")
        info_layout.addWidget(self.size_label)

        self.fingerprint_label = QLabel("Parmak İzi: -")
        self.fingerprint_label.setStyleSheet("color: #00ff88; font-family: monospace;")
        info_layout.addWidget(self.fingerprint_label)

        layout.addLayout(info_layout)

        # Metin alanı
        self.key_text = QTextEdit()
        self.key_text.setReadOnly(True)
        self.key_text.setPlaceholderText("Public key burada görüntülenecektir...")
        self.key_text.setStyleSheet(
            "background-color: #0d1117; "
            "color: #8b949e; "
            "font-family: 'Consolas', monospace; "
            "font-size: 12px; "
            "border: 1px solid #21262d;"
        )
        layout.addWidget(self.key_text)

        return group

    def _create_qr_section(self) -> QGroupBox:
        group = QGroupBox("📲 QR Kod Önizleme")
        layout = QVBoxLayout(group)

        self.qr_preview = QLabel("Henüz oluşturulmadı")
        self.qr_preview.setAlignment(Qt.AlignCenter)
        self.qr_preview.setMinimumSize(250, 250)
        self.qr_preview.setStyleSheet(
            "background-color: #0d1117; "
            "border: 2px dashed #30363d; "
            "border-radius: 10px;"
        )
        layout.addWidget(self.qr_preview)

        return group

    def _generate_keys(self):
        """Yeni RSA anahtar çifti üretir ve kaydeder."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Anahtarların Kaydedileceği Klasörü Seçin"
        )
        if not dir_path:
            return

        try:
            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("⏳ Üretiliyor...")
            if self.main_window:
                self.main_window.update_status("RSA-2048 anahtar çifti üretiliyor...")

            # UI'ın güncellenmesi için QApplication.processEvents()
            # (Küçük bir işlem olduğu için QThread yerine kullanılabilir)
            import PyQt5.QtWidgets as qtw
            qtw.QApplication.processEvents()

            private_pem, public_pem = generate_rsa_keypair()
            private_path, public_path = save_keypair(private_pem, public_pem, dir_path)

            self.current_public_key = public_pem
            self.current_private_key = private_pem

            self._update_ui_with_key(public_pem)

            msg = f"✅ Anahtarlar başarıyla üretildi ve kaydedildi:\n\n{public_path}\n{private_path}\n\n⚠️ UYARI: private_key.pem dosyasını kimseyle paylaşmayın!"
            QMessageBox.information(self, "Başarılı", msg)

            if self.main_window:
                self.main_window.update_status("Anahtarlar başarıyla üretildi.")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Anahtar üretilirken hata oluştu:\n{str(e)}")
            if self.main_window:
                self.main_window.update_status("Anahtar üretme başarısız.", True)
        finally:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("✨ Yeni RSA-2048 Anahtar Çifti Üret")

    def _load_public_key(self):
        """Mevcut bir public key'i yükler."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Public Key Seç", "", "PEM Dosyaları (*.pem);;Tüm Dosyalar (*)"
        )
        if not path:
            return

        try:
            public_pem = load_public_key(path)
            self.current_public_key = public_pem
            self._update_ui_with_key(public_pem)

            if self.main_window:
                self.main_window.update_status(f"Public key yüklendi: {os.path.basename(path)}")

        except InvalidKeyError as e:
            QMessageBox.critical(self, "Hata", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Anahtar yüklenemedi:\n{str(e)}")

    def _update_ui_with_key(self, public_pem: bytes):
        """Arayüzü yüklenen anahtarla günceller."""
        self.key_text.setPlainText(public_pem.decode("utf-8"))
        self.algo_label.setText("Algoritma: RSA")
        self.size_label.setText("Boyut: 2048-bit")

        fingerprint = get_key_fingerprint(public_pem)
        # Sadece ilk 16 karakteri göster
        self.fingerprint_label.setText(f"Parmak İzi: {fingerprint[:47]}...")

        self.qr_btn.setEnabled(True)

    def _save_as_qr(self):
        """Public key'i QR kod olarak kaydeder."""
        if not self.current_public_key:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "QR Kodu Kaydet", "public_key_qr.png", "PNG Dosyaları (*.png)"
        )
        if not path:
            return

        try:
            public_key_to_qr(
                self.current_public_key,
                path,
                label=f"CryptoStealth Public Key - {datetime.now().strftime('%Y-%m-%d')}"
            )

            # Önizlemeyi güncelle
            pixmap = QPixmap(path)
            scaled = pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_preview.setPixmap(scaled)

            QMessageBox.information(self, "Başarılı", f"✅ QR kod başarıyla kaydedildi:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"QR kod oluşturulamadı:\n{str(e)}")

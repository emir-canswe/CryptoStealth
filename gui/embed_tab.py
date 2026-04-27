"""
CryptoStealth — Gömme Sekmesi (embed_tab.py)
=============================================
Mesajı kriptografik olarak şifreler ve bir PNG görseline gömer.

İşlem Akışı:
1. Kullanıcı kaynak görseli seçer
2. Gizlenecek mesajı yazar
3. Alıcının public key dosyasını seçer
4. (İsteğe bağlı) Sahte mesaj ve şifre ekler
5. "Şifrele ve Göm" butonu ile işlem başlar
6. Çıktı PNG dosyası kaydedilir

Yazar: CryptoStealth Projesi
"""

import os
import json
import traceback
from datetime import datetime, timezone

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFileDialog, QProgressBar, QCheckBox,
    QFrame, QGroupBox, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QFont, QImage

from core.crypto_engine import (
    hybrid_encrypt, serialize_payload, load_public_key,
    compute_hash
)
from core.stego_engine import calculate_capacity, embed_data
from core.fake_layer import embed_fake_message
from core.integrity import compute_file_hash
from core.exceptions import CryptoStealthError, CapacityError


class EmbedWorker(QThread):
    """
    Gömme işlemini arka planda yürüten iş parçacığı.
    GUI'nin donmasını önler.
    """
    progress = pyqtSignal(int)        # İlerleme yüzdesi
    log_message = pyqtSignal(str)     # Log mesajı
    finished = pyqtSignal(bool, str)  # (başarı, mesaj)

    def __init__(self, params: dict):
        super().__init__()
        self.params = params

    def run(self):
        """Gömme işlemini çalıştırır."""
        try:
            p = self.params

            # Adım 1: Public key yükle
            self.log_message.emit("📥 Public key yükleniyor...")
            self.progress.emit(10)
            public_key = load_public_key(p["public_key_path"])

            # Adım 2: Mesajı hibrit şifrele
            self.log_message.emit("🔐 Mesaj AES-256 + RSA-2048 ile şifreleniyor...")
            self.progress.emit(30)
            payload = hybrid_encrypt(p["message"], public_key)

            # Adım 3: Payload'ı serileştir
            self.log_message.emit("📦 Payload JSON formatına dönüştürülüyor...")
            self.progress.emit(45)

            # Görsel hash'ini ekle
            image_hash = compute_file_hash(p["image_path"])
            payload["image_hash"] = image_hash
            payload["has_fake_layer"] = p.get("use_fake", False)

            serialized = serialize_payload(payload)
            self.log_message.emit(f"   Payload boyutu: {len(serialized)} byte")

            # Adım 4: Kapasite kontrolü
            self.log_message.emit("📏 Görsel kapasitesi kontrol ediliyor...")
            self.progress.emit(55)
            capacity = calculate_capacity(p["image_path"])
            self.log_message.emit(f"   Kapasite: {capacity} byte | Veri: {len(serialized)} byte")

            if len(serialized) > capacity:
                self.finished.emit(False,
                    f"Kapasite yetersiz! Veri: {len(serialized)} byte, "
                    f"Kapasite: {capacity} byte")
                return

            # Adım 5: Steganografik gömme
            if p.get("use_fake", False):
                self.log_message.emit("🎭 Sahte katman ekleniyor...")
                self.progress.emit(70)
                embed_fake_message(
                    image_path=p["image_path"],
                    real_payload=payload,
                    fake_message=p["fake_message"],
                    real_password=p["real_password"],
                    fake_password=p["fake_password"],
                    output_path=p["output_path"]
                )
            else:
                self.log_message.emit("📸 Veri piksellere gömülüyor (LSB)...")
                self.progress.emit(70)
                embed_data(p["image_path"], serialized, p["output_path"])

            self.progress.emit(90)

            # Adım 6: Doğrulama
            self.log_message.emit("✅ Çıktı dosyası doğrulanıyor...")
            output_hash = compute_file_hash(p["output_path"])
            output_size = os.path.getsize(p["output_path"])
            self.log_message.emit(f"   Çıktı boyutu: {output_size} byte")
            self.log_message.emit(f"   Çıktı SHA-256: {output_hash[:32]}...")

            self.progress.emit(100)
            self.finished.emit(True,
                f"Gömme başarılı! Dosya: {os.path.basename(p['output_path'])}")

        except CryptoStealthError as e:
            self.finished.emit(False, str(e))
        except Exception as e:
            self.finished.emit(False, f"Beklenmeyen hata: {str(e)}")


class EmbedTab(QWidget):
    """Mesaj gömme sekmesi arayüzü."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.image_path = None
        self.public_key_path = None
        self._init_ui()

    def _init_ui(self):
        """Arayüz elemanlarını oluşturur."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Üst kısım: Görsel + Mesaj (yan yana)
        top_layout = QHBoxLayout()

        # Sol: Görsel seçimi ve önizleme
        image_group = self._create_image_section()
        top_layout.addWidget(image_group, 1)

        # Sağ: Mesaj girişi
        message_group = self._create_message_section()
        top_layout.addWidget(message_group, 1)

        layout.addLayout(top_layout)

        # Orta kısım: Anahtar ve ayarlar
        settings_group = self._create_settings_section()
        layout.addWidget(settings_group)

        # Sahte mesaj bölümü
        self.fake_group = self._create_fake_section()
        self.fake_group.setVisible(False)
        layout.addWidget(self.fake_group)

        # Alt kısım: İşlem butonları ve ilerleme
        action_layout = self._create_action_section()
        layout.addLayout(action_layout)

        # Log alanı
        log_group = self._create_log_section()
        layout.addWidget(log_group)

    def _create_image_section(self) -> QGroupBox:
        """Görsel seçim ve önizleme bölümünü oluşturur."""
        group = QGroupBox("📸 Kaynak Görsel")
        group_layout = QVBoxLayout(group)

        # Görsel seç butonu
        select_btn = QPushButton("📂 Görsel Seç (PNG)")
        select_btn.clicked.connect(self._select_image)
        group_layout.addWidget(select_btn)

        # Önizleme alanı
        self.image_preview = QLabel("Görsel seçilmedi")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumSize(220, 220)
        self.image_preview.setMaximumSize(300, 300)
        self.image_preview.setStyleSheet(
            "background-color: #0d1117; "
            "border: 2px dashed #30363d; "
            "border-radius: 10px; "
            "color: #484f58; font-size: 13px;"
        )
        group_layout.addWidget(self.image_preview, alignment=Qt.AlignCenter)

        # Görsel bilgi etiketi
        self.image_info_label = QLabel("")
        self.image_info_label.setObjectName("subtitleLabel")
        self.image_info_label.setAlignment(Qt.AlignCenter)
        self.image_info_label.setWordWrap(True)
        group_layout.addWidget(self.image_info_label)

        return group

    def _create_message_section(self) -> QGroupBox:
        """Mesaj giriş bölümünü oluşturur."""
        group = QGroupBox("✉️ Gizlenecek Mesaj")
        group_layout = QVBoxLayout(group)

        # Mesaj giriş alanı
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText(
            "Gizlemek istediğiniz mesajı buraya yazın...\n\n"
            "Bu mesaj AES-256 ile şifrelenecek ve\n"
            "görselin piksellerine gömülecektir."
        )
        self.message_input.setMinimumHeight(200)
        self.message_input.textChanged.connect(self._update_char_count)
        group_layout.addWidget(self.message_input)

        # Karakter sayacı
        self.char_count_label = QLabel("0 karakter")
        self.char_count_label.setObjectName("subtitleLabel")
        self.char_count_label.setAlignment(Qt.AlignRight)
        group_layout.addWidget(self.char_count_label)

        return group

    def _create_settings_section(self) -> QGroupBox:
        """Anahtar ve ayarlar bölümünü oluşturur."""
        group = QGroupBox("🔑 Şifreleme Ayarları")
        group_layout = QVBoxLayout(group)

        # Public key seçimi
        key_layout = QHBoxLayout()
        key_label = QLabel("Alıcının Public Key'i:")
        key_layout.addWidget(key_label)

        self.key_path_input = QLineEdit()
        self.key_path_input.setReadOnly(True)
        self.key_path_input.setPlaceholderText("public_key.pem dosyasını seçin...")
        key_layout.addWidget(self.key_path_input, 1)

        key_btn = QPushButton("📂 Seç")
        key_btn.setMaximumWidth(80)
        key_btn.clicked.connect(self._select_public_key)
        key_layout.addWidget(key_btn)

        group_layout.addLayout(key_layout)

        # Sahte mesaj checkbox
        self.fake_checkbox = QCheckBox("🎭 Sahte Mesaj Katmanı Ekle (Tuzak)")
        self.fake_checkbox.setToolTip(
            "Yanlış şifre girildiğinde gösterilecek sahte bir mesaj ekler.\n"
            "Gerçek mesajı korumak için ekstra güvenlik katmanı."
        )
        self.fake_checkbox.stateChanged.connect(self._toggle_fake_section)
        group_layout.addWidget(self.fake_checkbox)

        return group

    def _create_fake_section(self) -> QGroupBox:
        """Sahte mesaj bölümünü oluşturur."""
        group = QGroupBox("🎭 Sahte Mesaj (Tuzak Katmanı)")
        group_layout = QVBoxLayout(group)

        # Sahte mesaj girişi
        fake_msg_label = QLabel("Sahte Mesaj:")
        group_layout.addWidget(fake_msg_label)

        self.fake_message_input = QTextEdit()
        self.fake_message_input.setPlaceholderText(
            "Yanlış şifre girildiğinde gösterilecek sahte mesaj...\n"
            "Örnek: 'Toplantı yarın saat 15:00'da.'"
        )
        self.fake_message_input.setMaximumHeight(80)
        group_layout.addWidget(self.fake_message_input)

        # Şifre alanları
        pwd_layout = QHBoxLayout()

        # Gerçek şifre
        real_pwd_layout = QVBoxLayout()
        real_pwd_label = QLabel("🔒 Gerçek Şifre:")
        real_pwd_layout.addWidget(real_pwd_label)
        self.real_password_input = QLineEdit()
        self.real_password_input.setEchoMode(QLineEdit.Password)
        self.real_password_input.setPlaceholderText("Gerçek mesaj için şifre")
        real_pwd_layout.addWidget(self.real_password_input)
        pwd_layout.addLayout(real_pwd_layout)

        # Sahte şifre
        fake_pwd_layout = QVBoxLayout()
        fake_pwd_label = QLabel("🎭 Sahte Şifre:")
        fake_pwd_layout.addWidget(fake_pwd_label)
        self.fake_password_input = QLineEdit()
        self.fake_password_input.setEchoMode(QLineEdit.Password)
        self.fake_password_input.setPlaceholderText("Tuzak mesaj için şifre")
        fake_pwd_layout.addWidget(self.fake_password_input)
        pwd_layout.addLayout(fake_pwd_layout)

        group_layout.addLayout(pwd_layout)

        return group

    def _create_action_section(self) -> QVBoxLayout:
        """İşlem butonları ve ilerleme çubuğunu oluşturur."""
        layout = QVBoxLayout()

        # Butonlar
        btn_layout = QHBoxLayout()

        # Kapasite kontrol butonu
        capacity_btn = QPushButton("📏 Kapasiteyi Kontrol Et")
        capacity_btn.clicked.connect(self._check_capacity)
        btn_layout.addWidget(capacity_btn)

        # Kapasite bilgisi
        self.capacity_label = QLabel("")
        self.capacity_label.setObjectName("subtitleLabel")
        btn_layout.addWidget(self.capacity_label, 1)

        # Çıktı yolu seçimi
        output_btn = QPushButton("💾 Çıktı Yolu")
        output_btn.clicked.connect(self._select_output_path)
        btn_layout.addWidget(output_btn)

        layout.addLayout(btn_layout)

        # Çıktı yolu gösterge
        self.output_path_label = QLineEdit()
        self.output_path_label.setReadOnly(True)
        self.output_path_label.setPlaceholderText("Çıktı dosyasının kaydedileceği yol...")
        layout.addWidget(self.output_path_label)

        # Ana işlem butonu
        self.embed_btn = QPushButton("🔐 ŞİFRELE VE GÖM")
        self.embed_btn.setObjectName("successBtn")
        self.embed_btn.setMinimumHeight(50)
        self.embed_btn.setFont(QFont("Consolas", 14, QFont.Bold))
        self.embed_btn.clicked.connect(self._start_embed)
        layout.addWidget(self.embed_btn)

        # İlerleme çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        return layout

    def _create_log_section(self) -> QGroupBox:
        """Log alanını oluşturur."""
        group = QGroupBox("📋 İşlem Logları")
        group_layout = QVBoxLayout(group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(130)
        self.log_output.setStyleSheet(
            "background-color: #0d1117; "
            "color: #8b949e; "
            "font-family: 'Consolas', monospace; "
            "font-size: 12px; "
            "border: 1px solid #21262d; "
            "border-radius: 6px;"
        )
        group_layout.addWidget(self.log_output)

        return group

    # ====================================================================
    # Olay İşleyicileri
    # ====================================================================

    def _select_image(self):
        """Görsel dosyası seçme diyaloğunu açar."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Kaynak Görsel Seç", "",
            "PNG Dosyaları (*.png);;Tüm Görseller (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.image_path = path
            self._show_image_preview(path)
            self._log(f"📸 Görsel seçildi: {os.path.basename(path)}")

    def _show_image_preview(self, path: str):
        """Seçilen görselin önizlemesini gösterir."""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                QSize(220, 220), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_preview.setPixmap(scaled)
            self.image_preview.setStyleSheet(
                "background-color: #0d1117; "
                "border: 2px solid #00ff88; "
                "border-radius: 10px; padding: 5px;"
            )

            # Görsel bilgisi
            w, h = pixmap.width(), pixmap.height()
            size_kb = os.path.getsize(path) / 1024
            try:
                cap = calculate_capacity(path)
                self.image_info_label.setText(
                    f"{w}x{h} piksel • {size_kb:.1f} KB • Kapasite: {cap} byte"
                )
            except Exception:
                self.image_info_label.setText(f"{w}x{h} piksel • {size_kb:.1f} KB")

    def _select_public_key(self):
        """Public key dosyası seçme diyaloğunu açar."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Public Key Seç", "",
            "PEM Dosyaları (*.pem);;Tüm Dosyalar (*)"
        )
        if path:
            self.public_key_path = path
            self.key_path_input.setText(path)
            self._log(f"🔑 Public key yüklendi: {os.path.basename(path)}")

    def _select_output_path(self):
        """Çıktı dosyası kaydetme yolunu seçer."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Çıktı Dosyasını Kaydet", "stego_output.png",
            "PNG Dosyaları (*.png)"
        )
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.output_path_label.setText(path)

    def _check_capacity(self):
        """Görselin veri taşıma kapasitesini kontrol eder."""
        if not self.image_path:
            self._log("⚠️ Önce bir görsel seçin!")
            return

        try:
            capacity = calculate_capacity(self.image_path)
            msg = self.message_input.toPlainText()
            msg_size = len(msg.encode("utf-8"))

            # Yaklaşık payload boyutunu hesapla (JSON overhead dahil)
            estimated_payload = msg_size + 600  # ~600 byte JSON overhead

            if estimated_payload <= capacity:
                self.capacity_label.setText(
                    f"✅ Kapasite: {capacity} byte | Tahmini veri: ~{estimated_payload} byte"
                )
                self.capacity_label.setStyleSheet("color: #00ff88; background: transparent;")
            else:
                self.capacity_label.setText(
                    f"❌ Kapasite yetersiz! {capacity} byte < ~{estimated_payload} byte"
                )
                self.capacity_label.setStyleSheet("color: #ff4757; background: transparent;")

            self._log(f"📏 Kapasite: {capacity} byte, Tahmini veri: ~{estimated_payload} byte")
        except Exception as e:
            self._log(f"❌ Kapasite hesaplama hatası: {str(e)}")

    def _toggle_fake_section(self, state):
        """Sahte mesaj bölümünü göster/gizle."""
        self.fake_group.setVisible(state == Qt.Checked)

    def _update_char_count(self):
        """Karakter sayacını günceller."""
        text = self.message_input.toPlainText()
        byte_count = len(text.encode("utf-8"))
        self.char_count_label.setText(f"{len(text)} karakter ({byte_count} byte)")

    def _start_embed(self):
        """Gömme işlemini başlatır."""
        # Doğrulama
        if not self.image_path:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir kaynak görsel seçin.")
            return
        if not self.message_input.toPlainText().strip():
            QMessageBox.warning(self, "Uyarı", "Lütfen gizlenecek mesajı girin.")
            return
        if not self.public_key_path:
            QMessageBox.warning(self, "Uyarı", "Lütfen alıcının public key dosyasını seçin.")
            return
        if not self.output_path_label.text():
            QMessageBox.warning(self, "Uyarı", "Lütfen çıktı dosyası kaydetme yolunu seçin.")
            return

        # Sahte katman doğrulaması
        use_fake = self.fake_checkbox.isChecked()
        if use_fake:
            if not self.fake_message_input.toPlainText().strip():
                QMessageBox.warning(self, "Uyarı", "Sahte mesaj alanı boş bırakılamaz.")
                return
            if not self.real_password_input.text():
                QMessageBox.warning(self, "Uyarı", "Gerçek şifre giriniz.")
                return
            if not self.fake_password_input.text():
                QMessageBox.warning(self, "Uyarı", "Sahte şifre giriniz.")
                return
            if self.real_password_input.text() == self.fake_password_input.text():
                QMessageBox.warning(self, "Uyarı", "Gerçek ve sahte şifreler farklı olmalıdır!")
                return

        # Parametreleri hazırla
        params = {
            "image_path": self.image_path,
            "message": self.message_input.toPlainText(),
            "public_key_path": self.public_key_path,
            "output_path": self.output_path_label.text(),
            "use_fake": use_fake,
        }

        if use_fake:
            params["fake_message"] = self.fake_message_input.toPlainText()
            params["real_password"] = self.real_password_input.text()
            params["fake_password"] = self.fake_password_input.text()

        # UI'yi kilitle
        self.embed_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()

        self._log("🚀 Gömme işlemi başlatılıyor...")
        self._log(f"   Algoritma: AES-256-CBC + RSA-2048-OAEP")
        self._log(f"   Kaynak: {os.path.basename(self.image_path)}")

        # İşçi thread'i başlat
        self.worker = EmbedWorker(params)
        self.worker.progress.connect(self._on_progress)
        self.worker.log_message.connect(self._log)
        self.worker.finished.connect(self._on_embed_finished)
        self.worker.start()

    def _on_progress(self, value: int):
        """İlerleme çubuğunu günceller."""
        self.progress_bar.setValue(value)

    def _on_embed_finished(self, success: bool, message: str):
        """Gömme işlemi tamamlandığında çağrılır."""
        self.embed_btn.setEnabled(True)

        if success:
            self._log(f"✅ {message}")
            self.progress_bar.setStyleSheet(
                "QProgressBar::chunk { background: #00ff88; border-radius: 5px; }"
            )
            if self.main_window:
                self.main_window.update_status(message)
            QMessageBox.information(self, "Başarılı", f"✅ {message}")
        else:
            self._log(f"❌ HATA: {message}")
            self.progress_bar.setStyleSheet(
                "QProgressBar::chunk { background: #ff4757; border-radius: 5px; }"
            )
            if self.main_window:
                self.main_window.update_status(message, is_error=True)
            QMessageBox.critical(self, "Hata", f"❌ {message}")

    def _log(self, message: str):
        """Log alanına mesaj ekler."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        # Otomatik scroll
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

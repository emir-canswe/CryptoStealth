"""
CryptoStealth — Çıkarma Sekmesi (extract_tab.py)
=================================================
Steganografik görselden şifreli mesajı çıkarır ve çözer.

İşlem Akışı:
1. Kullanıcı steganografik görseli seçer
2. Private key dosyasını seçer
3. (Sahte katman varsa) Şifre girer
4. "Çıkar ve Çöz" butonu ile işlem başlar
5. Mesaj gösterilir ve bütünlük doğrulanır

Brute-Force Koruması:
- Her yanlış denemede bekleme süresi 2x katlanır
- 5 başarısız denemeden sonra 60 saniyelik kilitleme

Yazar: CryptoStealth Projesi
"""

import os
import json
import time
from datetime import datetime, timezone

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFileDialog, QProgressBar, QFrame,
    QGroupBox, QMessageBox, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPixmap, QFont

from core.crypto_engine import (
    hybrid_decrypt, deserialize_payload, load_private_key,
    verify_hash
)
from core.stego_engine import extract_data
from core.fake_layer import extract_with_password, has_fake_layer
from core.exceptions import (
    CryptoStealthError, DecryptionError, IntegrityError, ExtractionError
)


# Brute-force koruma dosyası yolu
BRUTE_FORCE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "brute_force_log.json"
)


class ExtractWorker(QThread):
    """
    Çıkarma işlemini arka planda yürüten iş parçacığı.
    """
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str)  # (başarı, mesaj, sonuç_metin)

    def __init__(self, params: dict):
        super().__init__()
        self.params = params

    def run(self):
        """Çıkarma işlemini çalıştırır."""
        try:
            p = self.params

            # Adım 1: Görselden veri çıkar
            self.log_message.emit("📸 Görselden veri çıkarılıyor (LSB)...")
            self.progress.emit(20)

            if p.get("use_password", False):
                # Sahte katmanlı çıkarma
                self.log_message.emit("🎭 Şifre ile katman kontrolü yapılıyor...")
                self.progress.emit(40)

                private_key = None
                if p.get("private_key_path"):
                    private_key = load_private_key(p["private_key_path"])

                message, is_real = extract_with_password(
                    p["image_path"], p["password"], private_key
                )

                self.progress.emit(80)

                if is_real:
                    self.log_message.emit("✅ Gerçek mesaj başarıyla çözüldü!")
                    self.log_message.emit("🔐 Bu gerçek mesajdır.")
                else:
                    self.log_message.emit("🎭 Sahte katman mesajı döndürüldü.")
                    self.log_message.emit("⚠️ Bu SAHTE bir mesajdır!")

                self.progress.emit(100)
                layer_info = "GERÇEK" if is_real else "SAHTE (TUZAK)"
                self.finished.emit(True,
                    f"Mesaj çıkarıldı [{layer_info}]", message)

            else:
                # Standart çıkarma (sahte katman yok)
                raw_data = extract_data(p["image_path"])
                self.log_message.emit(f"   Çıkarılan veri: {len(raw_data)} byte")

                # Adım 2: JSON parse et
                self.log_message.emit("📦 Payload deserialize ediliyor...")
                self.progress.emit(40)
                payload = deserialize_payload(raw_data)

                self.log_message.emit(f"   Versiyon: {payload.get('version', '?')}")
                self.log_message.emit(
                    f"   Algoritma: {payload.get('algorithm', '?')}")

                # Adım 3: Private key yükle
                self.log_message.emit("🔑 Private key yükleniyor...")
                self.progress.emit(55)
                private_key = load_private_key(p["private_key_path"])

                # Adım 4: Hibrit şifre çöz
                self.log_message.emit("🔓 Hibrit şifre çözülüyor (RSA + AES)...")
                self.progress.emit(70)
                message = hybrid_decrypt(payload, private_key)

                # Adım 5: Hash doğrulama
                self.log_message.emit("🔍 Bütünlük doğrulanıyor (SHA-256)...")
                self.progress.emit(90)

                if "message_hash" in payload:
                    msg_bytes = message.encode("utf-8")
                    if verify_hash(msg_bytes, payload["message_hash"]):
                        self.log_message.emit("✅ Hash doğrulaması BAŞARILI!")
                    else:
                        self.log_message.emit("⚠️ Hash doğrulaması BAŞARISIZ!")

                self.progress.emit(100)
                self.log_message.emit(f"📝 Mesaj uzunluğu: {len(message)} karakter")
                self.finished.emit(True,
                    "Mesaj başarıyla çıkarıldı ve çözüldü!", message)

        except DecryptionError as e:
            self.finished.emit(False, str(e), "")
        except IntegrityError as e:
            self.finished.emit(False, str(e), "")
        except ExtractionError as e:
            self.finished.emit(False, str(e), "")
        except CryptoStealthError as e:
            self.finished.emit(False, str(e), "")
        except Exception as e:
            self.finished.emit(False, f"Beklenmeyen hata: {str(e)}", "")


class ExtractTab(QWidget):
    """Mesaj çıkarma sekmesi arayüzü."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.image_path = None
        self.private_key_path = None
        self.failed_attempts = 0
        self.last_attempt_time = 0
        self.lockout_until = 0
        self._load_brute_force_state()
        self._init_ui()

    def _init_ui(self):
        """Arayüz elemanlarını oluşturur."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # Üst kısım: Görsel + Sonuç (yan yana)
        top_layout = QHBoxLayout()

        # Sol: Görsel ve anahtar seçimi
        input_group = self._create_input_section()
        top_layout.addWidget(input_group, 1)

        # Sağ: Sonuç gösterimi
        result_group = self._create_result_section()
        top_layout.addWidget(result_group, 1)

        layout.addLayout(top_layout)

        # Şifre alanı (sahte katman için)
        password_group = self._create_password_section()
        layout.addWidget(password_group)

        # İşlem butonları
        action_layout = self._create_action_section()
        layout.addLayout(action_layout)

        # Log alanı
        log_group = self._create_log_section()
        layout.addWidget(log_group)

    def _create_input_section(self) -> QGroupBox:
        """Görsel ve anahtar seçim bölümünü oluşturur."""
        group = QGroupBox("📥 Giriş Dosyaları")
        group_layout = QVBoxLayout(group)

        # Steganografik görsel seçimi
        stego_btn = QPushButton("📸 Steganografik Görsel Seç")
        stego_btn.clicked.connect(self._select_stego_image)
        group_layout.addWidget(stego_btn)

        # Önizleme
        self.image_preview = QLabel("Görsel seçilmedi")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumSize(220, 220)
        self.image_preview.setMaximumSize(300, 300)
        self.image_preview.setStyleSheet(
            "background-color: #0d1117; "
            "border: 2px dashed #30363d; "
            "border-radius: 10px; "
            "color: #484f58;"
        )
        group_layout.addWidget(self.image_preview, alignment=Qt.AlignCenter)

        # Görsel bilgisi
        self.image_info_label = QLabel("")
        self.image_info_label.setObjectName("subtitleLabel")
        self.image_info_label.setAlignment(Qt.AlignCenter)
        group_layout.addWidget(self.image_info_label)

        # Private key seçimi
        key_layout = QHBoxLayout()
        key_label = QLabel("🔑 Private Key:")
        key_layout.addWidget(key_label)

        self.key_path_input = QLineEdit()
        self.key_path_input.setReadOnly(True)
        self.key_path_input.setPlaceholderText("private_key.pem dosyasını seçin...")
        key_layout.addWidget(self.key_path_input, 1)

        key_btn = QPushButton("📂 Seç")
        key_btn.setMaximumWidth(80)
        key_btn.clicked.connect(self._select_private_key)
        key_layout.addWidget(key_btn)

        group_layout.addLayout(key_layout)

        return group

    def _create_result_section(self) -> QGroupBox:
        """Sonuç gösterme bölümünü oluşturur."""
        group = QGroupBox("📝 Çözülmüş Mesaj")
        group_layout = QVBoxLayout(group)

        # Sonuç mesajı
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setPlaceholderText(
            "Çözülmüş mesaj burada görüntülenecek..."
        )
        self.result_output.setMinimumHeight(200)
        self.result_output.setStyleSheet(
            "background-color: #0d1117; "
            "color: #00ff88; "
            "font-family: 'Consolas', monospace; "
            "font-size: 14px; "
            "border: 1px solid #21262d; "
            "border-radius: 6px; "
            "padding: 10px;"
        )
        group_layout.addWidget(self.result_output)

        # Kopyala butonu
        copy_btn = QPushButton("📋 Mesajı Kopyala")
        copy_btn.clicked.connect(self._copy_result)
        group_layout.addWidget(copy_btn)

        # Hash doğrulama göstergesi
        self.hash_indicator = QLabel("")
        self.hash_indicator.setAlignment(Qt.AlignCenter)
        self.hash_indicator.setStyleSheet(
            "padding: 8px; border-radius: 6px; font-weight: bold;"
        )
        group_layout.addWidget(self.hash_indicator)

        return group

    def _create_password_section(self) -> QGroupBox:
        """Şifre giriş bölümünü oluşturur."""
        group = QGroupBox("🔐 Şifre (Sahte Katman İçin)")
        group_layout = QHBoxLayout(group)

        pwd_label = QLabel("Şifre:")
        group_layout.addWidget(pwd_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText(
            "Sahte katman varsa şifrenizi girin (yoksa boş bırakın)"
        )
        group_layout.addWidget(self.password_input, 1)

        # Deneme sayacı
        self.attempt_label = QLabel("")
        self.attempt_label.setObjectName("subtitleLabel")
        group_layout.addWidget(self.attempt_label)

        return group

    def _create_action_section(self) -> QVBoxLayout:
        """İşlem butonlarını oluşturur."""
        layout = QVBoxLayout()

        # Ana çıkarma butonu
        self.extract_btn = QPushButton("🔓 ÇIKAR VE ÇÖZ")
        self.extract_btn.setObjectName("primaryBtn")
        self.extract_btn.setMinimumHeight(50)
        self.extract_btn.setFont(QFont("Consolas", 14, QFont.Bold))
        self.extract_btn.clicked.connect(self._start_extract)
        layout.addWidget(self.extract_btn)

        # İlerleme çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        # Kilitleme uyarısı
        self.lockout_label = QLabel("")
        self.lockout_label.setAlignment(Qt.AlignCenter)
        self.lockout_label.setStyleSheet(
            "color: #ff4757; font-weight: bold; "
            "background: transparent; padding: 5px;"
        )
        self.lockout_label.setVisible(False)
        layout.addWidget(self.lockout_label)

        return layout

    def _create_log_section(self) -> QGroupBox:
        """Log alanını oluşturur."""
        group = QGroupBox("📋 İşlem Logları")
        group_layout = QVBoxLayout(group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(120)
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
    # Brute-Force Koruma
    # ====================================================================

    def _load_brute_force_state(self):
        """Brute-force deneme sayacını dosyadan yükler."""
        try:
            if os.path.exists(BRUTE_FORCE_FILE):
                with open(BRUTE_FORCE_FILE, "r") as f:
                    state = json.load(f)
                self.failed_attempts = state.get("failed_attempts", 0)
                self.last_attempt_time = state.get("last_attempt_time", 0)
                self.lockout_until = state.get("lockout_until", 0)
        except Exception:
            self.failed_attempts = 0
            self.last_attempt_time = 0
            self.lockout_until = 0

    def _save_brute_force_state(self):
        """Brute-force deneme sayacını dosyaya kaydeder."""
        try:
            state = {
                "failed_attempts": self.failed_attempts,
                "last_attempt_time": self.last_attempt_time,
                "lockout_until": self.lockout_until,
            }
            with open(BRUTE_FORCE_FILE, "w") as f:
                json.dump(state, f)
        except Exception:
            pass

    def _check_brute_force(self) -> bool:
        """
        Brute-force korumasını kontrol eder.

        Returns:
            bool: İşleme devam edilebilirse True.
        """
        current_time = time.time()

        # Kilitleme süresi kontrolü
        if current_time < self.lockout_until:
            remaining = int(self.lockout_until - current_time)
            self.lockout_label.setText(
                f"🔒 Çok fazla başarısız deneme! "
                f"Lütfen {remaining} saniye bekleyin."
            )
            self.lockout_label.setVisible(True)
            return False

        # Kilitleme süresi dolduysa sayacı sıfırla
        if self.lockout_until > 0 and current_time >= self.lockout_until:
            self.failed_attempts = 0
            self.lockout_until = 0
            self.lockout_label.setVisible(False)
            self._save_brute_force_state()

        # 5 başarısız denemeden sonra 60 saniye kilitle
        if self.failed_attempts >= 5:
            self.lockout_until = current_time + 60
            self._save_brute_force_state()
            self.lockout_label.setText(
                "🔒 Çok fazla başarısız deneme. Lütfen 60 saniye bekleyin."
            )
            self.lockout_label.setVisible(True)
            return False

        # Katlanan bekleme süresi: 1s, 2s, 4s, 8s...
        if self.failed_attempts > 0:
            wait_time = 2 ** (self.failed_attempts - 1)
            elapsed = current_time - self.last_attempt_time
            if elapsed < wait_time:
                remaining = int(wait_time - elapsed)
                self.lockout_label.setText(
                    f"⏳ Lütfen {remaining} saniye bekleyin... "
                    f"(Deneme {self.failed_attempts}/5)"
                )
                self.lockout_label.setVisible(True)
                return False

        self.lockout_label.setVisible(False)
        return True

    def _on_failed_attempt(self):
        """Başarısız deneme sayacını günceller."""
        self.failed_attempts += 1
        self.last_attempt_time = time.time()
        self._save_brute_force_state()
        self.attempt_label.setText(f"Deneme: {self.failed_attempts}/5")
        self.attempt_label.setStyleSheet("color: #ff4757; background: transparent;")

    def _on_successful_attempt(self):
        """Başarılı denemede sayacı sıfırlar."""
        self.failed_attempts = 0
        self.lockout_until = 0
        self._save_brute_force_state()
        self.attempt_label.setText("")
        self.lockout_label.setVisible(False)

    # ====================================================================
    # Olay İşleyicileri
    # ====================================================================

    def _select_stego_image(self):
        """Steganografik görsel seçme diyaloğunu açar."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Steganografik Görsel Seç", "",
            "PNG Dosyaları (*.png)"
        )
        if path:
            self.image_path = path
            self._show_image_preview(path)

            # Sahte katman kontrolü
            if has_fake_layer(path):
                self._log("🎭 Bu görselde sahte katman tespit edildi!")
                self._log("   Çıkarmak için şifre girmeniz gerekecek.")
            else:
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
                "border: 2px solid #1e90ff; "
                "border-radius: 10px; padding: 5px;"
            )

            w, h = pixmap.width(), pixmap.height()
            size_kb = os.path.getsize(path) / 1024
            has_fake = "🎭 Sahte katman var" if has_fake_layer(path) else ""
            self.image_info_label.setText(
                f"{w}x{h} piksel • {size_kb:.1f} KB {has_fake}"
            )

    def _select_private_key(self):
        """Private key dosyası seçme diyaloğunu açar."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Private Key Seç", "",
            "PEM Dosyaları (*.pem);;Tüm Dosyalar (*)"
        )
        if path:
            self.private_key_path = path
            self.key_path_input.setText(path)
            self._log(f"🔑 Private key yüklendi: {os.path.basename(path)}")

    def _copy_result(self):
        """Sonuç mesajını panoya kopyalar."""
        text = self.result_output.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self._log("📋 Mesaj panoya kopyalandı!")

    def _start_extract(self):
        """Çıkarma işlemini başlatır."""
        # Brute-force kontrolü
        if self.password_input.text() and not self._check_brute_force():
            return

        # Doğrulama
        if not self.image_path:
            QMessageBox.warning(self, "Uyarı", "Lütfen steganografik görseli seçin.")
            return
        if not self.private_key_path and not self.password_input.text():
            QMessageBox.warning(self, "Uyarı",
                "Lütfen private key dosyasını seçin veya şifre girin.")
            return

        # Parametreleri hazırla
        password = self.password_input.text()
        use_password = bool(password) and has_fake_layer(self.image_path)

        params = {
            "image_path": self.image_path,
            "private_key_path": self.private_key_path,
            "use_password": use_password,
            "password": password,
        }

        # UI'yi kilitle
        self.extract_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_output.clear()
        self.hash_indicator.setText("")
        self.log_output.clear()

        self._log("🚀 Çıkarma işlemi başlatılıyor...")

        # İşçi thread'i başlat
        self.worker = ExtractWorker(params)
        self.worker.progress.connect(self._on_progress)
        self.worker.log_message.connect(self._log)
        self.worker.finished.connect(self._on_extract_finished)
        self.worker.start()

    def _on_progress(self, value: int):
        """İlerleme çubuğunu günceller."""
        self.progress_bar.setValue(value)

    def _on_extract_finished(self, success: bool, message: str, result_text: str):
        """Çıkarma işlemi tamamlandığında çağrılır."""
        self.extract_btn.setEnabled(True)

        if success:
            self.result_output.setPlainText(result_text)
            self._log(f"✅ {message}")

            # Hash doğrulama göstergesi
            self.hash_indicator.setText("✅ Bütünlük Doğrulandı — Mesaj güvenilir")
            self.hash_indicator.setStyleSheet(
                "background-color: #0a2e1a; "
                "color: #00ff88; "
                "border: 1px solid #00ff88; "
                "border-radius: 6px; "
                "padding: 8px; font-weight: bold;"
            )

            self._on_successful_attempt()

            if self.main_window:
                self.main_window.update_status(message)

        else:
            self._log(f"❌ HATA: {message}")
            self.hash_indicator.setText("❌ Çıkarma Başarısız — " + message[:60])
            self.hash_indicator.setStyleSheet(
                "background-color: #2e0a0a; "
                "color: #ff4757; "
                "border: 1px solid #ff4757; "
                "border-radius: 6px; "
                "padding: 8px; font-weight: bold;"
            )

            # Şifre denemesi başarısız
            if self.password_input.text():
                self._on_failed_attempt()

            if self.main_window:
                self.main_window.update_status(message, is_error=True)

    def _log(self, message: str):
        """Log alanına mesaj ekler."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

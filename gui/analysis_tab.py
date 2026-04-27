"""
CryptoStealth — Piksel Analiz Sekmesi (analysis_tab.py)
========================================================
Görseller üzerinde steganografik manipülasyon tespiti için
gelişmiş analiz araçları sağlar.

Özellikler:
- Piksel fark haritası (Farklı pikselleri kırmızı ile vurgular)
- LSB dağılım analizi (0/1 oranı)
- PSNR (Peak Signal-to-Noise Ratio) hesaplama

Yazar: CryptoStealth Projesi
"""

import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QGroupBox, QMessageBox, QProgressBar,
    QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage

from core.stego_engine import get_pixel_diff_image, analyze_lsb_distribution, calculate_psnr
from utils.file_utils import get_image_dimensions


class AnalysisWorker(QThread):
    """Analiz işlemlerini arka planda yürüten iş parçacığı."""
    progress = pyqtSignal(int)
    result = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, original_path: str, stego_path: str):
        super().__init__()
        self.original_path = original_path
        self.stego_path = stego_path

    def run(self):
        try:
            self.progress.emit(10)

            # 1. PSNR Hesaplama
            psnr_val = calculate_psnr(self.original_path, self.stego_path)
            self.progress.emit(30)

            # 2. LSB Dağılımı (Sadece stego görseli üzerinde)
            lsb_dist = analyze_lsb_distribution(self.stego_path)
            self.progress.emit(60)

            # 3. Fark Haritası Oluşturma
            diff_img = get_pixel_diff_image(self.original_path, self.stego_path)
            
            # PIL Image -> QImage dönüşümü
            diff_img = diff_img.convert("RGBA")
            data = diff_img.tobytes("raw", "RGBA")
            qim = QImage(data, diff_img.width, diff_img.height, QImage.Format_RGBA8888)
            
            self.progress.emit(90)

            res = {
                "psnr": psnr_val,
                "lsb": lsb_dist,
                "diff_qimage": qim
            }
            self.progress.emit(100)
            self.result.emit(res)

        except Exception as e:
            self.error.emit(str(e))


class AnalysisTab(QWidget):
    """Piksel analiz araçları arayüzü."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.original_path = None
        self.stego_path = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Üst kısım: Dosya seçimi
        selection_layout = QHBoxLayout()

        # Orijinal görsel
        self.orig_group = self._create_file_selector("Orijinal Görsel", self._select_original)
        selection_layout.addWidget(self.orig_group)

        # Stego görsel
        self.stego_group = self._create_file_selector("Şüpheli (Stego) Görsel", self._select_stego)
        selection_layout.addWidget(self.stego_group)

        layout.addLayout(selection_layout)

        # İşlem butonu ve progress
        action_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("🔍 Görselleri Karşılaştır ve Analiz Et")
        self.analyze_btn.setObjectName("primaryBtn")
        self.analyze_btn.clicked.connect(self._start_analysis)
        self.analyze_btn.setEnabled(False)
        action_layout.addWidget(self.analyze_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        action_layout.addWidget(self.progress_bar)
        
        layout.addLayout(action_layout)

        # Alt kısım: Sonuçlar
        results_layout = QHBoxLayout()

        # Sol: Fark haritası önizleme
        diff_group = QGroupBox("🔴 Piksel Fark Haritası (10x Büyütülmüş)")
        diff_layout = QVBoxLayout(diff_group)
        self.diff_preview = QLabel("Analiz bekleniyor...")
        self.diff_preview.setAlignment(Qt.AlignCenter)
        self.diff_preview.setStyleSheet(
            "background-color: #0d1117; "
            "border: 1px solid #30363d;"
        )
        diff_layout.addWidget(self.diff_preview)
        results_layout.addWidget(diff_group, 1)

        # Sağ: İstatistikler
        stats_group = QGroupBox("📊 Analiz İstatistikleri")
        self.stats_layout = QVBoxLayout(stats_group)
        
        self.psnr_label = QLabel("PSNR: -")
        self.psnr_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e90ff;")
        self.stats_layout.addWidget(self.psnr_label)

        self.lsb_labels = {}
        for color, name in [("red", "Kırmızı"), ("green", "Yeşil"), ("blue", "Mavi")]:
            lbl = QLabel(f"{name} Kanalı LSB (0/1): -")
            self.lsb_labels[color] = lbl
            self.stats_layout.addWidget(lbl)

        self.stats_layout.addStretch()
        results_layout.addWidget(stats_group, 1)

        layout.addLayout(results_layout)

    def _create_file_selector(self, title: str, callback) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)

        btn = QPushButton(f"📂 {title} Seç")
        btn.clicked.connect(callback)
        layout.addWidget(btn)

        preview = QLabel("Seçilmedi")
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumSize(150, 150)
        preview.setStyleSheet("border: 1px dashed #484f58;")
        layout.addWidget(preview)

        # Obje referansını tutmak için
        group.preview_label = preview
        return group

    def _select_original(self):
        path, _ = QFileDialog.getOpenFileName(self, "Orijinal Görsel Seç", "", "Görseller (*.png *.jpg *.bmp)")
        if path:
            self.original_path = path
            self._update_preview(self.orig_group.preview_label, path)
            self._check_ready()

    def _select_stego(self):
        path, _ = QFileDialog.getOpenFileName(self, "Şüpheli Görsel Seç", "", "PNG Dosyaları (*.png)")
        if path:
            self.stego_path = path
            self._update_preview(self.stego_group.preview_label, path)
            self._check_ready()

    def _update_preview(self, label: QLabel, path: str):
        pixmap = QPixmap(path)
        scaled = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)

    def _check_ready(self):
        self.analyze_btn.setEnabled(bool(self.original_path and self.stego_path))

    def _start_analysis(self):
        if not self.original_path or not self.stego_path:
            return

        # Boyut kontrolü
        try:
            dim1 = get_image_dimensions(self.original_path)
            dim2 = get_image_dimensions(self.stego_path)
            if dim1 != dim2:
                QMessageBox.warning(self, "Boyut Uyuşmazlığı", 
                    f"Görsel boyutları farklı! Karşılaştırma yapılamaz.\n"
                    f"Orijinal: {dim1}\nŞüpheli: {dim2}")
                return
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Görseller okunamadı:\n{str(e)}")
            return

        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        if self.main_window:
            self.main_window.update_status("Analiz yapılıyor, lütfen bekleyin...")

        self.worker = AnalysisWorker(self.original_path, self.stego_path)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.result.connect(self._on_analysis_complete)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.start()

    def _on_analysis_complete(self, result: dict):
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # PSNR
        psnr = result["psnr"]
        if psnr == float('inf'):
            self.psnr_label.setText("PSNR: ∞ (Görseller Birebir Aynı)")
            self.psnr_label.setStyleSheet("color: #00ff88; font-weight: bold;")
        else:
            color = "#00ff88" if psnr > 40 else "#ffa502" if psnr > 30 else "#ff4757"
            self.psnr_label.setText(f"PSNR: {psnr} dB")
            self.psnr_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")

        # LSB
        lsb = result["lsb"]
        for color, lbl in self.lsb_labels.items():
            ratio = lsb[color]['ratio']
            percent = ratio * 100
            lbl.setText(f"{color.capitalize()} Kanalı 1 Oranı: %{percent:.2f}")

        # Fark Haritası
        pixmap = QPixmap.fromImage(result["diff_qimage"])
        scaled = pixmap.scaled(self.diff_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.diff_preview.setPixmap(scaled)

        if self.main_window:
            self.main_window.update_status("Analiz tamamlandı.")

    def _on_analysis_error(self, err: str):
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Hata", f"Analiz sırasında hata oluştu:\n{err}")
        if self.main_window:
            self.main_window.update_status("Analiz başarısız.", True)

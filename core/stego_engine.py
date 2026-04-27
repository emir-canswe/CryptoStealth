"""
CryptoStealth — Steganografi Motoru (stego_engine.py)
=====================================================
LSB (Least Significant Bit) steganografi algoritması ile
görsel dosyalara veri gömme ve çıkarma işlemleri.

Teknik Detaylar:
- Her pikselin R, G, B kanallarının son biti (LSB) kullanılır
- 1 piksel = 3 bit veri kapasitesi
- İlk 32 bit veri uzunluğunu (header) tutar
- Yalnızca PNG formatı desteklenir (kayıpsız sıkıştırma zorunlu)
- Minimum görsel boyutu: 100x100 piksel

Yazar: CryptoStealth Projesi
"""

import struct
import numpy as np
from PIL import Image
from typing import Optional

from core.exceptions import CapacityError, ExtractionError


# ========================================================================
# Kapasite Hesaplama
# ========================================================================

def calculate_capacity(image_path: str) -> int:
    """
    Bir görselin kaç byte veri taşıyabileceğini hesaplar.

    Her pikselin 3 kanalında (R, G, B) birer bit gizlenebilir.
    İlk 32 bit header (veri uzunluğu) için ayrılır.

    Formül: ((width * height * 3) // 8) - 4  byte
             (4 byte = 32-bit header)

    Args:
        image_path: Görselin dosya yolu.

    Returns:
        int: Kullanılabilir kapasite (byte cinsinden).

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        ValueError: Görsel boyutu minimum gereksinimleri karşılamıyorsa.
    """
    img = Image.open(image_path)
    width, height = img.size

    # Minimum boyut kontrolü
    if width < 100 or height < 100:
        raise ValueError(
            f"Görsel boyutu en az 100x100 piksel olmalıdır. "
            f"Mevcut boyut: {width}x{height}"
        )

    # Toplam bit kapasitesi (3 kanal × piksel sayısı)
    total_bits = width * height * 3

    # Byte'a çevir ve 32-bit header'ı çıkar
    capacity_bytes = (total_bits // 8) - 4

    return max(0, capacity_bytes)


def _validate_image(image_path: str) -> Image.Image:
    """
    Görseli doğrular ve RGB moduna çevirir.

    Args:
        image_path: Görselin dosya yolu.

    Returns:
        PIL.Image.Image: RGB modunda açılmış görsel.

    Raises:
        ValueError: Görsel geçersizse veya çok küçükse.
    """
    try:
        img = Image.open(image_path)
    except Exception as e:
        raise ValueError(f"Görsel dosyası açılamadı: {str(e)}")

    # RGBA veya diğer modları RGB'ye çevir
    if img.mode != "RGB":
        img = img.convert("RGB")

    width, height = img.size
    if width < 100 or height < 100:
        raise ValueError(
            f"Görsel boyutu en az 100x100 piksel olmalıdır. "
            f"Mevcut boyut: {width}x{height}"
        )

    return img


# ========================================================================
# LSB Veri Gömme
# ========================================================================

def embed_data(image_path: str, data: bytes, output_path: str) -> bool:
    """
    LSB steganografi yöntemiyle veriyi görsele gömer.

    Algoritma:
    1. Veri uzunluğu ilk 32 bite yazılır (big-endian uint32)
    2. Veri bitleri sırasıyla piksellerin R, G, B kanallarının
       son bitine (LSB) yazılır
    3. Sonuç PNG olarak kaydedilir (kayıpsız sıkıştırma)

    Args:
        image_path: Kaynak görselin dosya yolu.
        data: Gömülecek veri (bytes).
        output_path: Çıktı görselin kaydedileceği yol (PNG formatı).

    Returns:
        bool: İşlem başarılıysa True.

    Raises:
        CapacityError: Veri boyutu görselin kapasitesini aşarsa.
    """
    img = _validate_image(image_path)
    pixels = np.array(img, dtype=np.uint8)
    height, width, channels = pixels.shape

    # Kapasite kontrolü
    capacity = calculate_capacity(image_path)
    if len(data) > capacity:
        raise CapacityError(
            f"Veri boyutu ({len(data)} byte) görselin kapasitesini "
            f"({capacity} byte) aşıyor. Daha büyük bir görsel kullanın."
        )

    # Veri uzunluğunu 32-bit big-endian header olarak hazırla
    data_length = len(data)
    header = struct.pack(">I", data_length)  # 4 byte, big-endian unsigned int

    # Header + veriyi birleştir
    full_data = header + data

    # Tüm veriyi bit dizisine çevir
    bit_array = []
    for byte in full_data:
        for bit_pos in range(7, -1, -1):
            bit_array.append((byte >> bit_pos) & 1)

    # Pikselleri düzleştir (flatten)
    flat_pixels = pixels.flatten()

    # LSB'lere bitleri göm
    for i, bit in enumerate(bit_array):
        # Mevcut pikselin son bitini temizle ve yeni biti yaz
        flat_pixels[i] = (flat_pixels[i] & 0xFE) | bit

    # Pikselleri orijinal şekle geri getir
    stego_pixels = flat_pixels.reshape(height, width, channels)

    # PNG olarak kaydet (kayıpsız sıkıştırma)
    stego_img = Image.fromarray(stego_pixels, "RGB")
    stego_img.save(output_path, format="PNG", optimize=False)

    return True


# ========================================================================
# LSB Veri Çıkarma
# ========================================================================

def extract_data(image_path: str) -> bytes:
    """
    LSB steganografi yöntemiyle görselden veri çıkarır.

    Algoritma:
    1. İlk 32 bitten veri uzunluğu okunur (big-endian uint32)
    2. Uzunluk kadar bit toplanır
    3. Bitler bytes'a dönüştürülür

    Args:
        image_path: Steganografik görselin dosya yolu.

    Returns:
        bytes: Görselden çıkarılan veri.

    Raises:
        ExtractionError: Veri çıkarma başarısızsa veya görsel bozuksa.
    """
    try:
        img = _validate_image(image_path)
    except ValueError as e:
        raise ExtractionError(str(e))

    pixels = np.array(img, dtype=np.uint8)
    flat_pixels = pixels.flatten()

    # İlk 32 bitten veri uzunluğunu oku (header)
    header_bits = []
    for i in range(32):
        if i >= len(flat_pixels):
            raise ExtractionError("Görsel çok küçük, header okunamadı.")
        header_bits.append(flat_pixels[i] & 1)

    # 32 biti 4 byte'a çevir
    header_bytes = _bits_to_bytes(header_bits)
    data_length = struct.unpack(">I", header_bytes)[0]

    # Uzunluk doğrulama
    total_pixels = len(flat_pixels)
    max_data_bytes = (total_pixels // 8) - 4
    if data_length <= 0 or data_length > max_data_bytes:
        raise ExtractionError(
            f"Geçersiz veri uzunluğu ({data_length} byte). "
            f"Görsel steganografik veri içermiyor olabilir."
        )

    # Veri bitlerini oku (header'dan sonra)
    total_data_bits = data_length * 8
    data_bits = []
    start_bit = 32  # Header'dan sonra başla

    for i in range(start_bit, start_bit + total_data_bits):
        if i >= len(flat_pixels):
            raise ExtractionError("Veri bitmeden piksel bitti. Görsel bozuk olabilir.")
        data_bits.append(flat_pixels[i] & 1)

    # Bitleri bytes'a çevir
    extracted_data = _bits_to_bytes(data_bits)

    return extracted_data


def _bits_to_bytes(bits: list) -> bytes:
    """
    Bit listesini bytes'a çevirir.

    Args:
        bits: 0 ve 1'lerden oluşan liste.

    Returns:
        bytes: Dönüştürülmüş byte dizisi.
    """
    byte_array = bytearray()
    for i in range(0, len(bits), 8):
        byte_val = 0
        for j in range(8):
            if i + j < len(bits):
                byte_val = (byte_val << 1) | bits[i + j]
            else:
                byte_val = byte_val << 1
        byte_array.append(byte_val)
    return bytes(byte_array)


# ========================================================================
# Piksel Fark Analizi
# ========================================================================

def get_pixel_diff_image(original_path: str, stego_path: str) -> Image.Image:
    """
    Orijinal ve steganografik görsel arasındaki piksel farklarını görselleştirir.

    Fark olan pikseller 10x büyütülerek kırmızı tonlarında gösterilir.
    Bu analiz, steganografik manipülasyonun tespitinde kullanılır.

    Args:
        original_path: Orijinal görselin dosya yolu.
        stego_path: Steganografik görselin dosya yolu.

    Returns:
        PIL.Image.Image: Fark haritası görseli.
            - Siyah piksel: Değişiklik yok
            - Kırmızı tonları: LSB farkı var (10x büyütülmüş)
    """
    original = np.array(Image.open(original_path).convert("RGB"), dtype=np.int16)
    stego = np.array(Image.open(stego_path).convert("RGB"), dtype=np.int16)

    # Boyut uyumluluğu kontrolü
    if original.shape != stego.shape:
        raise ValueError(
            f"Görsel boyutları uyuşmuyor: "
            f"Orijinal {original.shape} vs Stego {stego.shape}"
        )

    # Mutlak farkı hesapla ve 10x büyüt (görünürlük için)
    diff = np.abs(original - stego)
    diff_amplified = np.clip(diff * 10, 0, 255).astype(np.uint8)

    # Fark olan pikselleri kırmızıyla vurgula
    diff_image = np.zeros_like(diff_amplified)
    # Herhangi bir kanalda fark varsa kırmızı kanalı öne çıkar
    has_diff = np.any(diff > 0, axis=2)
    diff_image[has_diff, 0] = 255  # Kırmızı kanal
    diff_image[has_diff, 1] = diff_amplified[has_diff, 1] // 3  # Yeşil (kısık)
    diff_image[has_diff, 2] = diff_amplified[has_diff, 2] // 3  # Mavi (kısık)

    # Fark miktarını kırmızı yoğunluğuyla göster
    diff_magnitude = np.max(diff_amplified, axis=2)
    diff_image[:, :, 0] = np.where(has_diff, np.maximum(diff_magnitude, 128), 0)

    return Image.fromarray(diff_image, "RGB")


# ========================================================================
# LSB Dağılım Analizi
# ========================================================================

def analyze_lsb_distribution(image_path: str) -> dict:
    """
    Görseldeki LSB (son bit) dağılımını analiz eder.

    Doğal görsellerde LSB dağılımı ~%50/50 (rastgele) olmalıdır.
    Steganografik görsellerde belirgin düzen sapmaları görülebilir.

    Args:
        image_path: Analiz edilecek görselin dosya yolu.

    Returns:
        dict: Her kanal için LSB dağılımı:
            {
                "red": {"zeros": int, "ones": int, "ratio": float},
                "green": {"zeros": int, "ones": int, "ratio": float},
                "blue": {"zeros": int, "ones": int, "ratio": float},
                "total_pixels": int
            }
    """
    img = np.array(Image.open(image_path).convert("RGB"), dtype=np.uint8)
    total_pixels = img.shape[0] * img.shape[1]

    result = {"total_pixels": total_pixels}
    channel_names = ["red", "green", "blue"]

    for ch_idx, ch_name in enumerate(channel_names):
        channel = img[:, :, ch_idx]
        lsb = channel & 1  # Son bitleri al
        ones = int(np.sum(lsb))
        zeros = total_pixels - ones
        ratio = ones / total_pixels if total_pixels > 0 else 0.0

        result[ch_name] = {
            "zeros": zeros,
            "ones": ones,
            "ratio": round(ratio, 4),
        }

    return result


def calculate_psnr(original_path: str, stego_path: str) -> float:
    """
    İki görsel arasındaki PSNR (Peak Signal-to-Noise Ratio) değerini hesaplar.

    PSNR Yorumlama:
    - > 40 dB: Görsel olarak ayırt edilemez (mükemmel)
    - 30-40 dB: Hafif farklılıklar olabilir
    - < 30 dB: Belirgin kalite kaybı

    Formül: PSNR = 10 * log10(MAX² / MSE)
            MSE = ortalama kare hata

    Args:
        original_path: Orijinal görselin dosya yolu.
        stego_path: Steganografik görselin dosya yolu.

    Returns:
        float: PSNR değeri (dB cinsinden).
               Görseller aynıysa float('inf') döner.
    """
    original = np.array(Image.open(original_path).convert("RGB"), dtype=np.float64)
    stego = np.array(Image.open(stego_path).convert("RGB"), dtype=np.float64)

    if original.shape != stego.shape:
        raise ValueError("Görsel boyutları uyuşmuyor.")

    # Ortalama Kare Hata (MSE)
    mse = np.mean((original - stego) ** 2)

    if mse == 0:
        return float("inf")  # Görseller aynı

    # Maksimum piksel değeri
    max_pixel = 255.0

    # PSNR hesapla
    psnr = 10 * np.log10((max_pixel ** 2) / mse)

    return round(psnr, 2)

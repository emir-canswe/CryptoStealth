"""
CryptoStealth — Sahte Mesaj (Tuzak) Katmanı (fake_layer.py)
============================================================
Yanlış şifre girildiğinde sahte ama inandırıcı bir mesaj göstererek
gerçek mesajın varlığını gizleyen çift katmanlı steganografi sistemi.

Çalışma Prensibi:
- Gerçek şifreli veri görselin alt yarısındaki piksellere gömülür
- Sahte mesaj görselin üst yarısındaki piksellere gömülür
- Her iki katman da farklı şifrelerle korunur
- Doğru şifre girildiğinde gerçek mesaj, sahte şifre girildiğinde
  sahte mesaj döndürülür

Yazar: CryptoStealth Projesi
"""

import os
import json
import struct
import hashlib
import numpy as np
from PIL import Image
from typing import Tuple, Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.backends import default_backend

from core.exceptions import DecryptionError, CapacityError
from core.crypto_engine import (
    hybrid_encrypt, hybrid_decrypt,
    serialize_payload, deserialize_payload,
    compute_hash
)


# ========================================================================
# Şifre Tabanlı Anahtar Türetme
# ========================================================================

def _derive_key_from_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """
    Şifreden AES-256 anahtarı türetir (PBKDF2 benzeri basit türetme).

    Args:
        password: Kullanıcının girdiği şifre.
        salt: Tuz değeri. None ise rastgele üretilir.

    Returns:
        Tuple[bytes, bytes]: (key, salt) çifti.
    """
    if salt is None:
        salt = os.urandom(16)

    # SHA-256 ile anahtar türet (iterasyonlu)
    key_material = password.encode("utf-8") + salt
    for _ in range(100000):  # 100K iterasyon — brute-force'a karşı
        key_material = hashlib.sha256(key_material).digest()

    return key_material[:32], salt


def _password_encrypt(data: bytes, password: str) -> bytes:
    """
    Şifre tabanlı AES-256-CBC şifreleme.

    Çıktı formatı: salt(16) + iv(16) + ciphertext

    Args:
        data: Şifrelenecek veri.
        password: Şifre.

    Returns:
        bytes: salt + iv + şifreli veri.
    """
    key, salt = _derive_key_from_password(password)
    iv = os.urandom(16)

    # PKCS7 padding
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()

    # AES-CBC şifreleme
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    return salt + iv + ciphertext


def _password_decrypt(encrypted_data: bytes, password: str) -> bytes:
    """
    Şifre tabanlı AES-256-CBC şifre çözme.

    Args:
        encrypted_data: salt(16) + iv(16) + ciphertext formatında veri.
        password: Şifre.

    Returns:
        bytes: Çözülmüş veri.

    Raises:
        DecryptionError: Yanlış şifre veya bozuk veri.
    """
    if len(encrypted_data) < 48:  # 16 salt + 16 iv + en az 16 ciphertext
        raise DecryptionError("Şifreli veri çok kısa. Veri bozuk olabilir.")

    salt = encrypted_data[:16]
    iv = encrypted_data[16:32]
    ciphertext = encrypted_data[32:]

    key, _ = _derive_key_from_password(password, salt)

    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = sym_padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()

        return plaintext
    except Exception:
        raise DecryptionError("Şifre çözme başarısız. Yanlış şifre girilmiş olabilir.")


# ========================================================================
# Sahte Katmanlı Gömme
# ========================================================================

def embed_fake_message(
    image_path: str,
    real_payload: dict,
    fake_message: str,
    real_password: str,
    fake_password: str,
    output_path: str
) -> bool:
    """
    Görsele hem gerçek hem sahte mesaj gömer (çift katmanlı steganografi).

    Pikseller iki bölgeye ayrılır:
    - Üst yarı: Sahte mesaj (tuzak)
    - Alt yarı: Gerçek şifreli payload

    Her bölge kendi şifresiyle korunur.

    Args:
        image_path: Kaynak görselin dosya yolu.
        real_payload: hybrid_encrypt() çıktısı (gerçek şifreli mesaj).
        fake_message: Sahte mesaj metni (düz metin).
        real_password: Gerçek mesajın şifresi.
        fake_password: Sahte mesajın şifresi.
        output_path: Çıktı görselin kaydedileceği yol.

    Returns:
        bool: İşlem başarılıysa True.

    Raises:
        CapacityError: Veri boyutu görselin kapasitesini aşarsa.
    """
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img, dtype=np.uint8)
    height, width, channels = pixels.shape

    if width < 100 or height < 100:
        raise ValueError("Görsel boyutu en az 100x100 piksel olmalıdır.")

    # Gerçek payload'ı serileştir ve şifrele
    real_data = serialize_payload(real_payload)
    real_encrypted = _password_encrypt(real_data, real_password)

    # Sahte mesajı şifrele
    fake_data = json.dumps({
        "message": fake_message,
        "hash": compute_hash(fake_message.encode("utf-8")),
        "is_fake": True  # İç kullanım için işaretçi
    }).encode("utf-8")
    fake_encrypted = _password_encrypt(fake_data, fake_password)

    # Piksel bölgelerini hesapla
    mid_row = height // 2
    upper_region = pixels[:mid_row, :, :].flatten()  # Üst yarı — sahte
    lower_region = pixels[mid_row:, :, :].flatten()   # Alt yarı — gerçek

    # Kapasite kontrolü
    upper_capacity = (len(upper_region) // 8) - 4  # 4 byte header
    lower_capacity = (len(lower_region) // 8) - 4

    if len(fake_encrypted) > upper_capacity:
        raise CapacityError(
            f"Sahte mesaj boyutu ({len(fake_encrypted)} byte) üst bölge kapasitesini "
            f"({upper_capacity} byte) aşıyor."
        )

    if len(real_encrypted) > lower_capacity:
        raise CapacityError(
            f"Gerçek mesaj boyutu ({len(real_encrypted)} byte) alt bölge kapasitesini "
            f"({lower_capacity} byte) aşıyor."
        )

    # Sahte mesajı üst bölgeye göm
    upper_region = _embed_to_region(upper_region, fake_encrypted)
    # Gerçek mesajı alt bölgeye göm
    lower_region = _embed_to_region(lower_region, real_encrypted)

    # Pikselleri birleştir
    pixels[:mid_row, :, :] = upper_region.reshape(mid_row, width, channels)
    pixels[mid_row:, :, :] = lower_region.reshape(height - mid_row, width, channels)

    # Metadata header'ı (ilk pikselin alpha benzeri işareti)
    # İlk pikselin mavi kanalının 2. bitini işaretçi olarak kullan
    # Bu, sahte katman varlığını belirtir
    pixels[0, 0, 2] = (pixels[0, 0, 2] & 0xFD) | 0x02  # Bit 1'i set et

    # PNG olarak kaydet
    stego_img = Image.fromarray(pixels, "RGB")
    stego_img.save(output_path, format="PNG", optimize=False)

    return True


def _embed_to_region(flat_pixels: np.ndarray, data: bytes) -> np.ndarray:
    """
    Düzleştirilmiş piksel dizisine LSB yöntemiyle veri gömer.

    Args:
        flat_pixels: Düzleştirilmiş piksel dizisi.
        data: Gömülecek veri.

    Returns:
        np.ndarray: Veri gömülmüş piksel dizisi.
    """
    result = flat_pixels.copy()

    # Header: 32-bit veri uzunluğu
    header = struct.pack(">I", len(data))
    full_data = header + data

    # Bit dizisine çevir
    bit_array = []
    for byte in full_data:
        for bit_pos in range(7, -1, -1):
            bit_array.append((byte >> bit_pos) & 1)

    # LSB'lere göm
    for i, bit in enumerate(bit_array):
        result[i] = (result[i] & 0xFE) | bit

    return result


def _extract_from_region(flat_pixels: np.ndarray) -> bytes:
    """
    Düzleştirilmiş piksel dizisinden LSB yöntemiyle veri çıkarır.

    Args:
        flat_pixels: Düzleştirilmiş piksel dizisi.

    Returns:
        bytes: Çıkarılan veri.

    Raises:
        DecryptionError: Veri çıkarılamazsa.
    """
    # Header'dan uzunluğu oku (ilk 32 bit)
    header_bits = []
    for i in range(32):
        header_bits.append(flat_pixels[i] & 1)

    header_bytes = bytearray()
    for i in range(0, 32, 8):
        byte_val = 0
        for j in range(8):
            byte_val = (byte_val << 1) | header_bits[i + j]
        header_bytes.append(byte_val)

    data_length = struct.unpack(">I", bytes(header_bytes))[0]

    # Uzunluk doğrulama
    max_capacity = (len(flat_pixels) // 8) - 4
    if data_length <= 0 or data_length > max_capacity:
        raise DecryptionError("Geçersiz veri uzunluğu. Bu bölgede veri bulunamadı.")

    # Veri bitlerini oku
    data_bits = []
    for i in range(32, 32 + data_length * 8):
        data_bits.append(flat_pixels[i] & 1)

    # Bytes'a çevir
    data_bytes = bytearray()
    for i in range(0, len(data_bits), 8):
        byte_val = 0
        for j in range(8):
            if i + j < len(data_bits):
                byte_val = (byte_val << 1) | data_bits[i + j]
            else:
                byte_val = byte_val << 1
        data_bytes.append(byte_val)

    return bytes(data_bytes)


# ========================================================================
# Şifre ile Çıkarma
# ========================================================================

def extract_with_password(
    image_path: str,
    password: str,
    private_key_pem: bytes = None
) -> Tuple[str, bool]:
    """
    Şifre kullanarak görselden mesaj çıkarır.

    Doğru şifre girildiğinde gerçek mesaj, sahte şifre girildiğinde
    sahte mesaj döndürülür.

    Args:
        image_path: Steganografik görselin dosya yolu.
        password: Kullanıcının girdiği şifre.
        private_key_pem: RSA private key (gerçek mesaj için gerekli).

    Returns:
        Tuple[str, bool]: (mesaj, is_real) çifti.
            - is_real=True: Gerçek mesaj döndürüldü
            - is_real=False: Sahte mesaj döndürüldü

    Raises:
        DecryptionError: Hiçbir şifre eşleşmezse.
    """
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img, dtype=np.uint8)
    height, width, channels = pixels.shape
    mid_row = height // 2

    # Önce alt bölgeden (gerçek mesaj) dene
    lower_region = pixels[mid_row:, :, :].flatten()
    try:
        real_encrypted = _extract_from_region(lower_region)
        real_data = _password_decrypt(real_encrypted, password)

        # RSA ile çöz
        payload = deserialize_payload(real_data)

        if private_key_pem is not None:
            message = hybrid_decrypt(payload, private_key_pem)
            return message, True
        else:
            # Private key yoksa payload bilgisini döndür
            return "[Gerçek mesaj çözüldü ancak RSA private key gerekli]", True

    except (DecryptionError, Exception):
        pass  # Gerçek şifre değil, sahte bölgeyi dene

    # Üst bölgeden (sahte mesaj) dene
    upper_region = pixels[:mid_row, :, :].flatten()
    try:
        fake_encrypted = _extract_from_region(upper_region)
        fake_data = _password_decrypt(fake_encrypted, password)

        fake_payload = json.loads(fake_data.decode("utf-8"))
        return fake_payload.get("message", ""), False

    except (DecryptionError, Exception):
        pass  # Sahte şifre de değil

    raise DecryptionError(
        "Girilen şifre ile eşleşen bir mesaj bulunamadı. "
        "Lütfen şifrenizi kontrol edin."
    )


def has_fake_layer(image_path: str) -> bool:
    """
    Görselin sahte katman içerip içermediğini kontrol eder.

    İlk pikselin mavi kanalının 2. biti işaretçi olarak kullanılır.

    Args:
        image_path: Kontrol edilecek görselin dosya yolu.

    Returns:
        bool: Sahte katman varsa True.
    """
    try:
        img = Image.open(image_path).convert("RGB")
        pixels = np.array(img, dtype=np.uint8)
        # İlk pikselin mavi kanalının bit 1'ini kontrol et
        return bool(pixels[0, 0, 2] & 0x02)
    except Exception:
        return False

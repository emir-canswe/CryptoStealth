"""
CryptoStealth — Bütünlük Doğrulama Modülü (integrity.py)
=========================================================
Verilerin hash tabanlı bütünlük kontrolünü sağlar.
Dosya ve mesaj seviyesinde SHA-256 doğrulama işlemleri.

Yazar: CryptoStealth Projesi
"""

import hashlib
import os

from core.exceptions import IntegrityError


def compute_file_hash(file_path: str) -> str:
    """
    Dosyanın SHA-256 hash değerini hesaplar.

    Büyük dosyalar için bellek dostu chunk okuma kullanır.

    Args:
        file_path: Hash'lenecek dosyanın yolu.

    Returns:
        str: 64 karakterlik hexadecimal hash string.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)  # 8KB chunk'lar halinde oku
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()


def compute_data_hash(data: bytes) -> str:
    """
    Byte verisinin SHA-256 hash değerini hesaplar.

    Args:
        data: Hash'lenecek veri (bytes).

    Returns:
        str: 64 karakterlik hexadecimal hash string.
    """
    return hashlib.sha256(data).hexdigest()


def verify_file_integrity(file_path: str, expected_hash: str) -> bool:
    """
    Dosyanın bütünlüğünü SHA-256 hash karşılaştırmasıyla doğrular.

    Args:
        file_path: Doğrulanacak dosyanın yolu.
        expected_hash: Beklenen SHA-256 hash değeri.

    Returns:
        bool: Hash'ler eşleşiyorsa True, aksi halde False.
    """
    computed = compute_file_hash(file_path)
    return computed == expected_hash


def verify_data_integrity(data: bytes, expected_hash: str) -> bool:
    """
    Byte verisinin bütünlüğünü SHA-256 hash karşılaştırmasıyla doğrular.

    Args:
        data: Doğrulanacak veri (bytes).
        expected_hash: Beklenen SHA-256 hash değeri.

    Returns:
        bool: Hash'ler eşleşiyorsa True, aksi halde False.
    """
    computed = compute_data_hash(data)
    return computed == expected_hash


def verify_and_raise(data: bytes, expected_hash: str) -> None:
    """
    Veri bütünlüğünü doğrular, başarısız olursa IntegrityError fırlatır.

    Args:
        data: Doğrulanacak veri (bytes).
        expected_hash: Beklenen SHA-256 hash değeri.

    Raises:
        IntegrityError: Hash doğrulaması başarısız olursa.
    """
    if not verify_data_integrity(data, expected_hash):
        raise IntegrityError(
            "Veri bütünlüğü doğrulaması başarısız! "
            "Veriler aktarım sırasında değiştirilmiş olabilir. "
            f"Beklenen hash: {expected_hash[:16]}... "
            f"Hesaplanan hash: {compute_data_hash(data)[:16]}..."
        )


def generate_integrity_report(
    original_hash: str,
    current_hash: str,
    file_path: str = None
) -> dict:
    """
    Bütünlük doğrulama raporu üretir.

    Args:
        original_hash: Orijinal SHA-256 hash.
        current_hash: Mevcut SHA-256 hash.
        file_path: İlgili dosya yolu (opsiyonel).

    Returns:
        dict: Doğrulama raporu:
            {
                "is_valid": bool,
                "original_hash": str,
                "current_hash": str,
                "file_path": str veya None,
                "status": str  (Türkçe durum mesajı)
            }
    """
    is_valid = original_hash == current_hash

    return {
        "is_valid": is_valid,
        "original_hash": original_hash,
        "current_hash": current_hash,
        "file_path": file_path,
        "status": "✓ Bütünlük doğrulandı" if is_valid else "✗ Bütünlük bozulmuş!"
    }

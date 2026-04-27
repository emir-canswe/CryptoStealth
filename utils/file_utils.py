"""
CryptoStealth — Dosya İşlemleri Yardımcıları (file_utils.py)
=============================================================
Dosya okuma, yazma ve doğrulama işlemleri için yardımcı fonksiyonlar.

Yazar: CryptoStealth Projesi
"""

import os
import json
import shutil
from datetime import datetime, timezone
from typing import Optional


def ensure_directory(directory: str) -> str:
    """
    Dizinin var olduğundan emin olur, yoksa oluşturur.

    Args:
        directory: Oluşturulacak/kontrol edilecek dizin yolu.

    Returns:
        str: Dizin yolu.
    """
    os.makedirs(directory, exist_ok=True)
    return directory


def safe_write_bytes(file_path: str, data: bytes) -> bool:
    """
    Veriyi güvenli bir şekilde dosyaya yazar.
    Yazma sırasında hata olursa bozuk dosya bırakmaz.

    Args:
        file_path: Hedef dosya yolu.
        data: Yazılacak veri (bytes).

    Returns:
        bool: İşlem başarılıysa True.
    """
    # Geçici dosyaya yaz
    temp_path = file_path + ".tmp"
    try:
        ensure_directory(os.path.dirname(file_path))
        with open(temp_path, "wb") as f:
            f.write(data)
        # Atomik taşıma
        if os.path.exists(file_path):
            os.remove(file_path)
        os.rename(temp_path, file_path)
        return True
    except Exception:
        # Geçici dosyayı temizle
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def safe_read_bytes(file_path: str) -> bytes:
    """
    Dosyadan güvenli bir şekilde veri okur.

    Args:
        file_path: Kaynak dosya yolu.

    Returns:
        bytes: Okunan veri.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

    with open(file_path, "rb") as f:
        return f.read()


def read_json(file_path: str) -> dict:
    """
    JSON dosyasını okur ve dict olarak döndürür.

    Args:
        file_path: JSON dosyasının yolu.

    Returns:
        dict: JSON içeriği.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(file_path: str, data: dict) -> None:
    """
    Dict'i JSON dosyasına yazar.

    Args:
        file_path: Hedef JSON dosyasının yolu.
        data: Yazılacak dict.
    """
    ensure_directory(os.path.dirname(file_path) if os.path.dirname(file_path) else ".")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_file_info(file_path: str) -> dict:
    """
    Dosya bilgilerini döndürür.

    Args:
        file_path: Dosya yolu.

    Returns:
        dict: Dosya bilgileri (isim, boyut, değiştirme tarihi).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

    stat = os.stat(file_path)
    return {
        "name": os.path.basename(file_path),
        "path": os.path.abspath(file_path),
        "size_bytes": stat.st_size,
        "size_human": _format_size(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _format_size(size_bytes: int) -> str:
    """
    Byte değerini okunabilir formata çevirir.

    Args:
        size_bytes: Boyut (byte cinsinden).

    Returns:
        str: Okunabilir boyut string'i (ör: "2.5 MB").
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def is_valid_png(file_path: str) -> bool:
    """
    Dosyanın geçerli bir PNG dosyası olup olmadığını kontrol eder.

    PNG dosyaları her zaman aynı 8 byte header ile başlar.

    Args:
        file_path: Kontrol edilecek dosya yolu.

    Returns:
        bool: Geçerli PNG ise True.
    """
    PNG_HEADER = b'\x89PNG\r\n\x1a\n'
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
        return header == PNG_HEADER
    except Exception:
        return False


def get_image_dimensions(file_path: str) -> tuple:
    """
    PNG görselinin boyutlarını döndürür (PIL kullanmadan).

    Args:
        file_path: Görsel dosya yolu.

    Returns:
        tuple: (width, height) çifti.
    """
    from PIL import Image
    with Image.open(file_path) as img:
        return img.size


def create_backup(file_path: str) -> str:
    """
    Dosyanın yedeğini oluşturur.

    Args:
        file_path: Yedeklenecek dosya yolu.

    Returns:
        str: Yedek dosyanın yolu.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

    backup_path = file_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    return backup_path

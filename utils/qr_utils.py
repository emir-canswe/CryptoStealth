"""
CryptoStealth — QR Kod Üretme Yardımcıları (qr_utils.py)
=========================================================
RSA public key'leri QR koda dönüştürme ve kaydetme işlemleri.

QR kod ile anahtar paylaşımı, fiziksel ortamda güvenli
anahtar transferi için kullanılır.

Yazar: CryptoStealth Projesi
"""

import qrcode
from PIL import Image
from typing import Optional


def generate_qr_code(
    data: str,
    output_path: str,
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "#0f3460",
    back_color: str = "#1a1a2e"
) -> str:
    """
    Veriden QR kod görseli üretir ve kaydeder.

    Args:
        data: QR koda kodlanacak metin verisi.
        output_path: Çıktı görsel dosyasının yolu (PNG).
        box_size: Her QR modülünün piksel boyutu.
        border: QR kodun etrafındaki boşluk (modül cinsinden).
        fill_color: QR kod modüllerinin rengi.
        back_color: Arka plan rengi.

    Returns:
        str: Kaydedilen dosyanın yolu.
    """
    qr = qrcode.QRCode(
        version=None,  # Otomatik boyut
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # QR görseli oluştur
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    img.save(output_path, format="PNG")

    return output_path


def public_key_to_qr(
    public_key_pem: bytes,
    output_path: str,
    label: Optional[str] = None
) -> str:
    """
    RSA public key'i QR koda dönüştürür ve kaydeder.

    PEM formatındaki public key'i QR koda kodlar.
    Opsiyonel olarak etiket bilgisi eklenebilir.

    Args:
        public_key_pem: PEM formatında public key (bytes).
        output_path: Çıktı görsel dosyasının yolu (PNG).
        label: QR koda eklenecek opsiyonel etiket.

    Returns:
        str: Kaydedilen dosyanın yolu.
    """
    # PEM key'i string'e çevir
    key_text = public_key_pem.decode("utf-8")

    # Etiket varsa ekle
    if label:
        data = f"LABEL:{label}\n{key_text}"
    else:
        data = key_text

    return generate_qr_code(
        data=data,
        output_path=output_path,
        box_size=6,  # Public key uzun olduğu için daha küçük modüller
        border=2,
    )


def generate_fingerprint_qr(
    fingerprint: str,
    output_path: str
) -> str:
    """
    Anahtar parmak izini QR koda dönüştürür.

    Parmak izi (SHA-256 hash) doğrulama amaçlı paylaşılabilir.
    Karşı taraf QR kodu okuyarak anahtarın doğruluğunu teyit edebilir.

    Args:
        fingerprint: SHA-256 parmak izi string'i (ör: "AB:CD:EF:...").
        output_path: Çıktı görsel dosyasının yolu (PNG).

    Returns:
        str: Kaydedilen dosyanın yolu.
    """
    return generate_qr_code(
        data=f"CryptoStealth Key Fingerprint\n{fingerprint}",
        output_path=output_path,
        box_size=8,
        border=3,
        fill_color="#00ff88",
        back_color="#1a1a2e",
    )

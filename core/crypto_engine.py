"""
CryptoStealth — Kriptografi Motoru (crypto_engine.py)
=====================================================
AES-256-CBC, RSA-2048-OAEP ve SHA-256 tabanlı hibrit şifreleme işlemleri.

Desteklenen algoritmalar:
- AES-256 (CBC modu, PKCS7 padding)
- RSA-2048 (OAEP padding, SHA-256 hash)
- SHA-256 bütünlük doğrulama
- Hibrit şifreleme (AES + RSA kombinasyonu)

Yazar: CryptoStealth Projesi
"""

import os
import json
import base64
import hashlib
from datetime import datetime, timezone
from typing import Tuple, Dict

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey

from core.exceptions import DecryptionError, IntegrityError, InvalidKeyError


# ========================================================================
# AES-256-CBC Şifreleme / Çözme
# ========================================================================

def aes_encrypt(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes]:
    """
    AES-256-CBC modu ile veri şifreler.

    Args:
        plaintext: Şifrelenecek düz metin (bytes).
        key: 256-bit (32 byte) AES anahtarı.

    Returns:
        Tuple[bytes, bytes]: (şifreli_veri, iv) çifti.

    Raises:
        ValueError: Anahtar boyutu 32 byte değilse.
    """
    if len(key) != 32:
        raise ValueError("AES-256 anahtarı tam olarak 32 byte (256 bit) olmalıdır.")

    # 128-bit rastgele IV (Initialization Vector) üret
    iv = os.urandom(16)

    # PKCS7 padding uygula (blok boyutu: 128 bit)
    padder = sym_padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()

    # AES-256-CBC şifreleme
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return ciphertext, iv


def aes_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """
    AES-256-CBC modu ile şifreli veriyi çözer.

    Args:
        ciphertext: Şifreli veri (bytes).
        key: 256-bit (32 byte) AES anahtarı.
        iv: 128-bit (16 byte) başlangıç vektörü.

    Returns:
        bytes: Çözülmüş düz metin.

    Raises:
        DecryptionError: Şifre çözme başarısız olursa (yanlış anahtar/veri).
    """
    try:
        # AES-256-CBC şifre çözme
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # PKCS7 padding'i kaldır
        unpadder = sym_padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()

        return plaintext
    except Exception as e:
        raise DecryptionError(f"AES şifre çözme başarısız: {str(e)}")


# ========================================================================
# RSA-2048 Anahtar Üretme / Şifreleme / Çözme
# ========================================================================

def generate_rsa_keypair() -> Tuple[bytes, bytes]:
    """
    2048-bit RSA anahtar çifti üretir.

    Returns:
        Tuple[bytes, bytes]: (private_key_pem, public_key_pem) çifti.
        Her iki anahtar da PEM formatında bytes olarak döndürülür.
    """
    # RSA-2048 anahtar çifti üret
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Private key'i PEM formatına çevir
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Public key'i PEM formatına çevir
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem


def rsa_encrypt(data: bytes, public_key_pem: bytes) -> bytes:
    """
    RSA-2048 OAEP padding ile veri şifreler.

    Args:
        data: Şifrelenecek veri (bytes). RSA-2048 için maksimum 190 byte.
        public_key_pem: PEM formatında public key.

    Returns:
        bytes: RSA ile şifrelenmiş veri.

    Raises:
        InvalidKeyError: Public key geçersizse.
    """
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem, backend=default_backend()
        )
    except Exception as e:
        raise InvalidKeyError(f"Public key yüklenemedi: {str(e)}")

    # OAEP padding ile şifrele (SHA-256 hash)
    ciphertext = public_key.encrypt(
        data,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext


def rsa_decrypt(ciphertext: bytes, private_key_pem: bytes) -> bytes:
    """
    RSA-2048 OAEP padding ile şifreli veriyi çözer.

    Args:
        ciphertext: RSA ile şifrelenmiş veri (bytes).
        private_key_pem: PEM formatında private key.

    Returns:
        bytes: Çözülmüş veri.

    Raises:
        InvalidKeyError: Private key geçersizse veya şifre çözme başarısızsa.
    """
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None, backend=default_backend()
        )
    except Exception as e:
        raise InvalidKeyError(f"Private key yüklenemedi: {str(e)}")

    try:
        plaintext = private_key.decrypt(
            ciphertext,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext
    except Exception as e:
        raise InvalidKeyError(f"RSA şifre çözme başarısız. Yanlış anahtar olabilir: {str(e)}")


def save_keypair(private_pem: bytes, public_pem: bytes, directory: str) -> Tuple[str, str]:
    """
    RSA anahtar çiftini belirtilen dizine kaydeder.

    Args:
        private_pem: PEM formatında private key (bytes).
        public_pem: PEM formatında public key (bytes).
        directory: Anahtarların kaydedileceği dizin yolu.

    Returns:
        Tuple[str, str]: (private_key_path, public_key_path) dosya yolları.
    """
    os.makedirs(directory, exist_ok=True)

    private_path = os.path.join(directory, "private_key.pem")
    public_path = os.path.join(directory, "public_key.pem")

    with open(private_path, "wb") as f:
        f.write(private_pem)

    with open(public_path, "wb") as f:
        f.write(public_pem)

    return private_path, public_path


def load_public_key(path: str) -> bytes:
    """
    Dosyadan public key okur.

    Args:
        path: Public key dosyasının yolu.

    Returns:
        bytes: PEM formatında public key.

    Raises:
        InvalidKeyError: Dosya okunamazsa veya geçerli bir PEM değilse.
    """
    try:
        with open(path, "rb") as f:
            pem_data = f.read()
        # Geçerlilik kontrolü
        serialization.load_pem_public_key(pem_data, backend=default_backend())
        return pem_data
    except Exception as e:
        raise InvalidKeyError(f"Public key dosyası okunamadı: {str(e)}")


def load_private_key(path: str) -> bytes:
    """
    Dosyadan private key okur.

    Args:
        path: Private key dosyasının yolu.

    Returns:
        bytes: PEM formatında private key.

    Raises:
        InvalidKeyError: Dosya okunamazsa veya geçerli bir PEM değilse.
    """
    try:
        with open(path, "rb") as f:
            pem_data = f.read()
        # Geçerlilik kontrolü
        serialization.load_pem_private_key(pem_data, password=None, backend=default_backend())
        return pem_data
    except Exception as e:
        raise InvalidKeyError(f"Private key dosyası okunamadı: {str(e)}")


# ========================================================================
# SHA-256 Bütünlük Doğrulama
# ========================================================================

def compute_hash(data: bytes) -> str:
    """
    Verinin SHA-256 hash değerini hesaplar.

    Args:
        data: Hash'lenecek veri (bytes).

    Returns:
        str: 64 karakterlik hexadecimal hash string.
    """
    return hashlib.sha256(data).hexdigest()


def verify_hash(data: bytes, expected_hash: str) -> bool:
    """
    Verinin SHA-256 hash'ini beklenen değerle karşılaştırır.

    Args:
        data: Doğrulanacak veri (bytes).
        expected_hash: Beklenen hash değeri (hex string).

    Returns:
        bool: Hash'ler eşleşiyorsa True, değilse False.
    """
    computed = compute_hash(data)
    return computed == expected_hash


# ========================================================================
# Hibrit Şifreleme (AES-256 + RSA-2048)
# ========================================================================

def hybrid_encrypt(message: str, public_key_pem: bytes) -> dict:
    """
    Hibrit şifreleme: Mesajı AES-256 ile şifreler, AES anahtarını RSA ile korur.

    Akış:
    1. Rastgele 256-bit AES anahtarı üretilir
    2. Mesaj AES-256-CBC ile şifrelenir
    3. AES anahtarı RSA-2048-OAEP ile şifrelenir
    4. Mesajın SHA-256 hash'i hesaplanır

    Args:
        message: Şifrelenecek metin mesajı.
        public_key_pem: Alıcının PEM formatında public key'i.

    Returns:
        dict: Şifreli payload içeren sözlük:
            - aes_ciphertext (bytes): AES şifreli mesaj
            - iv (bytes): AES başlangıç vektörü
            - encrypted_aes_key (bytes): RSA ile şifrelenmiş AES anahtarı
            - message_hash (str): Orijinal mesajın SHA-256 hash'i
            - version (str): Protokol versiyonu
            - timestamp (str): Şifreleme zamanı (ISO 8601)
    """
    # Mesajı bytes'a çevir
    message_bytes = message.encode("utf-8")

    # Rastgele 256-bit AES anahtarı üret
    aes_key = os.urandom(32)

    # Mesajı AES-256-CBC ile şifrele
    ciphertext, iv = aes_encrypt(message_bytes, aes_key)

    # AES anahtarını RSA ile şifrele
    encrypted_aes_key = rsa_encrypt(aes_key, public_key_pem)

    # Mesajın bütünlük hash'ini hesapla
    message_hash = compute_hash(message_bytes)

    # Zaman damgası
    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "aes_ciphertext": ciphertext,
        "iv": iv,
        "encrypted_aes_key": encrypted_aes_key,
        "message_hash": message_hash,
        "version": "1.0",
        "timestamp": timestamp,
    }


def hybrid_decrypt(payload: dict, private_key_pem: bytes) -> str:
    """
    Hibrit şifre çözme: RSA ile AES anahtarını, AES ile mesajı çözer.

    Akış:
    1. RSA ile AES anahtarı çözülür
    2. AES ile mesaj çözülür
    3. Mesajın hash'i doğrulanır

    Args:
        payload: hybrid_encrypt() çıktısı olan şifreli payload dict.
        private_key_pem: Alıcının PEM formatında private key'i.

    Returns:
        str: Çözülmüş orijinal mesaj.

    Raises:
        DecryptionError: Şifre çözme başarısız olursa.
        IntegrityError: Hash doğrulaması başarısız olursa.
    """
    try:
        # RSA ile AES anahtarını çöz
        aes_key = rsa_decrypt(payload["encrypted_aes_key"], private_key_pem)
    except InvalidKeyError as e:
        raise DecryptionError(f"AES anahtarı çözülemedi: {str(e)}")

    # AES ile mesajı çöz
    plaintext_bytes = aes_decrypt(payload["aes_ciphertext"], aes_key, payload["iv"])

    # Mesajı string'e çevir
    message = plaintext_bytes.decode("utf-8")

    # Bütünlük doğrulaması
    if "message_hash" in payload:
        if not verify_hash(plaintext_bytes, payload["message_hash"]):
            raise IntegrityError(
                "Mesaj bütünlüğü doğrulanamadı! "
                "Veri aktarım sırasında değiştirilmiş olabilir."
            )

    return message


# ========================================================================
# Payload Serileştirme / Deserileştirme
# ========================================================================

def serialize_payload(payload: dict) -> bytes:
    """
    Şifreli payload'ı JSON formatına serileştirir.
    bytes değerleri base64 olarak kodlar.

    Args:
        payload: hybrid_encrypt() çıktısı.

    Returns:
        bytes: UTF-8 kodlanmış JSON verisi.
    """
    serializable = {}
    for key, value in payload.items():
        if isinstance(value, bytes):
            serializable[key] = base64.b64encode(value).decode("ascii")
        else:
            serializable[key] = value

    # Ek bilgiler
    serializable["algorithm"] = "AES-256-CBC + RSA-2048-OAEP"

    return json.dumps(serializable, indent=2).encode("utf-8")


def deserialize_payload(data: bytes) -> dict:
    """
    JSON formatındaki payload'ı dict'e deserileştirir.
    base64 kodlanmış değerleri bytes'a çevirir.

    Args:
        data: UTF-8 kodlanmış JSON verisi.

    Returns:
        dict: Orijinal payload yapısı.

    Raises:
        DecryptionError: JSON parse edilemezse.
    """
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise DecryptionError(f"Payload verisi çözümlenemedi: {str(e)}")

    # base64 kodlanmış alanları bytes'a çevir
    bytes_fields = ["aes_ciphertext", "iv", "encrypted_aes_key"]
    for field in bytes_fields:
        if field in parsed and isinstance(parsed[field], str):
            try:
                parsed[field] = base64.b64decode(parsed[field])
            except Exception:
                raise DecryptionError(f"'{field}' alanı base64 decode edilemedi.")

    return parsed


def get_key_fingerprint(key_pem: bytes) -> str:
    """
    PEM formatındaki bir anahtarın SHA-256 parmak izini hesaplar.

    Args:
        key_pem: PEM formatında anahtar (public veya private).

    Returns:
        str: İki karakter arası ':' ile ayrılmış SHA-256 parmak izi.
             Örnek: "AB:CD:EF:12:34:..."
    """
    hash_bytes = hashlib.sha256(key_pem).digest()
    return ":".join(f"{b:02X}" for b in hash_bytes)

import unittest
import os
import shutil

from core.crypto_engine import generate_rsa_keypair, hybrid_encrypt, hybrid_decrypt
from core.integrity import compute_data_hash, verify_data_integrity


class TestCryptoStealthCore(unittest.TestCase):

    def setUp(self):
        # Test öncesi geçici anahtarlar üret
        self.private_pem, self.public_pem = generate_rsa_keypair()

    def test_hybrid_encryption_decryption(self):
        """Hibrit şifreleme ve çözme işleminin doğru çalışıp çalışmadığını test eder."""
        original_message = "Gizli test mesaji! 123 @#$"
        
        # Şifrele
        payload = hybrid_encrypt(original_message, self.public_pem)
        
        # Şifrelenmiş mesajın orijinalinden farklı olduğunu doğrula
        self.assertNotEqual(payload["aes_ciphertext"], original_message.encode('utf-8'))
        
        # Çöz
        decrypted_message = hybrid_decrypt(payload, self.private_pem)
        
        # Orijinal mesaja geri dönüldüğünü doğrula
        self.assertEqual(original_message, decrypted_message)

    def test_integrity_hash(self):
        """SHA-256 hash doğrulamasını test eder."""
        data = b"Bazi rastgele veriler..."
        expected_hash = compute_data_hash(data)
        
        # Doğru hash
        self.assertTrue(verify_data_integrity(data, expected_hash))
        
        # Yanlış veri
        self.assertFalse(verify_data_integrity(b"Degistirilmis veriler...", expected_hash))


if __name__ == '__main__':
    unittest.main()

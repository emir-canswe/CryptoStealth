"""
CryptoStealth — Özel Hata Sınıfları
====================================
Tüm uygulama genelinde kullanılan özel exception tanımları.
Her hata sınıfı, kullanıcıya Türkçe mesaj döndürmeyi destekler.
"""


class CryptoStealthError(Exception):
    """CryptoStealth uygulamasının temel hata sınıfı."""

    def __init__(self, message: str = "Bilinmeyen bir hata oluştu."):
        self.message = message
        super().__init__(self.message)


class DecryptionError(CryptoStealthError):
    """Şifre çözme işlemi sırasında oluşan hatalar.
    
    Yanlış anahtar, bozuk veri veya hatalı şifre durumlarında fırlatılır.
    """

    def __init__(self, message: str = "Şifre çözme başarısız. Anahtar veya veri hatalı olabilir."):
        super().__init__(message)


class IntegrityError(CryptoStealthError):
    """Veri bütünlüğü doğrulama hatası.
    
    Hash kontrolü başarısız olduğunda fırlatılır.
    Verinin aktarım sırasında değiştirilmiş olabileceğini gösterir.
    """

    def __init__(self, message: str = "Veri bütünlüğü doğrulanamadı. Veri değiştirilmiş olabilir."):
        super().__init__(message)


class CapacityError(CryptoStealthError):
    """Görsel kapasite aşım hatası.
    
    Gömülecek veri, görselin taşıyabileceği kapasiteden büyük olduğunda fırlatılır.
    """

    def __init__(self, message: str = "Veri boyutu görselin kapasitesini aşıyor."):
        super().__init__(message)


class ExtractionError(CryptoStealthError):
    """Steganografik veri çıkarma hatası.
    
    Görselden veri çıkarılırken hata oluştuğunda fırlatılır.
    Görsel bozuk veya steganografik veri içermiyor olabilir.
    """

    def __init__(self, message: str = "Görselden veri çıkarılamadı. Görsel bozuk veya veri içermiyor olabilir."):
        super().__init__(message)


class InvalidKeyError(CryptoStealthError):
    """Geçersiz anahtar hatası.
    
    RSA anahtarı yüklenemediğinde veya geçersiz olduğunda fırlatılır.
    Python'ın yerleşik KeyError sınıfıyla çakışmayı önlemek için
    InvalidKeyError adı kullanılmıştır.
    """

    def __init__(self, message: str = "Geçersiz veya bozuk anahtar. Lütfen anahtarı kontrol edin."):
        super().__init__(message)

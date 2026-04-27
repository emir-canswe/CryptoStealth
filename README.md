# CryptoStealth

**CryptoStealth**, steganografi (bilgi gizleme) ve kriptografi (şifreleme) tekniklerini birleştirerek üst düzey güvenlik sağlayan bir masaüstü uygulamasıdır. "Bilgi Güvenliği" dersi projesi kapsamında geliştirilmiştir.

Uygulama, gizlemek istediğiniz metin tabanlı mesajları önce AES-256 ve RSA-2048 hibrit şifreleme ile güvence altına alır, ardından LSB (Least Significant Bit) steganografi yöntemi ile sıradan bir PNG görselinin pikselleri arasına yerleştirir. Dışarıdan bakıldığında görselin orijinalinden hiçbir farkı yoktur.

## Özellikler

- **Hibrit Şifreleme:** AES-256 (simetrik) ve RSA-2048 (asimetrik) birleşimi.
- **LSB Steganografi:** Kayıpsız PNG formatında piksellerin en düşük anlamlı bitlerine veri gömme.
- **Tuzak (Sahte) Katman:** Yanlış şifre girildiğinde inandırıcı ama sahte bir mesaj döndüren çift katmanlı yapı.
- **Bütünlük Kontrolü:** Verilerin değiştirilip değiştirilmediğini anlamak için SHA-256 doğrulama.
- **Piksel Analizi:** Görsel üzerinde steganografik müdahaleyi analiz edebilme (Fark haritası, PSNR, LSB dağılımı).
- **Brute-Force Koruması:** Yanlış şifre denemelerinde katlanarak artan bekleme süreleri.
- **QR Kod Entegrasyonu:** Public key'leri fiziksel olarak güvenli şekilde paylaşabilmek için QR kod üretimi.

## Gereksinimler ve Kurulum

Proje Python 3.10 veya üzeri sürümlerde çalışmaktadır. 

1. Proje dizinine gidin.
2. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. Uygulamayı başlatın:
   ```bash
   python main.py
   ```

## Kullanım Kılavuzu

### 1. Anahtar Üretimi (🔑 Anahtar Yönetimi)
Öncelikle mesajı alacak kişinin bir RSA anahtar çifti oluşturması gerekir.
- Sekmeden "Yeni RSA-2048 Anahtar Çifti Üret" butonuna tıklayın.
- İki dosya oluşacaktır: `public_key.pem` (herkese açık) ve `private_key.pem` (gizli).
- Public key'i QR kod olarak da dışa aktarabilirsiniz.

### 2. Mesaj Gömme (🔒 Gömme)
- Bir kaynak görsel seçin (minimum 100x100 piksel, PNG/JPG).
- Gizlenecek mesajı yazın.
- Alıcının `public_key.pem` dosyasını seçin.
- (Opsiyonel) "Sahte Mesaj" katmanını açın ve yanlış bir şifre girildiğinde gösterilecek bir metin ile iki farklı şifre belirleyin.
- "Şifrele ve Göm" butonuna basarak gizli veriyi taşıyan yeni PNG dosyanızı oluşturun.

### 3. Mesaj Çıkarma (🔓 Çıkarma)
- Size gönderilen steganografik PNG görselini seçin.
- Kendi `private_key.pem` dosyanızı seçin.
- Eğer mesajda sahte katman (tuzak) kullanıldıysa şifrenizi girin.
- "Çıkar ve Çöz" butonu ile orijinal mesajı okuyun.

### 4. Piksel Analizi (📊 Piksel Analizi)
- Orijinal görsel ile şüpheli görseli yükleyerek aralarındaki PSNR farkını görebilirsiniz.
- Uygulama, fark olan pikselleri kırmızı renkle vurgulayan bir analiz haritası çıkartacaktır.

## Güvenlik Notları
- Şifrelenmiş görsel mutlaka **PNG** formatında aktarılmalıdır. WhatsApp gibi platformlar görselleri sıkıştırıp (JPEG'e dönüştürerek) pikselleri bozar ve gömülü veriyi yok eder. Görselleri dosya olarak (.zip vb.) iletiniz.
- `private_key.pem` dosyasını asla kimseyle paylaşmayınız.

## Eğitim Amacı
Bu proje steganografi ve kriptografi tekniklerinin entegrasyonunu göstermek için eğitim amacıyla oluşturulmuştur.

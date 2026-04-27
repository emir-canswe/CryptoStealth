# CryptoStealth: Projenin Amacı ve Çözdüğü Sorunlar

## Temel Problem
Dijital iletişimde gizlilik denildiğinde akla ilk olarak verilerin şifrelenmesi (Kriptografi) gelir. Ancak geleneksel şifreleme yöntemlerinin büyük bir dezavantajı vardır: **Şifrelenmiş bir dosya, "Benim içimde gizli ve önemli bir veri var" mesajı verir.** Bu durum, dosyayı doğrudan siber saldırganların hedefi haline getirir. Şifre kırılamasa bile, iletişim kurduğunuzun tespit edilmesi veya dosyanın imha edilmesi başlı başına bir güvenlik açığıdır.

## CryptoStealth'in Çözümü
CryptoStealth, bu sorunu çözmek için Kriptografi ve Steganografi'yi (bilgi gizleme sanatı) tek bir sistemde birleştirir. Temel prensibi şudur: **"Saldırganların göremediği bir şeyi kıramazlar."**

Programın temel işlevleri ve çalışma mantığı şu şekildedir:

### 1. Kırılamaz Matematiksel Zırh (Kriptografi)
Göndermek istediğiniz metin, öncelikle günümüzün en güvenilir askeri düzey algoritmalarıyla (AES-256 ve RSA-2048 hibrit yapısı) şifrelenir. Bu sayede veri, anahtar olmadan hiçbir şekilde anlaşılamaz bir karakter yığınına dönüşür.

### 2. Görünmezlik Pelerini (Steganografi)
Elde edilen şifreli veri, sıradan bir PNG görselinin (örneğin bir manzara fotoğrafının) pikselleri arasına yerleştirilir. LSB (Least Significant Bit) algoritması kullanılarak piksellerin en düşük anlamlı bitleri değiştirildiği için, fotoğraf dışarıdan bakıldığında hiçbir farklılık göstermez. Veri, masum bir fotoğrafın içinde adeta "görünmez" olur.

### 3. Hedef Şaşırtma (Sahte Tuzak Katmanı)
Eğer bir şüphe olur da birisi şifreyi çözmeye zorlarsa, CryptoStealth "çift katmanlı" bir güvenlik sunar. Doğru şifre girildiğinde asıl mesaj açılır. Ancak programa bir "tuzak şifre" ve "sahte mesaj" eklenmişse; saldırgan yanlış şifreyi girdiğinde sahte bir mesajla (örneğin: "Proje dosyaları yarına yetişecek") karşılaşır ve asıl gizli veriye ulaştığını sanarak işlemi sonlandırır.

## Özet Olarak Ne İşe Yarar?
CryptoStealth; gazetecilerin, araştırmacıların, şirketlerin veya sadece kişisel gizliliğine önem veren bireylerin, iletişimlerini sansür veya takip edilme riski olmadan, "sıradan bir fotoğraf paylaşıyormuş gibi" güvenle gerçekleştirebilmelerini sağlar. Bilginin hem içeriğini matematikle korur hem de varlığını gözlerden saklar.

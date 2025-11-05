# EduCoach - Kişisel Sınav Koçu Platformu

EduCoach, AI destekli kişiselleştirilmiş sınav koçluğu platformudur. Öğrencilerin sınavlarına hazırlanması için ChatGPT, Gemini veya Claude AI'larından birini seçerek özel çalışma planları oluşturur.

## 🚀 Özellikler

### 🤖 AI Seçimi
- **ChatGPT**: Detaylı açıklamalar ve kapsamlı planlar
- **Gemini**: Hızlı ve etkili çözümler
- **Claude**: Analitik ve mantıklı yaklaşımlar

### 📚 Kişisel Çalışma Planları
- Sınav tarihi, mevcut seviye ve hedef nota göre özelleştirilmiş planlar
- Haftalık detaylı konu dağılımı
- Günlük çalışma saatleri önerileri

### 📄 Doküman Paylaşım Sistemi
- Doküman yükleme ve kredi kazanma
- Diğer öğrencilerin paylaştığı kaynaklara erişim
- Konu bazında filtreleme ve arama

### 🎯 Kullanıcı Dostu Arayüz
- Modern ve responsive tasarım
- Bootstrap 5 ile geliştirilmiş
- Font Awesome ikonları
- Gradient renkler ve animasyonlar

## 🛠️ Teknolojiler

### Backend
- **Python Flask**: Web framework
- **PostgreSQL**: Veritabanı
- **SQLAlchemy**: ORM
- **Flask-Login**: Kullanıcı oturum yönetimi
- **Flask-WTF**: Form yönetimi

### Frontend
- **HTML5/CSS3**: Temel yapı
- **Bootstrap 5**: UI framework
- **Font Awesome**: İkonlar
- **JavaScript**: İnteraktif özellikler

### AI Entegrasyonları
- **OpenAI API**: ChatGPT
- **Google Generative AI**: Gemini
- **Anthropic API**: Claude

## 📦 Kurulum

### Gereksinimler
- Python 3.8+
- PostgreSQL 12+
- pip

### Adımlar

1. **Projeyi klonlayın**
```bash
git clone <repository-url>
cd HHackathon
```

2. **Sanal ortam oluşturun**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Bağımlılıkları yükleyin**
```bash
pip install -r requirements.txt
```

4. **PostgreSQL veritabanını oluşturun**
```sql
CREATE DATABASE hackathon;
```

5. **Çevre değişkenlerini ayarlayın**
```bash
# config.env dosyasını düzenleyin
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

6. **Uygulamayı çalıştırın**
```bash
python app.py
```

Uygulama `http://localhost:5000` adresinde çalışacaktır.

## 🗄️ Veritabanı Yapısı

### Tablolar
- **users**: Kullanıcı bilgileri
- **courses**: Kurs/sınav bilgileri
- **study_plans**: Çalışma planları
- **tests**: Test sonuçları
- **documents**: Paylaşılan dokümanlar

## 🎨 Sayfa Yapısı

### Ana Sayfalar
- **Ana Sayfa**: Platform tanıtımı ve özellikler
- **Kayıt Ol**: Yeni kullanıcı kaydı
- **Giriş Yap**: Mevcut kullanıcı girişi
- **Dashboard**: Ana kontrol paneli

### Kullanıcı Sayfaları
- **AI Seçimi**: Tercih edilen AI'yı belirleme
- **Kurs Oluştur**: Yeni sınav/kurs ekleme
- **Kurs Detayı**: Çalışma planı görüntüleme
- **Dokümanlar**: Paylaşılan kaynaklar

## 🔧 API Endpoints

### Kimlik Doğrulama
- `POST /register` - Kullanıcı kaydı
- `POST /login` - Kullanıcı girişi
- `GET /logout` - Çıkış yapma

### Kurs Yönetimi
- `GET /dashboard` - Ana panel
- `GET/POST /create-course` - Kurs oluşturma
- `GET /course/<id>` - Kurs detayı

### AI ve Dokümanlar
- `GET/POST /ai-selection` - AI tercihi
- `GET /documents` - Doküman listesi

## 🎯 Kullanım Senaryoları

### 1. Yeni Kullanıcı
1. Kayıt ol
2. AI tercihini belirle
3. İlk kursunu oluştur
4. AI'nın oluşturduğu planı takip et

### 2. Doküman Paylaşımı
1. Doküman yükle
2. 100 kredi kazan
3. Diğer dokümanları görüntüle
4. İhtiyaç duyulanları indir

### 3. Çalışma Planı Takibi
1. Kurs detayına git
2. Haftalık planları görüntüle
3. Konuları takip et
4. İlerlemeyi değerlendir

## 🚀 Gelecek Özellikler

- [ ] Test çözme sistemi
- [ ] İlerleme takibi ve grafikler
- [ ] Doküman yükleme sistemi
- [ ] Mobil uygulama
- [ ] Bildirim sistemi
- [ ] Sosyal özellikler

## 📝 Lisans

Bu proje hackathon amaçlı geliştirilmiştir.

---

**EduCoach** ile sınavlarınızda başarıya ulaşın! 🎓✨

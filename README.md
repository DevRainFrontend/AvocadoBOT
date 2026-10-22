# AvocadoBOT

Eski 2024'te arkadaşlarla takılırken yazdığım Discord botu. İçinde moderasyon, eğlence, Gemini AI soru-cevap, çeviri ve ufak tefek araçlar var. Artık kullanmadığım için açık kaynak bırakıyorum.

### Kurulum

Gereken kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

`.env` dosyasını açıp bot tokeninizi ve anahtarları yazın:
```env
DISCORD_TOKEN=burayatoken
COMMAND_PREFIX=a!
GEMINI_API_KEY=burayageminikey
OPENWEATHER_API_KEY=burayahawakey
MODERATOR_IDS=burayaownerid
STATUS_CHANNEL_ID=burayakanalid
SUPPORT_SERVER_URL=https://discord.gg/burayasunucuid
```

Çalıştırmak için:
```bash
python bot.py
```

### Komutlar (Prefix: `a!`)

- `a!yardım` - Butonlu yardım menüsü
- `a!sorusor <soru>` - Gemini'ye soru sorar
- `a!hesapla <işlem>` - Hesap makinesi
- `a!hava <şehir>` - Hava durumu
- `a!çevir <dil> <metin>` - Çeviri yapar
- `a!sil <sayı>` - Mesaj siler
- `a!nuke` - Kanalı silip tekrar açar
- `a!lock` / `a!unlock` - Kanalı kilitler / açar
- `a!ban <kişi>` - Sunucudan banlar
- `a!jail` / `a!unjail` - Jaile atar / çıkarır
- `a!avatar` - Profil resmi gösterir
- `a!zarat` - 1-6 arası zar atar
- `a!tokat <kişi>` - Tokat atar
- `a!ping` - Botun pingini gösterir

İstediğiniz gibi alıp editleyip kullanabilirsiniz.

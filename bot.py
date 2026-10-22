import os
import sys
import time
import random
import asyncio
import ast
import operator
import math
from datetime import timedelta
import aiohttp
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

import ai
from googletrans import Translator, LANGUAGES

load_dotenv()

# Ayarlar
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "burayatoken")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "a!")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "burayahawakey")
STATUS_CHANNEL_ID = int(os.getenv("STATUS_CHANNEL_ID", "0"))
SUPPORT_SERVER_URL = os.getenv("SUPPORT_SERVER_URL", "https://discord.gg/burayasunucuid")

# Yetkililer
raw_mod_ids = os.getenv("MODERATOR_IDS", "burayaownerid")
MODERATOR_IDS = [int(i.strip()) for i in raw_mod_ids.split(",") if i.strip().isdigit()]

# Bot durumu
STATUS_LIST = [
    "Version 3.0",
    "AvocadoBOT",
    "Sunucuları İzliyorum",
    f"{COMMAND_PREFIX}yardım"
]

MORS_ALFABE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 'G': '--.', 'H': '....',
    'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---', 'P': '.--.',
    'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..',
    '1': '.----', '2': '..---', '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.', '0': '-----',
    ' ': '/'
}

# Güvenli hesap makinesi (eval yerine)
class SafeCalculator:
    _OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    _UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }
    _NAMES = {
        "pi": math.pi, "e": math.e, "tau": math.tau,
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10, "ceil": math.ceil, "floor": math.floor,
    }

    @classmethod
    def calculate(cls, expr: str):
        if not expr or not expr.strip():
            raise ValueError("Bir işlem girmelisin.")
        if len(expr) > 200:
            raise ValueError("İfade çok uzun.")
        try:
            tree = ast.parse(expr.strip(), mode='eval')
        except SyntaxError:
            raise ValueError("Geçersiz matematiksel ifade.")

        res = cls._eval(tree.body)
        if isinstance(res, complex) or math.isinf(res) or math.isnan(res):
            raise ValueError("Geçersiz sonuç.")
        if isinstance(res, float) and res.is_integer():
            return int(res)
        return round(res, 6) if isinstance(res, float) else res

    @classmethod
    def _eval(cls, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Sadece sayılar geçerli.")
        elif isinstance(node, ast.BinOp):
            op = type(node.op)
            if op not in cls._OPS:
                raise ValueError("Desteklenmeyen işlem.")
            l = cls._eval(node.left)
            r = cls._eval(node.right)
            if op is ast.Pow and (abs(r) > 1000 or (abs(l) > 1000 and r > 10)):
                raise ValueError("Üs çok büyük.")
            if op in (ast.Div, ast.FloorDiv, ast.Mod) and r == 0:
                raise ValueError("0'a bölünemez.")
            return cls._OPS[op](l, r)
        elif isinstance(node, ast.UnaryOp):
            op = type(node.op)
            if op not in cls._UNARY_OPS:
                raise ValueError("Desteklenmeyen tekli işlem.")
            return cls._UNARY_OPS[op](cls._eval(node.operand))
        elif isinstance(node, ast.Name):
            if node.id in cls._NAMES and not callable(cls._NAMES[node.id]):
                return cls._NAMES[node.id]
            raise ValueError(f"Bilinmeyen değer: {node.id}")
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Geçersiz fonksiyon.")
            fn = node.func.id
            if fn not in cls._NAMES or not callable(cls._NAMES[fn]):
                raise ValueError(f"Bilinmeyen fonksiyon: {fn}")
            args = [cls._eval(a) for a in node.args]
            return cls._NAMES[fn](*args)
        raise ValueError("Geçersiz karakter veya işlem.")

# Bot kurulumu
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)
bot.start_time = time.time()
translator = Translator()

def is_bot_owner(ctx):
    return ctx.author.id in MODERATOR_IDS

def is_moderator(ctx):
    if ctx.author.id in MODERATOR_IDS:
        return True
    if ctx.guild:
        p = ctx.author.guild_permissions
        return p.administrator or p.manage_guild or p.manage_roles
    return False

def random_password(length: int) -> str:
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
    return ''.join(random.choice(chars) for _ in range(length))

# Yardım menüsü
class HelpView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("Bu menüyü sadece komutu yazan kullanabilir.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Admin Komutları", style=discord.ButtonStyle.danger, emoji="⚙️")
    async def admin_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙️ Admin Komutları",
            color=discord.Color.red(),
            description=(
                f"`{COMMAND_PREFIX}nuke` - Kanalı silip tekrar açar\n"
                f"`{COMMAND_PREFIX}lock` - Kanalı kilitler\n"
                f"`{COMMAND_PREFIX}unlock` - Kanal kilidini açar\n"
                f"`{COMMAND_PREFIX}ban <kişi> [sebep]` - Kullanıcıyı banlar\n"
                f"`{COMMAND_PREFIX}idban <id> [sebep]` - ID ile banlar\n"
                f"`{COMMAND_PREFIX}sil <sayı>` - Toplu mesaj siler\n"
                f"`{COMMAND_PREFIX}herkesetagver <tag>` - Herkese tag ekler\n"
                f"`{COMMAND_PREFIX}tagsıfırla` - Tagleri temizler\n"
                f"`{COMMAND_PREFIX}jail <kişi>` - Jaile atar\n"
                f"`{COMMAND_PREFIX}unjail <kişi>` - Jaili kaldırır\n"
                f"`{COMMAND_PREFIX}kanallarasüresınırıkoy <saniye>` - Yavaş mod ayarlar\n"
                f"`{COMMAND_PREFIX}busunucuyukopyala <kaynak_id>` - Sunucu yapısını kopyalar\n"
                f"`{COMMAND_PREFIX}rollerisil` - Rolleri siler"
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Eğlence", style=discord.ButtonStyle.success, emoji="🎉")
    async def fun_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎉 Eğlence Komutları",
            color=discord.Color.green(),
            description=(
                f"`{COMMAND_PREFIX}hava <şehir>` - Hava durumunu gösterir\n"
                f"`{COMMAND_PREFIX}mors <metin>` - Mors alfabesine çevirir\n"
                f"`{COMMAND_PREFIX}tersinecevir <metin>` - Metni tersten yazar\n"
                f"`{COMMAND_PREFIX}sifreolustur [uzunluk]` - Rastgele şifre verir\n"
                f"`{COMMAND_PREFIX}zarat` - Zar atar (1-6)\n"
                f"`{COMMAND_PREFIX}avatar [kullanıcı]` - Profil fotoğrafını gösterir\n"
                f"`{COMMAND_PREFIX}tokat <kullanıcı>` - Birine tokat atar\n"
                f"`{COMMAND_PREFIX}çevir <dil> <metin>` - Metni çevirir\n"
                f"`{COMMAND_PREFIX}durumlist` - Çevrimiçi üyeleri listeler"
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Yapay Zeka & Araçlar", style=discord.ButtonStyle.primary, emoji="🤖")
    async def ai_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🤖 Yapay Zeka & Araçlar",
            color=discord.Color.blue(),
            description=(
                f"`{COMMAND_PREFIX}sorusor <soru>` - Gemini'ye soru sorar\n"
                f"`{COMMAND_PREFIX}hesapla <işlem>` - Matematik işlemi yapar\n"
                f"`{COMMAND_PREFIX}ping` - Botun gecikmesini gösterir\n"
                f"`{COMMAND_PREFIX}tanıt` - Bot bilgilerini gösterir\n"
                f"`{COMMAND_PREFIX}sunucum` - Destek sunucusu linki\n"
                f"`{COMMAND_PREFIX}yardimcagrisi <sebep>` - Destek çağrısı yollar"
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    if not change_status.is_running():
        change_status.start()

    uptime_sec = round(time.time() - bot.start_time)
    formatted_uptime = str(timedelta(seconds=uptime_sec))
    shard_count = bot.shard_count if bot.shard_count else 1
    ping = round(bot.latency * 1000)

    print(f"AvocadoBOT açıldı! Giriş yapılan: {bot.user}")
    print(f"Sunucu sayısı: {len(bot.guilds)} | Ping: {ping}ms")

    if STATUS_CHANNEL_ID != 0:
        try:
            channel = bot.get_channel(STATUS_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="AvocadoBOT Açıldı!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Açılış Süresi", value=f"{formatted_uptime}", inline=True)
                embed.add_field(name="Ping", value=f"{ping} ms", inline=True)
                embed.add_field(name="Sunucu Sayısı", value=f"{len(bot.guilds)}", inline=True)
                embed.set_footer(text="AvocadoBOT • 2024")
                await channel.send(embed=embed)
        except Exception as e:
            print(f"Kanal mesajı gönderilemedi: {e}")

@tasks.loop(seconds=10)
async def change_status():
    status = STATUS_LIST.pop(0)
    STATUS_LIST.append(status)
    await bot.change_presence(activity=discord.Game(name=status))

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    if message.content.strip().lower() in ["sa", "selam", "selamun aleykum"]:
        await message.channel.send(f"Aleyküm Selam {message.author.mention}, hoş geldin!")

    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
    print(f"Yeni sunucuya katıldım: {guild.name} ({guild.id})")
    if STATUS_CHANNEL_ID != 0:
        try:
            ch = bot.get_channel(STATUS_CHANNEL_ID)
            if ch:
                embed = discord.Embed(title="Yeni Sunucuya Eklendim!", color=discord.Color.blue())
                embed.add_field(name="Sunucu", value=guild.name, inline=True)
                embed.add_field(name="Üye Sayısı", value=str(guild.member_count), inline=True)
                embed.add_field(name="Kurucu", value=str(guild.owner), inline=True)
                await ch.send(embed=embed)
        except:
            pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Komut Bulunamadı",
            description=f"Böyle bir komut yok. Komutlar için `{COMMAND_PREFIX}yardım` yazabilirsin.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=6)
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("Bu komutu kullanmak için yetkin yok!", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Eksik parametre girdin! Parametre: `{error.param.name}`", delete_after=6)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Hatalı parametre: {error}", delete_after=6)
    else:
        print(f"Hata ({ctx.command}): {error}")
        await ctx.send(f"Bir hata oluştu: `{error}`")

# Komutlar
@bot.command(name="yardım", aliases=["help"])
async def yardım(ctx):
    embed = discord.Embed(
        title="🥑 AvocadoBOT Yardım Menüsü",
        description="Aşağıdaki butonlara tıklayarak komutları görebilirsin.",
        color=0x43B581
    )
    embed.set_footer(text=f"Prefix: {COMMAND_PREFIX}")
    await ctx.send(embed=embed, view=HelpView(ctx.author))

@bot.command(name="ping")
async def ping(ctx):
    ws_ping = round(bot.latency * 1000)
    t = time.time()
    msg = await ctx.send("Ölçülüyor...")
    resp_ping = round((time.time() - t) * 1000)

    embed = discord.Embed(title="Ping Değerleri", color=discord.Color.green())
    embed.add_field(name="Websocket", value=f"`{ws_ping} ms`", inline=True)
    embed.add_field(name="Mesaj Gecikmesi", value=f"`{resp_ping} ms`", inline=True)
    await msg.edit(content=None, embed=embed)

@bot.command(name="tanıt")
async def tanıt(ctx):
    sec = round(time.time() - bot.start_time)
    embed = discord.Embed(title="🥑 AvocadoBOT", color=0x2ECC71)
    embed.add_field(name="Geliştirici", value="AvocadoBOT", inline=True)
    embed.add_field(name="Versiyon", value="Version 3.0", inline=True)
    embed.add_field(name="Tarih", value="2024", inline=True)
    embed.add_field(name="Sunucu Sayısı", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="Kullanıcı Sayısı", value=f"{len(bot.users)}", inline=True)
    embed.add_field(name="Açık Kalma Süresi", value=str(timedelta(seconds=sec)), inline=True)
    embed.add_field(name="Destek Sunucusu", value=f"[Tıkla]({SUPPORT_SERVER_URL})", inline=False)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="sunucum")
async def sunucum(ctx):
    await ctx.send(f"Destek sunucusu: {SUPPORT_SERVER_URL}")

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"{target.display_name} profil fotoğrafı", color=discord.Color.blue())
    embed.set_image(url=target.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="durumlist")
async def durum_listesi(ctx):
    if not ctx.guild:
        return
    online = [m.name for m in ctx.guild.members if m.status == discord.Status.online]
    dnd = [m.name for m in ctx.guild.members if m.status == discord.Status.dnd]
    idle = [m.name for m in ctx.guild.members if m.status == discord.Status.idle]
    offline = [m.name for m in ctx.guild.members if m.status in (discord.Status.offline, discord.Status.invisible)]

    embed = discord.Embed(title=f"{ctx.guild.name} Durum Listesi", color=discord.Color.teal())
    embed.add_field(name="🟢 Çevrimiçi", value=f"{len(online)}", inline=True)
    embed.add_field(name="🔴 Rahatsız Etmeyin", value=f"{len(dnd)}", inline=True)
    embed.add_field(name="🟡 Boşta", value=f"{len(idle)}", inline=True)
    embed.add_field(name="⚫ Çevrimdışı", value=f"{len(offline)}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="yardimcagrisi")
async def yardim_cagrisi(ctx, *, reason: str = "Gerekli bir sebep belirtilmedi."):
    embed = discord.Embed(
        title="Destek Talebi İletildi",
        description=f"Sebep: {reason}",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

    if STATUS_CHANNEL_ID != 0:
        try:
            ch = bot.get_channel(STATUS_CHANNEL_ID)
            if ch:
                alert = discord.Embed(title="Yeni Yardım Çağrısı", color=discord.Color.red())
                alert.add_field(name="Kullanıcı", value=f"{ctx.author} (`{ctx.author.id}`)", inline=True)
                alert.add_field(name="Sunucu", value=f"{ctx.guild.name}", inline=True)
                alert.add_field(name="Kanal", value=f"{ctx.channel.mention}", inline=True)
                alert.add_field(name="Sebep", value=reason, inline=False)
                await ch.send(embed=alert)
        except Exception as e:
            print(f"Çağrı iletilemedi: {e}")

@bot.command(name="hesapla")
async def hesapla(ctx, *, expression: str):
    try:
        sonuc = SafeCalculator.calculate(expression)
        embed = discord.Embed(title="Hesap Makinesi", color=discord.Color.green())
        embed.add_field(name="İşlem", value=f"```{expression}```", inline=False)
        embed.add_field(name="Sonuç", value=f"```{sonuc}```", inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command(name="sorusor", aliases=["ai", "gemini"])
async def sorusor(ctx, *, soru: str):
    async with ctx.typing():
        cevap = await ai.ask_gemini(soru)

    if len(cevap) <= 1950:
        await ctx.send(cevap)
    else:
        chunks = [cevap[i:i + 1900] for i in range(0, len(cevap), 1900)]
        for chunk in chunks:
            await ctx.send(chunk)

@bot.command(name="çevir")
async def cevir(ctx, *, args: str):
    try:
        parts = args.split(" ", 1)
        if len(parts) < 2:
            await ctx.send("Kullanım: `a!çevir en Merhaba nasılsın`")
            return

        target_lang = parts[0].lower()
        text_to_translate = parts[1]

        lang_code = target_lang if target_lang in LANGUAGES else None
        if not lang_code:
            for code, name in LANGUAGES.items():
                if name.lower() == target_lang:
                    lang_code = code
                    break

        if not lang_code:
            await ctx.send(f"Geçersiz dil: `{target_lang}`")
            return

        translated = await asyncio.to_thread(translator.translate, text_to_translate, dest=lang_code)

        embed = discord.Embed(title="Çeviri", color=discord.Color.blue())
        embed.add_field(name="Orijinal", value=text_to_translate, inline=False)
        embed.add_field(name="Sonuç", value=translated.text, inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Çeviri hatası: {e}")

@bot.command(name="hava")
async def hava(ctx, *, sehir: str):
    if not OPENWEATHER_API_KEY:
        await ctx.send("Hava durumu API anahtarı ayarlanmamış.")
        return

    url = f"https://api.openweathermap.org/data/2.5/weather?q={sehir}&appid={OPENWEATHER_API_KEY}&units=metric&lang=tr"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 404:
                    await ctx.send("Şehir bulunamadı.")
                    return
                data = await resp.json()

                temp = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                desc = data["weather"][0]["description"].capitalize()
                city = data["name"]
                icon = data["weather"][0]["icon"]

                embed = discord.Embed(title=f"{city} Hava Durumu", color=0x3498DB)
                embed.add_field(name="Sıcaklık", value=f"{temp}°C", inline=True)
                embed.add_field(name="Hissedilen", value=f"{feels_like}°C", inline=True)
                embed.add_field(name="Durum", value=desc, inline=True)
                embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon}@2x.png")
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Hata: {e}")

@bot.command(name="mors")
async def mors(ctx, *, text: str):
    code = ' '.join(MORS_ALFABE.get(char.upper(), char) for char in text)
    await ctx.send(f"Mors Kodu: `{code}`")

@bot.command(name="tersinecevir")
async def tersinecevir(ctx, *, metin: str):
    await ctx.send(f"Ters hali: {metin[::-1]}")

@bot.command(name="sifreolustur")
async def sifreolustur(ctx, length: int = 12):
    if length < 4 or length > 64:
        await ctx.send("Uzunluk 4 ile 64 arasında olmalıdır.")
        return
    pwd = random_password(length)
    try:
        await ctx.author.send(f"Şifreniz: `{pwd}`")
        await ctx.send(f"{ctx.author.mention} şifreniz özelden gönderildi!")
    except:
        await ctx.send(f"Şifreniz: `{pwd}`")

@bot.command(name="zarat")
async def zarat(ctx):
    zar = random.randint(1, 6)
    await ctx.send(f"{ctx.author.mention} zar attı: **{zar}**")

@bot.command(name="tokat")
async def tokat(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send(f"{ctx.author.mention} kendine tokat attı!")
        return
    await ctx.send(f"{ctx.author.display_name}, {member.mention} kullanıcısına tokat attı! 💥")

# Moderasyon komutları
@bot.command(name="nuke")
@commands.guild_only()
@commands.check(is_moderator)
async def nuke(ctx):
    ch = ctx.channel
    pos = ch.position
    new_ch = await ch.clone(reason=f"Nuke: {ctx.author}")
    await ch.delete(reason=f"Nuke: {ctx.author}")
    await new_ch.edit(position=pos)
    await new_ch.send("Kanal başarıyla nukelendi! 🥑")

@bot.command(name="lock")
@commands.guild_only()
@commands.check(is_moderator)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("Kanal kilitlendi!")

@bot.command(name="unlock")
@commands.guild_only()
@commands.check(is_moderator)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("Kanal kilidi açıldı!")

@bot.command(name="ban")
@commands.guild_only()
@commands.check(is_moderator)
async def ban(ctx, member: discord.Member, *, reason: str = "Sebep belirtilmedi"):
    if member == ctx.author:
        await ctx.send("Kendini banlayamazsın!")
        return
    if member == ctx.guild.owner:
        await ctx.send("Sunucu sahibini banlayamazsın!")
        return
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner and ctx.author.id not in MODERATOR_IDS:
        await ctx.send("Kendinden üst veya eşit yetkideki birini banlayamazsın!")
        return
    try:
        await member.ban(reason=reason)
        await ctx.send(f"{member} banlandı! Sebep: {reason}")
    except discord.Forbidden:
        await ctx.send("Yetkim yetersiz!")

@bot.command(name="idban")
@commands.guild_only()
@commands.check(is_moderator)
async def idban(ctx, user_id: int, *, reason: str = "Sebep belirtilmedi"):
    if user_id == ctx.author.id:
        await ctx.send("Kendini banlayamazsın!")
        return
    if user_id == ctx.guild.owner_id:
        await ctx.send("Sunucu sahibini banlayamazsın!")
        return
    try:
        user = await bot.fetch_user(user_id)
        target_member = ctx.guild.get_member(user_id)
        if target_member and target_member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner and ctx.author.id not in MODERATOR_IDS:
            await ctx.send("Kendinden üst veya eşit yetkideki birini banlayamazsın!")
            return
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f"{user} ID ile banlandı!")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command(name="sil", aliases=["clear"])
@commands.guild_only()
@commands.check(is_moderator)
async def sil(ctx, amount: int):
    if amount < 1 or amount > 100:
        await ctx.send("1 ile 100 arasında bir sayı girin.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"**{len(deleted) - 1}** mesaj silindi.", delete_after=4)

@bot.command(name="herkesetagver")
@commands.guild_only()
@commands.check(is_moderator)
async def herkesetagver(ctx, tag: str):
    count = 0
    await ctx.send("Tag veriliyor...")
    for m in ctx.guild.members:
        if m.bot or m == ctx.guild.owner:
            continue
        try:
            if not m.display_name.startswith(tag):
                await m.edit(nick=f"{tag} {m.display_name[:28]}")
                count += 1
        except:
            pass
    await ctx.send(f"{count} kişiye tag verildi.")

@bot.command(name="tagsıfırla")
@commands.guild_only()
@commands.check(is_moderator)
async def tagsıfırla(ctx, tag: str = None):
    count = 0
    await ctx.send("Tagler sıfırlanıyor...")
    for m in ctx.guild.members:
        if m.bot or m == ctx.guild.owner:
            continue
        try:
            if tag and tag in m.display_name:
                new_nick = m.display_name.replace(tag, "").strip()
                await m.edit(nick=new_nick or None)
                count += 1
            elif not tag and m.nick:
                await m.edit(nick=None)
                count += 1
        except:
            pass
    await ctx.send(f"{count} kişinin ismi sıfırlandı.")

@bot.command(name="jail")
@commands.guild_only()
@commands.check(is_moderator)
async def jail(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send("Kendini jaile atamazsın!")
        return
    if member == ctx.guild.owner:
        await ctx.send("Sunucu sahibini jaile atamazsın!")
        return
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner and ctx.author.id not in MODERATOR_IDS:
        await ctx.send("Kendinden üst veya eşit yetkideki birini jaile atamazsın!")
        return
    role = discord.utils.get(ctx.guild.roles, name="Jail") or discord.utils.get(ctx.guild.roles, name="Cezalı")
    if not role:
        await ctx.send("Sunucuda `Jail` veya `Cezalı` adında rol bulunamadı.")
        return
    try:
        await member.add_roles(role)
        await ctx.send(f"{member.mention} jaile atıldı!")
    except:
        await ctx.send("Rol verilemedi, yetkim yetmiyor.")

@bot.command(name="unjail")
@commands.guild_only()
@commands.check(is_moderator)
async def unjail(ctx, member: discord.Member):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner and ctx.author.id not in MODERATOR_IDS:
        await ctx.send("Kendinden üst veya eşit yetkideki birinin cezasını kaldıramazsın!")
        return
    role = discord.utils.get(ctx.guild.roles, name="Jail") or discord.utils.get(ctx.guild.roles, name="Cezalı")
    if not role:
        await ctx.send("Sunucuda rol bulunamadı.")
        return
    try:
        await member.remove_roles(role)
        await ctx.send(f"{member.mention} jailden çıkarıldı!")
    except:
        await ctx.send("Yetki yetersiz.")

@bot.command(name="kanallarasüresınırıkoy")
@commands.guild_only()
@commands.check(is_moderator)
async def kanallara_sure_siniri(ctx, saniye: int):
    count = 0
    for ch in ctx.guild.text_channels:
        try:
            await ch.edit(slowmode_delay=saniye)
            count += 1
        except:
            pass
    await ctx.send(f"{count} kanala {saniye} saniye yavaş mod uygulandı.")

@bot.command(name="sunucuanı")
@commands.guild_only()
@commands.check(is_moderator)
async def sunucuanı(ctx):
    members = [m for ch in ctx.guild.voice_channels for m in ch.members]
    if members:
        names = "\n".join([f"• {m.display_name} ({m.voice.channel.name})" for m in members])
        await ctx.send(f"**Sesteki Üyeler ({len(members)}):**\n{names[:1900]}")
    else:
        await ctx.send("Ses kanallarında kimse yok.")

# Sunucu yönetimi (Owner)
@bot.command(name="sunucudancik")
@commands.check(is_bot_owner)
async def sunucudancik(ctx, guild_id: int):
    guild = bot.get_guild(guild_id)
    if not guild:
        await ctx.send("Sunucu bulunamadı.")
        return
    await guild.leave()
    await ctx.send(f"{guild.name} sunucusundan çıkıldı.")

@bot.command(name="sunucusorgulama")
@commands.check(is_bot_owner)
async def sunucusorgulama(ctx, guild_id: int):
    guild = bot.get_guild(guild_id)
    if not guild:
        await ctx.send("Sunucu bulunamadı.")
        return

    embed = discord.Embed(title=f"Sunucu Bilgisi: {guild.name}", color=discord.Color.purple())
    embed.add_field(name="ID", value=str(guild.id), inline=True)
    embed.add_field(name="Kurucu", value=str(guild.owner), inline=True)
    embed.add_field(name="Üye Sayısı", value=str(guild.member_count), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="sunucuları")
@commands.check(is_bot_owner)
async def sunuculari(ctx):
    guilds = bot.guilds
    pages = [guilds[i:i + 6] for i in range(0, len(guilds), 6)]
    if not pages:
        await ctx.send("Hiç sunucu yok.")
        return

    page = 0
    def get_embed(idx):
        emb = discord.Embed(title=f"Sunucular ({len(guilds)})", description=f"Sayfa {idx + 1} / {len(pages)}")
        for g in pages[idx]:
            emb.add_field(name=g.name, value=f"ID: `{g.id}` | Üye: `{g.member_count}`", inline=False)
        return emb

    msg = await ctx.send(embed=get_embed(page))
    if len(pages) > 1:
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == msg.id

        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "⬅️" and page > 0:
                    page -= 1
                    await msg.edit(embed=get_embed(page))
                elif str(reaction.emoji) == "➡️" and page < len(pages) - 1:
                    page += 1
                    await msg.edit(embed=get_embed(page))
                await msg.remove_reaction(reaction.emoji, user)
            except asyncio.TimeoutError:
                break

@bot.command(name="busunucuyukopyala")
@commands.guild_only()
@commands.check(is_bot_owner)
@commands.has_permissions(administrator=True)
async def busunucuyukopyala(ctx, source_guild_id: int):
    source = bot.get_guild(source_guild_id)
    if not source:
        await ctx.send("Kaynak sunucu bulunamadı.")
        return

    target = ctx.guild
    msg = await ctx.send(f"{source.name} sunucusu kopyalanıyor...")

    for role in source.roles:
        if role.is_default() or role.managed:
            continue
        try:
            await target.create_role(
                name=role.name, permissions=role.permissions,
                colour=role.colour, hoist=role.hoist, mentionable=role.mentionable
            )
        except:
            pass

    cat_map = {}
    for cat in source.categories:
        try:
            new_cat = await target.create_category(name=cat.name)
            cat_map[cat.id] = new_cat
        except:
            pass

    for ch in source.channels:
        cat = cat_map.get(ch.category_id)
        try:
            if isinstance(ch, discord.TextChannel):
                await target.create_text_channel(name=ch.name, category=cat, topic=ch.topic)
            elif isinstance(ch, discord.VoiceChannel):
                await target.create_voice_channel(name=ch.name, category=cat)
        except:
            pass

    await msg.edit(content=f"{source.name} sunucusu başarıyla kopyalandı!")

@bot.command(name="rollerisil")
@commands.guild_only()
@commands.check(is_bot_owner)
@commands.has_permissions(administrator=True)
async def rollerisil(ctx):
    count = 0
    await ctx.send("Roller siliniyor...")
    for role in ctx.guild.roles:
        if role.is_default() or role >= ctx.guild.me.top_role or role.managed:
            continue
        try:
            await role.delete(reason=f"Toplu silme: {ctx.author}")
            count += 1
        except:
            pass
    await ctx.send(f"{count} adet rol silindi.")

if __name__ == "__main__":
    if not DISCORD_TOKEN or DISCORD_TOKEN == "burayatoken":
        print("Lütfen .env dosyasındaki DISCORD_TOKEN alanını doldurun.")
        sys.exit(1)

    print("Bot başlatılıyor...")
    bot.run(DISCORD_TOKEN)

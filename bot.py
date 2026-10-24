import os, sqlite3, logging, asyncio
from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import requests

load_dotenv()
TOKEN=os.getenv("DİSCORD TOKEN","").strip()
ROBLOX_API_KEY=os.getenv("xSj0+3+8Pk+ALTHINbPvL1HmPRyPzH+EHM2QoVOHWa5Ml2XBZXlKaGJHY2lPaUpTVXpJMU5pSXNJbXRwWkNJNkluTnBaeTB5TURJeExUQTNMVEV6VkRFNE9qVXhPalE1V2lJc0luUjVjQ0k2SWtwWFZDSjkuZXlKaGRXUWlPaUpTYjJKc2IzaEpiblJsY201aGJDSXNJbWx6Y3lJNklrTnNiM1ZrUVhWMGFHVnVkR2xqWVhScGIyNVRaWEoyYVdObElpd2lZbUZ6WlVGd2FVdGxlU0k2SW5oVGFqQXJNeXM0VUdzclFVeFVTRWxPWWxCMlRERkliVkJTZVZCNlNDdEZTRTB5VVc5V1QwaFhZVFZOYkRKWVFpSXNJbTkzYm1WeVNXUWlPaUl4TURVM05ESTRNekl3TWlJc0ltVjRjQ0k2TVRjNU1qZ3pOVGszTml3aWFXRjBJam94TnpreU9ETXlNemMyTENKdVltWWlPakUzT1RJNE16SXpOelo5LmRPX0g4MlFMX19ySkRIbFY0OXJpbU5QYlRIYWs2TW9Sd0I4MkhiSUh0X0pUWFo2ZEtTeHR4QkV2UXJBc254LXllajl5eHhoODR4YkpweXdRTFdFc2hnN2dBalFfMG14cXFaZnMwN2RUZ3lEcUhoNDN3ZnNySE5YQ3lXR1NiN0RzOVgyREFfSmtROExXQS1TcVdhbUxhb1lvVjA4ZkRSdEhwQ0l6eVJ0cGt0YVoxQTNhR0F4ZDR3R1dFaXN5clVUZWRUbHFtOHJySUhDd2V5QW5NUVRQSlduNmMzZ2NVaWhLSFg1Ulg3VlVWeGdqQjdLelhWbzl4M0pMd2hBaWdqT0VfUXQzZHFaeHNRZ1NCV0FjQmdMdTc5bHV6dG1RNzBpekV1OU5oOW9xWWVlUFdscWhOMVBPbjRCcHRtUW9HVkFKY3RiT2dja241bGNyMGU1TDJIcHJyZw==","").strip()
DB_PATH=os.getenv("DB_PATH","bot.db")
GUILD_ID=os.getenv("1562127265863704618","").strip()
logging.basicConfig(level=logging.INFO)
log=logging.getLogger("roblox-bot")

DEFAULT_GROUPS=[
("Ana Topluluk","430220395","main"),
("Askeri İnzibat","716378002","branch"),
("Hava Kuvvetleri Komutanlığı","60657292","branch"),
("Jandarma Genel Komutanlığı","585901114","branch"),
("Kara Kuvvetleri Komutanlığı","477860296","branch"),
("Sınır Müfettişleri","900935333","branch"),
("Özel Kuvvetler Komutanlığı","842748385","branch"),
]
intents=discord.Intents.default()
intents.members=True
intents.message_content=True
bot=commands.Bot(command_prefix="!",intents=intents)

def connect():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS groups(group_id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT DEFAULT 'branch',log_channel TEXT);
        CREATE TABLE IF NOT EXISTS links(discord_id TEXT PRIMARY KEY,roblox_id TEXT NOT NULL,roblox_name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,action TEXT,details TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY AUTOINCREMENT,discord_id TEXT,group_id TEXT,reason TEXT,status TEXT DEFAULT 'pending',created TEXT);
        CREATE TABLE IF NOT EXISTS autoresponses(trigger TEXT PRIMARY KEY,response TEXT);
        CREATE TABLE IF NOT EXISTS tickets(channel_id TEXT PRIMARY KEY,owner_id TEXT,category TEXT,status TEXT DEFAULT 'open');
        CREATE TABLE IF NOT EXISTS bans(user_id TEXT PRIMARY KEY,reason TEXT,actor TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS rules(id INTEGER PRIMARY KEY AUTOINCREMENT,content TEXT);
        CREATE TABLE IF NOT EXISTS registrations(discord_id TEXT PRIMARY KEY,roblox_name TEXT,notes TEXT);
        """)
        for name,gid,kind in DEFAULT_GROUPS:
            c.execute("INSERT OR IGNORE INTO groups(group_id,name,kind) VALUES(?,?,?)",(gid,name,kind))
def setting(key, default=None):
    with connect() as c:
        r=c.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
    return r["value"] if r else default
def set_setting(key,value):
    with connect() as c: c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))
def log_action(user,action,details):
    with connect() as c: c.execute("INSERT INTO audit(actor,action,details,created) VALUES(?,?,?,?)",(str(user.id),action,str(details)[:1000],datetime.now(timezone.utc).isoformat()))
def admin(i): return bool(i.guild and i.user.guild_permissions.manage_guild)
async def need_admin(i):
    if not admin(i):
        await i.response.send_message("Bu komut için **Sunucuyu Yönet** izni gerekli.",ephemeral=True); return False
    return True
def groups():
    with connect() as c: return c.execute("SELECT * FROM groups ORDER BY kind DESC,name").fetchall()
def get_group(gid):
    with connect() as c: return c.execute("SELECT * FROM groups WHERE group_id=?",(str(gid),)).fetchone()
def linked(did):
    with connect() as c: return c.execute("SELECT * FROM links WHERE discord_id=?",(str(did),)).fetchone()
def api(method,url,**kwargs):
    if not ROBLOX_API_KEY: raise RuntimeError("ROBLOX_API_KEY .env dosyasında ayarlanmamış.")
    headers=kwargs.pop("headers",{})
    headers.update({"x-api-key":ROBLOX_API_KEY,"Content-Type":"application/json"})
    r=requests.request(method,url,headers=headers,timeout=20,**kwargs)
    if not r.ok: raise RuntimeError(f"Roblox API HTTP {r.status_code}: {r.text[:350]}")
    return r.json() if r.content else {}
async def error_reply(i,e):
    msg=f"İşlem başarısız: `{str(e)[:650]}`"
    if i.response.is_done(): await i.followup.send(msg,ephemeral=True)
    else: await i.response.send_message(msg,ephemeral=True)
async def audit_channel(guild, text):
    cid=setting("log_channel")
    if guild and cid:
        ch=guild.get_channel(int(cid))
        if ch:
            try: await ch.send(text)
            except discord.HTTPException: pass
async def record(i,action,details):
    log_action(i.user,action,details)
    await audit_channel(i.guild,f"🧾 **{action}** · {i.user.mention}\n{details}")

@bot.event
async def on_ready():
    init_db()
    try:
        if GUILD_ID.isdigit():
            obj=discord.Object(id=int(GUILD_ID)); bot.tree.copy_global_to(guild=obj); synced=await bot.tree.sync(guild=obj)
        else: synced=await bot.tree.sync()
        log.info("Bot hazır: %s | %s komut",bot.user,len(synced))
    except Exception: log.exception("Slash komutları eşitlenemedi")

@bot.event
async def on_message(message):
    if message.author.bot: return
    with connect() as c:
        auto=c.execute("SELECT response FROM autoresponses WHERE lower(trigger)=lower(?)",(message.content.strip(),)).fetchone()
    if auto: await message.channel.send(auto["response"])
    await bot.process_commands(message)

@bot.tree.command(name="ping",description="Bot gecikmesini gösterir.")
async def ping(i): await i.response.send_message(f"Pong! `{round(bot.latency*1000)} ms`")
@bot.tree.command(name="yardim",description="Komut kategorilerini gösterir.")
async def help_cmd(i):
    await i.response.send_message(
    "**Yönetim:** `/gruplar`, `/grup-ekle`, `/grup-sil`, `/log-kanali`, `/son-islemler`\\n"
    "**Roblox:** `/dogrula`, `/roblox-hesabim`, `/oyuncu-bilgi`, `/rutbeler`, `/rutbe-degistir`, `/rutbe-terfi`, `/rutbe-tenzil`\\n"
    "**Branş:** `/brans-istek`, `/brans-istekler`, `/brans-onayla`, `/brans-reddet`\\n"
    "**Kayıt:** `/kayit`, `/kayit-bilgi` · **Kurallar:** `/kurallar`, `/kural-ekle`\\n"
    "**Otomatik yanıt:** `/oto-yanit-ekle`, `/oto-yanit-sil`, `/oto-yanitlar`\\n"
    "**Bilet:** `/bilet-panel`, `/bilet-kapat`, `/bilet-kullanici-ekle`\\n"
    "**Duyuru:** `/duyuru` · **Yasak:** `/tam-yasak-at`, `/tam-yasak-kaldir`",
    ephemeral=True)

@bot.tree.command(name="gruplar",description="Kayıtlı Roblox topluluklarını listeler.")
async def gruplar_cmd(i):
    await i.response.send_message("\\n".join(f"• **{r['name']}** — `{r['group_id']}` ({'Ana' if r['kind']=='main' else 'Branş'})" for r in groups()))
@bot.tree.command(name="grup-ekle",description="Roblox grubu ekler.")
@app_commands.describe(ad="Grup adı",grup_id="Sayısal Roblox grup ID")
async def grup_ekle(i,ad:str,grup_id:str):
    if not await need_admin(i): return
    if not grup_id.isdigit(): return await i.response.send_message("ID sadece rakam olmalı.",ephemeral=True)
    with connect() as c: c.execute("INSERT INTO groups(group_id,name,kind) VALUES(?,?,?) ON CONFLICT(group_id) DO UPDATE SET name=excluded.name",(grup_id,ad[:100],"branch"))
    await record(i,"grup-ekle",f"{ad} ({grup_id})"); await i.response.send_message(f"✅ {ad} eklendi.")
@bot.tree.command(name="grup-sil",description="Roblox grubunu listeden siler.")
async def grup_sil(i,grup_id:str):
    if not await need_admin(i): return
    with connect() as c: cur=c.execute("DELETE FROM groups WHERE group_id=?",(grup_id,))
    await i.response.send_message("Grup silindi." if cur.rowcount else "Bu grup bulunamadı.")
@bot.tree.command(name="log-kanali",description="İşlem kayıt kanalını belirler.")
async def log_kanali(i,kanal:discord.TextChannel):
    if not await need_admin(i): return
    set_setting("log_channel",kanal.id); await i.response.send_message(f"Log kanalı: {kanal.mention}",ephemeral=True)

@bot.tree.command(name="dogrula",description="Roblox kullanıcı adını Discord hesabına bağlar (sahiplik kanıtı değildir).")
async def dogrula(i,kullanici_adi:str):
    await i.response.defer(ephemeral=True)
    try:
        r=requests.post("https://users.roblox.com/v1/usernames/users",json={"usernames":[kullanici_adi],"excludeBannedUsers":True},timeout=20); r.raise_for_status()
        arr=r.json().get("data",[])
        if not arr: return await i.followup.send("Kullanıcı bulunamadı.",ephemeral=True)
        u=arr[0]
        with connect() as c: c.execute("INSERT INTO links(discord_id,roblox_id,roblox_name) VALUES(?,?,?) ON CONFLICT(discord_id) DO UPDATE SET roblox_id=excluded.roblox_id,roblox_name=excluded.roblox_name",(str(i.user.id),str(u["id"]),u["name"]))
        await record(i,"dogrula",f"{u['name']} / {u['id']}")
        await i.followup.send(f"Bağlandı: **{u['name']}** (`{u['id']}`). Bu komut hesap sahipliğini doğrulamaz.",ephemeral=True)
    except Exception as e: await error_reply(i,e)
@bot.tree.command(name="roblox-hesabim",description="Bağlı Roblox hesabını gösterir.")
async def roblox_hesabim(i):
    u=linked(i.user.id)
    await i.response.send_message(f"**{u['roblox_name']}** (`{u['roblox_id']}`)" if u else "Önce `/dogrula` kullan.",ephemeral=True)
@bot.tree.command(name="oyuncu-bilgi",description="Roblox kullanıcı ID'si hakkında bilgi verir.")
async def oyuncu_bilgi(i,roblox_kullanici_id:str):
    await i.response.defer()
    try:
        d=api("GET",f"https://users.roblox.com/v1/users/{roblox_kullanici_id}")
        await i.followup.send(f"**{d.get('name','?')}** · {d.get('displayName','?')} · ID `{d.get('id',roblox_kullanici_id)}`\\n{d.get('description','')[:500]}")
    except Exception as e: await error_reply(i,e)
@bot.tree.command(name="rutbeler",description="Grubun rollerini listeler.")
async def rutbeler(i,grup_id:str):
    await i.response.defer(ephemeral=True)
    if not get_group(grup_id): return await i.followup.send("Grup kayıtlı değil; `/gruplar` kullan.",ephemeral=True)
    try:
        d=api("GET",f"https://apis.roblox.com/cloud/v2/groups/{grup_id}/roles")
        roles=d.get("groupRoles",d.get("roles",[]))
        out=[]
        for r in roles[:25]:
            rid=r.get("id") or r.get("path","").split("/")[-1]
            out.append(f"• **{r.get('displayName',r.get('name','Rol'))}** — rank `{r.get('rank','?')}` — rol ID `{rid}`")
        await i.followup.send("\\n".join(out) or "Rol dönmedi. API izinlerini kontrol et.",ephemeral=True)
    except Exception as e: await error_reply(i,e)
async def change_role(i,group_id,user_id,role_id,action):
    if not await need_admin(i): return
    if not all(x.isdigit() for x in [group_id,user_id,role_id]): return await i.response.send_message("ID'ler rakam olmalı.",ephemeral=True)
    if not get_group(group_id): return await i.response.send_message("Grup kayıtlı değil.",ephemeral=True)
    await i.response.defer(ephemeral=True)
    try:
        api("PATCH",f"https://apis.roblox.com/cloud/v2/groups/{group_id}/members/{user_id}",json={"role":f"groups/{group_id}/roles/{role_id}"})
        await record(i,action,f"group={group_id}; user={user_id}; role={role_id}")
        await i.followup.send("Roblox API isteği başarılı. Yetki ve rol hiyerarşisi Roblox tarafından kabul edilmiş olmalı.",ephemeral=True)
    except Exception as e: await error_reply(i,e)
@bot.tree.command(name="rutbe-degistir",description="Roblox üyesinin rolünü değiştirir.")
async def rutbe_degistir(i,grup_id:str,roblox_kullanici_id:str,rol_id:str): await change_role(i,grup_id,roblox_kullanici_id,rol_id,"rutbe-degistir")
@bot.tree.command(name="rutbe-terfi",description="Üyeyi bir üst role almak için hedef rol ID'sini uygular.")
async def rutbe_terfi(i,grup_id:str,roblox_kullanici_id:str,yeni_rol_id:str): await change_role(i,grup_id,roblox_kullanici_id,yeni_rol_id,"rutbe-terfi")
@bot.tree.command(name="rutbe-tenzil",description="Üyeyi daha alt role almak için hedef rol ID'sini uygular.")
async def rutbe_tenzil(i,grup_id:str,roblox_kullanici_id:str,yeni_rol_id:str): await change_role(i,grup_id,roblox_kullanici_id,yeni_rol_id,"rutbe-tenzil")

@bot.tree.command(name="brans-istek",description="Bir branş topluluğuna katılım isteği gönderir.")
async def brans_istek(i,grup_id:str,sebep:str):
    if not get_group(grup_id): return await i.response.send_message("Branş ID'si kayıtlı değil.",ephemeral=True)
    with connect() as c: c.execute("INSERT INTO requests(discord_id,group_id,reason,created) VALUES(?,?,?,?)",(str(i.user.id),grup_id,sebep[:500],datetime.now(timezone.utc).isoformat()))
    await record(i,"brans-istek",f"user={i.user.id}; group={grup_id}; {sebep}")
    await i.response.send_message("Branş isteğin gönderildi.",ephemeral=True)
@bot.tree.command(name="brans-istekler",description="Bekleyen branş isteklerini listeler.")
async def brans_istekler(i):
    if not await need_admin(i): return
    with connect() as c: rows=c.execute("SELECT * FROM requests WHERE status='pending' ORDER BY id DESC LIMIT 15").fetchall()
    await i.response.send_message("\\n".join(f"#{r['id']} <@{r['discord_id']}> — grup `{r['group_id']}` — {r['reason']}" for r in rows) or "Bekleyen istek yok.",ephemeral=True)
async def request_decision(i,request_id,status):
    if not await need_admin(i): return
    with connect() as c:
        r=c.execute("SELECT * FROM requests WHERE id=?",(request_id,)).fetchone()
        if r: c.execute("UPDATE requests SET status=? WHERE id=?",(status,request_id))
    if not r: return await i.response.send_message("İstek bulunamadı.",ephemeral=True)
    await record(i,"brans-"+status,f"request={request_id}")
    await i.response.send_message(f"İstek {status}.",ephemeral=True)
@bot.tree.command(name="brans-onayla",description="Branş isteğini onaylar.")
async def brans_onayla(i,istek_no:int): await request_decision(i,istek_no,"approved")
@bot.tree.command(name="brans-reddet",description="Branş isteğini reddeder.")
async def brans_reddet(i,istek_no:int): await request_decision(i,istek_no,"rejected")

@bot.tree.command(name="kayit",description="Discord üyesini kayıt eder.")
async def kayit(i,uye:discord.Member,roblox_adi:str,notlar:str=""):
    if not await need_admin(i): return
    with connect() as c: c.execute("INSERT INTO registrations(discord_id,roblox_name,notes) VALUES(?,?,?) ON CONFLICT(discord_id) DO UPDATE SET roblox_name=excluded.roblox_name,notes=excluded.notes",(str(uye.id),roblox_adi[:100],notlar[:300]))
    await record(i,"kayit",f"{uye.id} => {roblox_adi}")
    await i.response.send_message(f"{uye.mention} kaydedildi.")
@bot.tree.command(name="kayit-bilgi",description="Üyenin kayıt bilgisini gösterir.")
async def kayit_bilgi(i,uye:discord.Member):
    with connect() as c: r=c.execute("SELECT * FROM registrations WHERE discord_id=?",(str(uye.id),)).fetchone()
    await i.response.send_message(f"**Roblox:** {r['roblox_name']}\\n**Not:** {r['notes'] or '-'}" if r else "Kayıt bulunamadı.",ephemeral=True)

@bot.tree.command(name="kurallar",description="Sunucu kurallarını gösterir.")
async def kurallar(i):
    with connect() as c: rows=c.execute("SELECT content FROM rules ORDER BY id").fetchall()
    await i.response.send_message("\\n".join(f"{n}. {r['content']}" for n,r in enumerate(rows,1)) or "Henüz kural eklenmemiş.",ephemeral=True)
@bot.tree.command(name="kural-ekle",description="Sunucu kuralı ekler.")
async def kural_ekle(i,metin:str):
    if not await need_admin(i): return
    with connect() as c: c.execute("INSERT INTO rules(content) VALUES(?)",(metin[:500],))
    await i.response.send_message("Kural eklendi.",ephemeral=True)

@bot.tree.command(name="oto-yanit-ekle",description="Mesaja otomatik yanıt ekler.")
async def oto_ekle(i,ifade:str,yanit:str):
    if not await need_admin(i): return
    with connect() as c: c.execute("INSERT INTO autoresponses(trigger,response) VALUES(?,?) ON CONFLICT(trigger) DO UPDATE SET response=excluded.response",(ifade[:150],yanit[:1500]))
    await i.response.send_message("Otomatik yanıt kaydedildi.",ephemeral=True)
@bot.tree.command(name="oto-yanit-sil",description="Otomatik yanıtı siler.")
async def oto_sil(i,ifade:str):
    if not await need_admin(i): return
    with connect() as c: cur=c.execute("DELETE FROM autoresponses WHERE lower(trigger)=lower(?)",(ifade,))
    await i.response.send_message("Silindi." if cur.rowcount else "Bulunamadı.",ephemeral=True)
@bot.tree.command(name="oto-yanitlar",description="Otomatik yanıtları listeler.")
async def oto_list(i):
    with connect() as c: rows=c.execute("SELECT trigger FROM autoresponses ORDER BY trigger").fetchall()
    await i.response.send_message(", ".join(f"`{r['trigger']}`" for r in rows) or "Kayıt yok.",ephemeral=True)

@bot.tree.command(name="duyuru",description="Seçilen kanala duyuru gönderir.")
async def duyuru(i,kanal:discord.TextChannel,baslik:str,mesaj:str):
    if not await need_admin(i): return
    embed=discord.Embed(title=baslik[:256],description=mesaj[:4000],color=discord.Color.blurple(),timestamp=datetime.now(timezone.utc))
    embed.set_footer(text=f"Gönderen: {i.user}")
    await kanal.send(embed=embed); await i.response.send_message("Duyuru gönderildi.",ephemeral=True)
@bot.tree.command(name="tam-yasak-at",description="Botun bulunduğu sunucuda üyeyi yasaklar.")
async def tam_yasak_at(i,uye:discord.Member,sebep:str):
    if not await need_admin(i): return
    try:
        await i.guild.ban(uye,reason=sebep[:400])
        with connect() as c: c.execute("INSERT INTO bans(user_id,reason,actor,created) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason,actor=excluded.actor,created=excluded.created",(str(uye.id),sebep[:500],str(i.user.id),datetime.now(timezone.utc).isoformat()))
        await record(i,"tam-yasak-at",f"{uye.id}: {sebep}")
        await i.response.send_message(f"{uye} sunucudan yasaklandı.")
    except Exception as e: await error_reply(i,e)
@bot.tree.command(name="tam-yasak-kaldir",description="Sunucudaki yasağı kaldırır.")
async def tam_yasak_kaldir(i,kullanici_id:str):
    if not await need_admin(i): return
    try:
        await i.guild.unban(discord.Object(id=int(kullanici_id)))
        with connect() as c: c.execute("DELETE FROM bans WHERE user_id=?",(kullanici_id,))
        await i.response.send_message("Yasak kaldırıldı.")
    except Exception as e: await error_reply(i,e)

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Destek bileti aç",style=discord.ButtonStyle.primary,custom_id="ticket:create")
    async def create_ticket(self,interaction:discord.Interaction,button:discord.ui.Button):
        guild=interaction.guild
        if not guild: return await interaction.response.send_message("Bu komut sunucuda kullanılmalı.",ephemeral=True)
        category_obj=None
        cat_id=setting("ticket_category")
        if cat_id:
            category_obj=guild.get_channel(int(cat_id))
        overwrites={guild.default_role:discord.PermissionOverwrite(view_channel=False),interaction.user:discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True)}
    

"""
Bot Discord + Gemini - v5.0.1
Chạy trên Render (Web Service): python main.py

Điểm quan trọng để chạy ổn trên Render:
- Web server (health check) mở port NGAY ĐẦU, trước khi bot đăng nhập Discord.
- Cogs được nạp trong setup_hook (chạy 1 lần), KHÔNG nạp trong on_ready
  (on_ready có thể chạy nhiều lần mỗi khi bot reconnect).
- Nếu chưa bật Privileged Intents trên Developer Portal, bot không crash-loop
  mà tự chạy chế độ hạn chế và ghi log hướng dẫn.
- Nếu Discord chặn IP của Render (HTTP 429 / Cloudflare 1015), bot đợi rồi thử lại
  thay vì chết liên tục.
"""
import asyncio
import time
import traceback

import aiohttp
import discord
from aiohttp import web
from discord.ext import commands

import config

START_TIME = time.time()

EXTENSIONS = (
    "cogs.ai_chat",
    "cogs.moderation",
    "cogs.reminders",
    "cogs.fun",
    "cogs.utility",
)


class GeminiBot(commands.Bot):
    async def setup_hook(self):
        # Chạy đúng 1 lần trước khi bot kết nối gateway
        for ext in EXTENSIONS:
            # Thử "cogs.ten" trước; nếu repo để file phẳng (không có thư mục cogs/)
            # thì tự thử "ten" ở thư mục gốc.
            flat = ext.split(".")[-1]
            loaded = False
            for candidate in (ext, flat):
                try:
                    await self.load_extension(candidate)
                    print(f"[COG] Da nap {candidate}")
                    loaded = True
                    break
                except commands.ExtensionNotFound:
                    continue
                except ModuleNotFoundError as e:
                    # Chỉ bỏ qua nếu thiếu chính module/thư mục cogs; lỗi thiếu thư viện khác thì báo
                    if e.name in (candidate, "cogs"):
                        continue
                    print(f"[COG LOI] {candidate} thieu thu vien: {e}")
                    traceback.print_exc()
                    loaded = True
                    break
                except Exception:
                    print(f"[COG LOI] Khong nap duoc {candidate}:")
                    traceback.print_exc()
                    loaded = True
                    break
            if not loaded:
                print(f"[COG LOI] Khong tim thay file cho {ext} (da thu {ext} va {flat})")
        if config.SYNC_COMMANDS:
            try:
                synced = await self.tree.sync()
                print(f"[SYNC] Dong bo {len(synced)} lenh slash (/)")
            except Exception:
                print("[SYNC LOI]")
                traceback.print_exc()

    async def on_ready(self):
        print(f"[READY] Dang nhap thanh cong: {self.user} (id={self.user.id})")
        print(f"[READY] Dang phuc vu {len(self.guilds)} server")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="chat cua ban | /help de xem lenh",
            )
        )

    async def on_guild_join(self, guild: discord.Guild):
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="Chao server! 👋",
                    description=(
                        "Minh la bot AI dung Gemini, vua tham gia server nay.\n"
                        "Nhac minh bang cach **@ten_bot** roi chat, hoac dung `/chaton` "
                        "de minh tu nhap hoi chuyen trong kenh nay.\n"
                        "Go `/help` de xem tat ca lenh."
                    ),
                    color=discord.Color.blurple(),
                )
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass
                break


def create_bot(privileged: bool = True) -> GeminiBot:
    intents = discord.Intents.default()
    # Hai intent này là "Privileged": phải bật trong Developer Portal -> Bot
    intents.message_content = privileged
    intents.members = privileged

    safe_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)
    bot = GeminiBot(
        command_prefix="!",
        intents=intents,
        allowed_mentions=safe_mentions,
        help_command=None,
    )
    bot.start_time = START_TIME
    return bot


# Bot hiện tại (được thay thế khi phải khởi tạo lại với intents hạn chế)
bot = create_bot()


# ---------------- Web server giúp Render thấy service "còn sống" ----------------
async def handle_health(request: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "alive",
            "bot": str(bot.user) if bot.user else "starting",
            "uptime_seconds": int(time.time() - START_TIME),
            "guilds": len(bot.guilds),
            "version": config.BOT_VERSION,
        }
    )


async def start_web_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/healthz", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    await site.start()
    print(f"[WEB] Health server chay o port {config.PORT}")
    return runner


async def keep_alive():
    """Tự gọi URL public của service mỗi 10 phút để Render free không ngủ (ngủ sau 15 phút)."""
    url = config.KEEPALIVE_URL
    if not url:
        return
    print(f"[KEEPALIVE] Tu ping {url} moi {config.KEEPALIVE_INTERVAL}s")
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            await asyncio.sleep(config.KEEPALIVE_INTERVAL)
            try:
                async with session.get(url) as resp:
                    print(f"[KEEPALIVE] ping -> {resp.status}")
            except Exception as e:
                print(f"[KEEPALIVE LOI] {e}")


# ---------------- Chạy bot ----------------
async def run_bot():
    """Chạy bot, tự xử lý 2 lỗi thường gặp khi deploy lần đầu trên Render."""
    global bot
    privileged = True
    rate_limit_wait = 60

    while True:
        try:
            async with bot:
                await bot.start(config.DISCORD_TOKEN)
            return
        except discord.PrivilegedIntentsRequired:
            if not privileged:
                raise
            print(
                "\n[LOI INTENTS] Chua bat Privileged Intents! Vao "
                "https://discord.com/developers/applications -> app cua ban -> Bot -> "
                "bat 'MESSAGE CONTENT INTENT' va 'SERVER MEMBERS INTENT' -> Save, roi Restart service.\n"
                "[LOI INTENTS] Tam thoi chay che do han che (chi tra loi khi @mention/DM, "
                "bo loc tu cam se khong hoat dong)."
            )
            privileged = False
            bot = create_bot(privileged=False)
        except discord.LoginFailure:
            raise RuntimeError(
                "DISCORD_TOKEN sai hoac da bi reset. Copy lai token o Developer Portal -> Bot -> Reset Token, "
                "roi cap nhat Environment Variables tren Render."
            )
        except discord.HTTPException as e:
            if e.status != 429:
                raise
            print(
                f"[RATE LIMIT] Discord tu choi dang nhap (429) - thuong do IP chung cua Render bi chan tam thoi. "
                f"Doi {rate_limit_wait}s roi thu lai..."
            )
            await asyncio.sleep(rate_limit_wait)
            rate_limit_wait = min(rate_limit_wait * 2, 900)
            bot = create_bot(privileged=privileged)


async def main():
    if not config.DISCORD_TOKEN:
        raise RuntimeError("Thieu DISCORD_TOKEN trong Environment Variables!")
    if not config.GEMINI_API_KEY:
        print("[CANH BAO] Thieu GEMINI_API_KEY - chuc nang AI se loi.")
    runner = await start_web_server()
    keepalive_task = asyncio.create_task(keep_alive())  # giữ tham chiếu để không bị GC
    try:
        await run_bot()
    finally:
        keepalive_task.cancel()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio

# ================= CONFIG =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

ydl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
}

ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

music_queue = []
is_playing = False

# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ================= CORE =================
async def play_next(ctx):
    global is_playing

    if len(music_queue) == 0:
        is_playing = False
        return

    is_playing = True
    url, title = music_queue.pop(0)

    source = discord.FFmpegPCMAudio(url, **ffmpeg_options)

    vc = ctx.voice_client
    vc.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(ctx), bot.loop
        ),
    )

    await ctx.send(f"🎵 Đang phát: **{title}**")

# ================= COMMANDS =================
@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("❌ Bạn phải vào voice trước")

    if ctx.voice_client:
        await ctx.voice_client.move_to(ctx.author.voice.channel)
    else:
        await ctx.author.voice.channel.connect()

    await ctx.send("✅ Đã vào voice")

@bot.command()
async def play(ctx, *, query):
    global is_playing

    if not ctx.author.voice:
        return await ctx.send("❌ Bạn phải vào voice")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    await ctx.send(f"🔎 Đang tìm: **{query}**")

    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await loop.run_in_executor(
            None, lambda: ydl.extract_info(query, download=False)
        )

    if "entries" in info:
        info = info["entries"][0]

    url = info["url"]
    title = info.get("title", "Unknown")

    music_queue.append((url, title))

    if not is_playing:
        await play_next(ctx)
    else:
        await ctx.send(f"➕ Đã thêm vào queue: **{title}**")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skip bài")
    else:
        await ctx.send("❌ Không có nhạc")

@bot.command()
async def queue(ctx):
    if not music_queue:
        return await ctx.send("📭 Queue trống")

    msg = "\n".join(
        [f"{i+1}. {t[1]}" for i, t in enumerate(music_queue)]
    )
    await ctx.send(f"📜 **Queue:**\n{msg}")

@bot.command()
async def stop(ctx):
    global music_queue, is_playing
    music_queue.clear()
    is_playing = False
    if ctx.voice_client:
        ctx.voice_client.stop()
    await ctx.send("⏹️ Đã dừng & clear queue")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Đã rời voice")

# ================= RUN =================
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("❌ Chưa set DISCORD_TOKEN")
    bot.run(token)

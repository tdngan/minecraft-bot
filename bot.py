import asyncio
import os
import re
import struct

import discord
from discord import app_commands

TOKEN = os.environ["DISCORD_TOKEN"]
HOST = os.getenv("RCON_HOST", "mc")
PORT = int(os.getenv("RCON_PORT", "25575"))
PASSWORD = os.environ["RCON_PASSWORD"]
ALLOWED = {int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()}
BLOCKED = {x.strip().lower() for x in os.getenv("BLOCKED_COMMANDS", "stop").split(",") if x.strip()}
GUILD_ID = os.getenv("GUILD_ID")


async def rcon(command: str) -> str:
    reader, writer = await asyncio.open_connection(HOST, PORT)

    async def send(ptype: int, body: str, pid: int):
        payload = struct.pack("<ii", pid, ptype) + body.encode() + b"\x00\x00"
        writer.write(struct.pack("<i", len(payload)) + payload)
        await writer.drain()

    async def recv():
        (length,) = struct.unpack("<i", await reader.readexactly(4))
        data = await reader.readexactly(length)
        pid, ptype = struct.unpack("<ii", data[:8])
        return pid, ptype, data[8:-2].decode("utf-8", "replace")

    try:
        await send(3, PASSWORD, 1)          # login
        pid, _, _ = await recv()
        if pid == -1:
            raise PermissionError("Sai mật khẩu RCON")
        await send(2, command, 2)           # command
        _, _, out = await recv()
        return re.sub(r"§.", "", out)       # bỏ mã màu Minecraft
    finally:
        writer.close()


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            guild = discord.Object(int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


bot = Bot()


@bot.tree.command(name="mc", description="Gửi lệnh RCON tới server Minecraft")
@app_commands.describe(command="Lệnh Minecraft, không cần dấu /")
@app_commands.guild_only()
async def mc(interaction: discord.Interaction, command: str):
    user = interaction.user
    cmd = command.strip().lstrip("/")

    if user.id not in ALLOWED:
        print(f"[DENY] {user} ({user.id}): {cmd}")
        await interaction.response.send_message("Bạn không có quyền dùng lệnh này.", ephemeral=True)
        return
    if not cmd or cmd.split()[0].lower() in BLOCKED:
        await interaction.response.send_message("Lệnh trống hoặc bị chặn.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    print(f"[RUN] {user} ({user.id}): {cmd}")
    try:
        out = await asyncio.wait_for(rcon(cmd), timeout=10)
    except Exception as e:
        await interaction.followup.send(f"Lỗi RCON: `{e}`", ephemeral=True)
        return
    out = out.strip() or "(không có output)"
    await interaction.followup.send(f"```\n{out[:1900]}\n```", ephemeral=True)


bot.run(TOKEN)

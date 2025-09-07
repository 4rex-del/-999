import discord
import os
import re
from discord.ext import commands
from discord import app_commands

from myserver import server_on

# ---------------- CONFIG ----------------
GUILD_ID = 1411573311787241534
LOG_CHANNEL_ID = 1412071745137020958
TARGET_CHANNEL_ID = 1411575566976417952

ROLES_FOR_SALE = {
    1411575321798512751: 10,
    1411586539544252537: 10,
    1412437426873434163: 10,
    1412438157772722317: 39,
    1411586465896464506: 59,
    1412436371175374940: 89,
    1412062520826662974: 100
}

user_points = {}

# ✅ Regex สำหรับตรวจลิ้งซองทรูมันนี่
TRUEWALLET_PATTERN = r"^https:\/\/gift\.truemoney\.com\/campaign\/\?v=[A-Za-z0-9]+$"

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------- MODAL ----------------
class TopupModal(discord.ui.Modal, title="เติมพอยผ่านระบบอั่งเปา"):
    url = discord.ui.TextInput(
        label="ลิ้งอั่งเปา",
        placeholder="กรอกลิ้งซองอั่งเปา 💸",
        required=True,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)

        # ✅ ตรวจสอบลิ้งซองทรูมันนี่
        if not re.match(TRUEWALLET_PATTERN, self.url.value.strip()):
            await interaction.response.send_message(
                "❌ กรุณากรอกลิ้งซองทรูมันนี่ที่ถูกต้อง!",
                ephemeral=True
            )
            return

        # ✅ ถ้าลิ้งถูกต้อง -> ส่งเข้า log
        if log_channel:
            embed = discord.Embed(
                title="📩 มีการส่งลิ้งอั่งเปา",
                description=f"👤 จาก: {interaction.user.mention}\n🔗 ลิ้ง: {self.url.value}",
                color=discord.Color.orange()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ ลิ้งของคุณถูกส่งไปตรวจสอบแล้ว", ephemeral=True
        )


# ---------------- VIEW ----------------
class MainMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ดูราคายศ", style=discord.ButtonStyle.primary, emoji=":emoji_145:")
    async def show_price(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="💎 ราคายศทั้งหมด", color=discord.Color.blue())
        for role_id, price in ROLES_FOR_SALE.items():
            role = interaction.guild.get_role(role_id)
            if role:
                embed.add_field(name=role.name, value=f"{price} Points", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="ซื้อยศ", style=discord.ButtonStyle.success, emoji=":86:")
    async def buy_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        points = user_points.get(user_id, 0)

        options = []
        for role_id, price in ROLES_FOR_SALE.items():
            role = interaction.guild.get_role(role_id)
            if role:
                options.append(discord.SelectOption(label=f"{role.name} - {price} Points", value=str(role_id)))

        if not options:
            await interaction.response.send_message("❌ ไม่มี Role ที่สามารถซื้อได้", ephemeral=True)
            return

        select = discord.ui.Select(placeholder="เลือกยศที่ต้องการซื้อ", options=options)

        async def select_callback(inter: discord.Interaction):
            role_id = int(select.values[0])
            price = ROLES_FOR_SALE[role_id]

            if user_points.get(user_id, 0) < price:
                await inter.response.send_message("❌ Point ของคุณไม่พอสำหรับการซื้อยศนี้!", ephemeral=True)
                return

            role = inter.guild.get_role(role_id)
            if role:
                await inter.user.add_roles(role)
                user_points[user_id] -= price
                await inter.response.send_message(
                    f"✅ คุณได้ซื้อยศ {role.name} แล้ว! เหลือ {user_points[user_id]} Points",
                    ephemeral=True
                )

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await interaction.response.send_message("เลือกยศที่คุณต้องการซื้อ:", view=view, ephemeral=True)

    @discord.ui.button(label="เช็คจำนวน Point", style=discord.ButtonStyle.secondary, emoji=":emoji_139~1:")
    async def check_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        points = user_points.get(user_id, 0)
        await interaction.response.send_message(f"💰 คุณมี {points} Points", ephemeral=True)

    @discord.ui.button(label="เติมเงิน", style=discord.ButtonStyle.danger, emoji=":emoji_122~2:")
    async def topup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopupModal())


# ---------------- SLASH COMMAND ----------------
@bot.tree.command(name="addpoin", description="เพิ่ม Point ให้ User")
@app_commands.describe(user="เลือก User ที่จะเพิ่ม Point", amount="จำนวน Point ที่จะเพิ่ม")
async def addpoin(interaction: discord.Interaction, user: discord.Member, amount: int):
    user_points[user.id] = user_points.get(user.id, 0) + amount
    await interaction.response.send_message(
        f"✅ เพิ่ม {amount} Points ให้ {user.mention} ตอนนี้มี {user_points[user.id]} Points",
        ephemeral=True
    )


# ---------------- EVENT ตรวจจับลิ้งในข้อความ ----------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if re.match(TRUEWALLET_PATTERN, message.content.strip()):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="📩 ตรวจพบลิ้งอั่งเปาในข้อความ",
                description=f"👤 จาก: {message.author.mention}\n🔗 ลิ้ง: {message.content}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

    await bot.process_commands(message)


# ---------------- READY ----------------
@bot.event
async def on_ready():
    streaming = discord.Streaming(
        name="พร้อมใช้งาน💜",
        url="https://www.youtube.com/"
    )
    await bot.change_presence(activity=streaming)
    await bot.tree.sync()
    print(f"✅ บอทออนไลน์แล้ว: {bot.user}")

    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🛒 ซื้อยศ",
            description="เลือกยศที่ต้องการ 100 Points = 1บาท",
            color=discord.Color.green()
        )
        embed.set_image(
            url="https://media.discordapp.net/attachments/1411575487096164522/1411580378254147704/1276_20250831121606.png"
        )
        await channel.send(embed=embed, view=MainMenu())

server_on()


bot.run(os.getenv('TOKEN'))

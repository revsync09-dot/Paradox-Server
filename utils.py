import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp
from io import BytesIO
import os

class V2Embed(discord.Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault('color', 0x2b2d31) 
        super().__init__(**kwargs)

class EmbedFactory:
    @staticmethod
    def create_premium_embed(title, description, color=0x2b2d31):
        return V2Embed(title=f"**{title}**", description=description)

async def create_vouch_card(booster_name, game_name, total_vouches, avatar_url):
    bg_path = "assets/vouch_bg.png"
    if not os.path.exists(bg_path):
        base = Image.new('RGB', (800, 400), color=(20, 20, 25))
    else:
        base = Image.open(bg_path).convert('RGBA')
        base = base.resize((800, 400))

    draw = ImageDraw.Draw(base)
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 50)
        sub_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 35)
        stat_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 80)
    except:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        stat_font = ImageFont.load_default()

    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as resp:
            if resp.status == 200:
                avatar_data = await resp.read()
                avatar = Image.open(BytesIO(avatar_data)).convert("RGBA")
                avatar = avatar.resize((180, 180))
                mask = Image.new('L', (180, 180), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
                avatar.putalpha(mask)
                base.paste(avatar, (50, 110), avatar)
                draw.ellipse((48, 108, 232, 292), outline=(114, 137, 218), width=5)

    draw.text((260, 120), booster_name, font=title_font, fill=(255, 255, 255))
    draw.text((260, 180), f"Game: {game_name}", font=sub_font, fill=(200, 200, 200))
    draw.text((550, 120), "VOUCHES", font=sub_font, fill=(114, 137, 218))
    w = draw.textlength(str(total_vouches), font=stat_font)
    draw.text((550 + (150 - w)//2, 170), str(total_vouches), font=stat_font, fill=(255, 215, 0))

    img_byte_arr = BytesIO()
    base.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

async def create_profile_card(booster_name, total_vouches, game_breakdown, avatar_url):
    bg_path = "assets/profile_bg.png"
    if not os.path.exists(bg_path):
        base = Image.new('RGB', (1000, 800), color=(15, 15, 20))
    else:
        base = Image.open(bg_path).convert('RGBA')
        base = base.resize((1000, 800))

    draw = ImageDraw.Draw(base)
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 60)
        sub_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 40)
        text_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
        stat_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 100)
        desc_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
    except:
        title_font = sub_font = text_font = stat_font = desc_font = ImageFont.load_default()

    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as resp:
            if resp.status == 200:
                avatar_data = await resp.read()
                avatar = Image.open(BytesIO(avatar_data)).convert("RGBA")
                avatar = avatar.resize((200, 200))
                mask = Image.new('L', (200, 200), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
                avatar.putalpha(mask)
                base.paste(avatar, (50, 50), avatar)
                draw.ellipse((48, 48, 252, 252), outline=(114, 137, 218), width=8)

    draw.text((280, 80), f"{booster_name}", font=title_font, fill=(255, 255, 255))
    draw.text((280, 150), f"You have {total_vouches} vouches! 🎉", font=text_font, fill=(200, 200, 200))
    draw.text((50, 300), "🏆 TOTAL VOUCHES", font=sub_font, fill=(255, 215, 0))
    draw.text((50, 350), f"{total_vouches}", font=stat_font, fill=(255, 255, 255))
    draw.text((50, 500), "🎮 BY GAME", font=sub_font, fill=(114, 137, 218))
    
    y_offset = 560
    for game, count in list(game_breakdown.items())[:5]:
        draw.text((60, y_offset), f"• {game}: {count}", font=text_font, fill=(220, 220, 220))
        y_offset += 40

    draw.text((550, 300), "🏅 ACHIEVEMENTS", font=sub_font, fill=(0, 255, 127))
    achievements = [
        (1, "🌱 First Steps", "Earned your first vouch"),
        (10, "⭐ Rising Star", "Reached 10 vouches"),
        (25, "🔥 Trusted Booster", "Reached 25 vouches"),
        (50, "💎 Veteran", "Reached 50 vouches"),
        (100, "👑 Elite Carrier", "Reached 100 vouches"),
        (250, "🏆 Legendary", "Reached 250 vouches"),
        (500, "🌟 Hall of Fame", "Reached 500 vouches"),
    ]

    y_offset = 360
    for threshold, name, desc in achievements:
        color = (255, 255, 255) if total_vouches >= threshold else (80, 80, 80)
        draw.text((560, y_offset), f"{name}", font=text_font, fill=color)
        draw.text((560, y_offset + 30), f"  — {desc}", font=desc_font, fill=color)
        y_offset += 60

    draw.text((50, 740), "Keep up the great work! • PARADOX", font=text_font, fill=(150, 150, 150))
    img_byte_arr = BytesIO()
    base.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

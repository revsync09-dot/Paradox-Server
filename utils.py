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
    
    # Calculate Rank Title
    rank_title = "🌱 Novice"
    if total_vouches >= 500: rank_title = "🌟 Hall of Fame"
    elif total_vouches >= 250: rank_title = "🏆 Legendary"
    elif total_vouches >= 100: rank_title = "👑 Elite Carrier"
    elif total_vouches >= 50: rank_title = "💎 Veteran"
    elif total_vouches >= 25: rank_title = "🔥 Trusted Booster"
    elif total_vouches >= 10: rank_title = "⭐ Rising Star"
    elif total_vouches >= 1: rank_title = "🌱 First Steps"
    
    draw.text((260, 230), rank_title, font=sub_font, fill=(0, 255, 127))
    
    # Stats Section
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
        base = Image.new('RGB', (1000, 800), color=(10, 10, 15))
    else:
        base = Image.open(bg_path).convert('RGBA')
        base = base.resize((1000, 800))

    draw = ImageDraw.Draw(base)
    
    # Dynamic font sizing for large numbers
    stat_size = 100
    if len(str(total_vouches)) > 6: stat_size = 70
    elif len(str(total_vouches)) > 8: stat_size = 50

    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 65)
        sub_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 40)
        text_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
        stat_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", stat_size)
        desc_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    except:
        title_font = sub_font = text_font = stat_font = desc_font = ImageFont.load_default()

    # Glassmorphism effect (semi-transparent overlays)
    overlay = Image.new('RGBA', (1000, 800), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    # Profile box
    overlay_draw.rounded_rectangle([30, 30, 970, 260], radius=20, fill=(20, 20, 30, 160), outline=(0, 255, 255, 100), width=2)
    # Stats box
    overlay_draw.rounded_rectangle([30, 280, 480, 770], radius=20, fill=(20, 20, 30, 160), outline=(114, 137, 218, 100), width=2)
    # Achievement box
    overlay_draw.rounded_rectangle([510, 280, 970, 770], radius=20, fill=(20, 20, 30, 160), outline=(0, 255, 127, 100), width=2)
    
    base.alpha_composite(overlay)

    # Avatar with glow
    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as resp:
            if resp.status == 200:
                avatar_data = await resp.read()
                avatar = Image.open(BytesIO(avatar_data)).convert("RGBA")
                avatar = avatar.resize((180, 180))
                mask = Image.new('L', (180, 180), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
                avatar.putalpha(mask)
                base.paste(avatar, (60, 55), avatar)
                draw.ellipse((58, 53, 242, 237), outline=(0, 255, 255), width=6)

    # Booster Name & Title
    draw.text((280, 80), f"{booster_name}", font=title_font, fill=(0, 255, 255))
    draw.text((280, 155), f"Member of Paradox Elite Services", font=text_font, fill=(200, 200, 200))
    
    # Progress Bar (dummy visual)
    draw.rounded_rectangle([280, 210, 900, 230], radius=10, fill=(40, 40, 50))
    progress = min(1.0, total_vouches / 500)
    draw.rounded_rectangle([280, 210, 280 + int(620 * progress), 230], radius=10, fill=(0, 255, 255))

    # Stats Section
    draw.text((60, 310), "🏆 TOTAL VOUCHES", font=sub_font, fill=(255, 215, 0))
    draw.text((60, 370), f"{total_vouches}", font=stat_font, fill=(255, 255, 255))
    
    draw.text((60, 520), "🎮 BY GAME", font=sub_font, fill=(114, 137, 218))
    y_offset = 580
    for game, count in list(game_breakdown.items())[:5]:
        draw.text((70, y_offset), f"• {game}: {count}", font=text_font, fill=(220, 220, 220))
        y_offset += 45

    # Achievements Section
    draw.text((540, 310), "🏅 ACHIEVEMENTS", font=sub_font, fill=(0, 255, 127))
    achievements = [
        (1, "🌱 First Steps", "Earned your first vouch"),
        (10, "⭐ Rising Star", "Reached 10 vouches"),
        (25, "🔥 Trusted Booster", "Reached 25 vouches"),
        (50, "💎 Veteran", "Reached 50 vouches"),
        (100, "👑 Elite Carrier", "Reached 100 vouches"),
        (250, "🏆 Legendary", "Reached 250 vouches"),
        (500, "🌟 Hall of Fame", "Reached 500 vouches"),
    ]

    y_offset = 380
    for threshold, name, desc in achievements:
        is_unlocked = total_vouches >= threshold
        color = (255, 255, 255) if is_unlocked else (80, 80, 80)
        marker = " [LOCKED]" if not is_unlocked else ""
        draw.text((550, y_offset), f"{name}{marker}", font=text_font, fill=color)
        draw.text((550, y_offset + 35), f"  — {desc}", font=desc_font, fill=color)
        y_offset += 65

    img_byte_arr = BytesIO()
    base.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

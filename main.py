import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio
from utils import V2Embed, create_vouch_card, create_profile_card, EmbedFactory
from supabase import create_client, Client

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CATEGORY_ID = int(os.getenv('CATEGORY_ID', 0))
STAFF_ROLE_ID = int(os.getenv('STAFF_ROLE_ID', 0))
VOUCH_CHANNEL_ID = int(os.getenv('VOUCH_CHANNEL_ID', 0))
HELPER_CHANNEL_ID = int(os.getenv('HELPER_CHANNEL_ID', 0))

# Supabase Setup
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "your_supabase_url":
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Emojis:
    # Core Emojis
    CARRY = os.getenv('EMOJI_CARRY', "⚔️")
    VOUCH = os.getenv('EMOJI_VOUCH', "⭐")
    STAFF = os.getenv('EMOJI_STAFF', "🛡️")
    TICKET = os.getenv('EMOJI_TICKET', "🎫")
    SUCCESS = os.getenv('EMOJI_SUCCESS', "✅")
    WAITING = os.getenv('EMOJI_WAITING', "⏳")
    GAME = os.getenv('EMOJI_GAME', "🎮")
    USER = os.getenv('EMOJI_USER', "👤")
    INFO = os.getenv('EMOJI_INFO', "ℹ️")
    ARROW = os.getenv('EMOJI_ARROW', "➔")
    LOCK = os.getenv('EMOJI_LOCK', "🔒")

    # Game Emojis
    ALS = os.getenv('EMOJI_ALS', "⚔️")
    AG = os.getenv('EMOJI_AG', "👻")
    AC = os.getenv('EMOJI_AC', "🗡️")
    UTD = os.getenv('EMOJI_UTD', "🌍")
    AV = os.getenv('EMOJI_AV', "🛡️")
    BL = os.getenv('EMOJI_BL', "💫")
    SP = os.getenv('EMOJI_SP', "⛵")
    ARX = os.getenv('EMOJI_ARX', "🔥")
    ASTD = os.getenv('EMOJI_ASTD', "⭐")
    AOL = os.getenv('EMOJI_AOL', "👑")

class TicketControlView(discord.ui.View):
    def __init__(self, user_id: int, game: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.game = game
        
        # Update button custom_ids to include state for persistence
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.custom_id = f"{item.custom_id}:{user_id}:{game}"

    @discord.ui.button(label="Vouch", style=discord.ButtonStyle.green, custom_id="vouch_button")
    async def vouch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update label with emoji
        button.label = f"{Emojis.SUCCESS} Vouch"
        # Parse state from custom_id if needed (for persistent view registration)
        _, user_id, game = interaction.data['custom_id'].split(':')
        user_id = int(user_id)
        
        if interaction.user.id == user_id:
            await interaction.response.send_message(
                "❌ You can't vouch for yourself!",
                ephemeral=True
            )
            return

        # Record the vouch in Supabase
        booster = interaction.user
        
        if supabase:
            try:
                supabase.table("vouches").insert({
                    "booster_id": str(booster.id),
                    "customer_id": str(user_id),
                    "game": game,
                    "booster_name": booster.name
                }).execute()
            except Exception as e:
                print(f"Error saving to Supabase: {e}")

        # Response message
        response_embed = discord.Embed(
            title="⭐ Vouch Recorded!",
            color=0x7289DA,
            description=f"Great work, {booster.mention}!"
        )
        response_embed.add_field(
            name="👤 Booster",
            value=booster.mention,
            inline=True
        )
        response_embed.add_field(
            name="🎮 Game",
            value=game,
            inline=True
        )
        response_embed.add_field(
            name="⭐ Total Vouches",
            value=f"**{len(vouches[booster.id])}**",
            inline=True
        )
        response_embed.set_footer(text="This vouch is visible on the booster's profile!")
        
        await interaction.response.send_message(embed=response_embed, ephemeral=False)

        # Post to vouch channel if configured
        if VOUCH_CHANNEL_ID != 0:
            vouch_channel = interaction.guild.get_channel(VOUCH_CHANNEL_ID)
            if vouch_channel:
                # Get total vouches from Supabase
                total_vouches = 0
                if supabase:
                    res = supabase.table("vouches").select("id", count="exact").eq("booster_id", str(booster.id)).execute()
                    total_vouches = res.count if res.count is not None else 0
                
                # Generate Canvas Image
                img_data = await create_vouch_card(
                    booster.name, 
                    game, 
                    total_vouches, 
                    booster.display_avatar.url
                )
                
                file = discord.File(img_data, filename="vouch.png")
                
                # Send ONLY the PNG
                await vouch_channel.send(file=file)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_button")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update label with emoji
        button.label = f"{Emojis.LOCK} Close Ticket"
        # Parse state from custom_id
        _, user_id, game = interaction.data['custom_id'].split(':')
        user_id = int(user_id)
        
        if interaction.user.id != user_id:
            # Allow staff to close too
            staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
            if not (staff_role and staff_role in interaction.user.roles):
                await interaction.response.send_message(
                    "❌ Only the ticket creator or staff can close this ticket!",
                    ephemeral=True
                )
                return

        close_embed = discord.Embed(
            title="🔒 Ticket Closed",
            color=0x7289DA,
            description="Thank you for using PARADOX! We hope to see you again soon."
        )
        close_embed.add_field(name="📋 Game", value=game, inline=True)
        close_embed.add_field(name="⏱️ Duration", value="Closed by " + interaction.user.mention, inline=True)
        
        await interaction.response.send_message(embed=close_embed)
        
        # Delete the channel after a short delay
        await asyncio.sleep(2)
        await interaction.channel.delete()

class ParadoxTicketView(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)  # Persistent view for 24/7 operation

    @discord.ui.select(
        custom_id="paradox_selector",
        placeholder="Select a game to start your ticket!",
        options=[
            discord.SelectOption(label="Anime Last Stand (ALS)", emoji=Emojis.ARROW, value="ALS"),
            discord.SelectOption(label="Anime Guardians (AG)", emoji=Emojis.ARROW, value="AG"),
            discord.SelectOption(label="Anime Crusaders (AC)", emoji=Emojis.ARROW, value="AC"),
            discord.SelectOption(label="Universal Tower Defense (UTD)", emoji=Emojis.ARROW, value="UTD"),
            discord.SelectOption(label="Anime Vanguards (AV)", emoji=Emojis.ARROW, value="AV"),
            discord.SelectOption(label="Bizarre Lineage (BL)", emoji=Emojis.ARROW, value="BL"),
            discord.SelectOption(label="Sailor Piece (SP)", emoji=Emojis.ARROW, value="SP"),
            discord.SelectOption(label="Anime Rangers X (ARX)", emoji=Emojis.ARROW, value="ARX"),
            discord.SelectOption(label="All Star Tower Defense (ASTD)", emoji=Emojis.ARROW, value="ASTD"),
            discord.SelectOption(label="Anime Overload (AOL)", emoji=Emojis.ARROW, value="AOL"),
        ]
    )
    async def callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORY_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)

        if not category:
            await interaction.response.send_message(
                "❌ Category not configured. Contact an admin.",
                ephemeral=True
            )
            return

        # Create private channel permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"carry-{select.values[0]}-{user.name}",
            category=category,
            overwrites=overwrites
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

        # Welcome embed inside the ticket
        embed = discord.Embed(
            title="⚔️ PARADOX | Carry Service",
            color=0x7289DA,
            description=f"Welcome {user.mention}! A professional booster will help you shortly."
        )
        
        game_emojis = {"ALS": "⚔️", "AV": "🛡️", "ASTD": "⭐"}
        game_names = {"ALS": "Anime Last Stand", "AV": "Anime Vanguards", "ASTD": "All Star Tower Defense"}
        selected_game = select.values[0]
        
        embed.add_field(
            name=f"{game_emojis.get(selected_game, '✨')} Service Type",
            value=game_names.get(selected_game, selected_game),
            inline=False
        )
        embed.add_field(
            name="👤 Customer",
            value=user.mention,
            inline=True
        )
        embed.add_field(
            name="⏱️ Status",
            value="🟢 Awaiting Booster",
            inline=True
        )
        
        embed.set_footer(text="React with ⭐ to vouch when complete!")
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await channel.send(embed=embed, view=TicketControlView(user.id, select.values[0]))


class HelperApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="helper_selector",
        placeholder="Select your specialty!",
        options=[
            discord.SelectOption(label="Anime Last Stand (ALS)", emoji=Emojis.ARROW, value="ALS"),
            discord.SelectOption(label="Anime Guardians (AG)", emoji=Emojis.ARROW, value="AG"),
            discord.SelectOption(label="Anime Crusaders (AC)", emoji=Emojis.ARROW, value="AC"),
            discord.SelectOption(label="Universal Tower Defense (UTD)", emoji=Emojis.ARROW, value="UTD"),
            discord.SelectOption(label="Anime Vanguards (AV)", emoji=Emojis.ARROW, value="AV"),
            discord.SelectOption(label="Bizarre Lineage (BL)", emoji=Emojis.ARROW, value="BL"),
            discord.SelectOption(label="Sailor Piece (SP)", emoji=Emojis.ARROW, value="SP"),
            discord.SelectOption(label="Anime Rangers X (ARX)", emoji=Emojis.ARROW, value="ARX"),
            discord.SelectOption(label="All Star Tower Defense (ASTD)", emoji=Emojis.ARROW, value="ASTD"),
            discord.SelectOption(label="Anime Overload (AOL)", emoji=Emojis.ARROW, value="AOL"),
        ]
    )
    async def callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        user = interaction.user
        specialty = select.values[0]
        
        # Game names mapping
        game_names = {
            "ALS": "Anime Last Stand",
            "AG": "Anime Guardians",
            "AC": "Anime Crusaders",
            "UTD": "Universal Tower Defense",
            "AV": "Anime Vanguards",
            "BL": "Bizarre Lineage",
            "SP": "Sailor Piece",
            "ARX": "Anime Rangers X",
            "ASTD": "All Star Tower Defense",
            "AOL": "Anime Overload"
        }
        
        # Create application embed
        embed = V2Embed(
            title=f"{Emojis.SUCCESS} Application Submitted",
            description=f"Thank you for applying, {user.mention}!\nOur team will review your specialty in **{game_names.get(specialty, specialty)}**."
        )
        
        embed.add_field(name=f"{Emojis.USER} Applicant", value=user.mention, inline=True)
        embed.add_field(name=f"{Emojis.GAME} Specialty", value=game_names.get(specialty, specialty), inline=True)
        embed.add_field(name=f"{Emojis.WAITING} Status", value="Pending Review", inline=True)
        
        embed.set_footer(text="Staff Review System • PARADOX", icon_url=user.display_avatar.url)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ParadoxBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # REQUIRED for !setup to work
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Keeps the dropdown working after restarts
        self.add_view(ParadoxTicketView())
        self.add_view(HelperApplicationView())

    async def on_ready(self):
        print(f"✅ Bot logged in as {self.user}")


bot = ParadoxBot()


@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Creates the ticket system embed"""
    if CATEGORY_ID == 0 or STAFF_ROLE_ID == 0:
        await ctx.send(
            "❌ Bot not configured. Set CATEGORY_ID and STAFF_ROLE_ID in .env file."
        )
        return

    # Header Image
    file = None
    if os.path.exists("assets/setup_header.png"):
        file = discord.File("assets/setup_header.png", filename="header.png")

    embed = V2Embed()
    
    embed.description = (
        f"**@everyone**\n\n"
        f"**{Emojis.CARRY} [ PARADOX CARRY REQUESTS ]**\n\n"
        f"**| {Emojis.INFO} Information**\n"
        f"**| Welcome to the Elite Carry Service!**\n"
        f"**| Your place for fast and professional carries.**\n\n"
        f"**| {Emojis.GAME} Supported Games**\n"
        "```diff\n"
        "+ Anime Last Stand (ALS)\n"
        "+ Anime Vanguards (AV)\n"
        "+ All Star Tower Defense (ASTD)\n"
        "+ Anime Rangers X (ARX)\n"
        "+ and many more...\n"
        "```\n"
        f"**| {Emojis.ARROW} How to start?**\n"
        f"**| Select your game from the menu below!**\n\n"
        f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**"
    )
    
    embed.set_footer(text="Paradox System • Premium Edition", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    if file:
        await ctx.send(file=file, embed=embed, view=ParadoxTicketView())
    else:
        await ctx.send(embed=embed, view=ParadoxTicketView())


@bot.command()
@commands.has_permissions(administrator=True)
async def helper_setup(ctx):
    """Creates the helper application system embed"""
    embed = V2Embed()
    
    embed.description = (
        f"**@everyone**\n\n"
        f"**{Emojis.STAFF} [ HELPER APPLICATIONS ]**\n\n"
        f"**| {Emojis.INFO} Requirements**\n"
        f"**| Must have meta units and high activity.**\n"
        f"**| Polite and professional attitude is required.**\n\n"
        f"**| {Emojis.SUCCESS} Benefits**\n"
        "```diff\n"
        "+ Gain community trust\n"
        "+ Build your reputation\n"
        "+ Access to exclusive staff channels\n"
        "+ Rank up in the Hall of Fame\n"
        "```\n"
        f"**| {Emojis.ARROW} How to apply?**\n"
        f"**| Select your specialty from the menu below!**\n\n"
        f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**"
    )
    
    embed.set_footer(text="Paradox Recruitment • Apply Now")
    
    await ctx.send(embed=embed, view=HelperApplicationView())


@bot.command()
async def vouches(ctx, user: discord.User = None):
    """Check vouches for a booster"""
    target = user or ctx.author
    
    total_vouches = 0
    game_count = {}
    
    if supabase:
        try:
            res = supabase.table("vouches").select("*").eq("booster_id", str(target.id)).execute()
            vouch_list = res.data
            total_vouches = len(vouch_list)
            
            for vouch in vouch_list:
                game = vouch["game"]
                game_count[game] = game_count.get(game, 0) + 1
        except Exception as e:
            print(f"Supabase error: {e}")
            await ctx.send("❌ Error fetching vouches from database.")
            return

    if total_vouches == 0:
        embed = V2Embed(
            title=f"{Emojis.VOUCH} Booster Profile",
            description=f"**{target.name}** hasn't earned any vouches yet! 🌱"
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)
        return
    
    # Generate the modern PNG profile card
    async with ctx.typing():
        img_data = await create_profile_card(
            target.name,
            total_vouches,
            game_count,
            target.display_avatar.url
        )
        file = discord.File(img_data, filename="profile.png")
        await ctx.send(file=file)


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN not found in .env file")
    bot.run(TOKEN)

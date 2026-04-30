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
SUPABASE_URL = os.getenv('SUPABASE_URL', '').replace('/rest/v1/', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "your_supabase_url":
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Emojis:
    def _get(key, default):
        val = os.getenv(f'EMOJI_{key}', default)
        # If it's a raw ID (digits only), wrap it in Discord emoji format
        if val and val.isdigit():
            # Using 'p' as a generic name (Discord usually ignores the name for IDs it knows)
            return f"<:p:{val}>"
        return val

    # Core Emojis
    CARRY = _get('CARRY', "⚔️")
    VOUCH = _get('VOUCH', "⭐")
    STAFF = _get('STAFF', "🛡️")
    TICKET = _get('TICKET', "🎫")
    SUCCESS = _get('SUCCESS', "✅")
    WAITING = _get('WAITING', "⏳")
    GAME = _get('GAME', "🎮")
    USER = _get('USER', "👤")
    INFO = _get('INFO', "ℹ️")
    ARROW = _get('ARROW', "➔")
    LOCK = _get('LOCK', "🔒")

    # Game Emojis
    ALS = _get('ALS', "⚔️")
    AG = _get('AG', "👻")
    AC = _get('AC', "🗡️")
    UTD = _get('UTD', "🌍")
    AV = _get('AV', "🛡️")
    BL = _get('BL', "💫")
    SP = _get('SP', "⛵")
    ARX = _get('ARX', "🔥")
    ASTD = _get('ASTD', "⭐")
    AOL = _get('AOL', "👑")

    # Ticket Control Emojis
    CLAIM = _get('CLAIM', "✅")
    UNCLAIM = _get('UNCLAIM', "🔄")
    REMIND = _get('REMIND', "🔔")
    COMPLETE = _get('COMPLETE', "✅")
    LINK = _get('LINK', "🔗")
    PLUS = _get('PLUS', "➕")
    DIAMOND = _get('DIAMOND', "💎")
    GOAL = _get('GOAL', "🎯")
    STATUS = _get('STATUS', "📊")

class TicketControlView(discord.ui.View):
    def __init__(self, user_id: int, game: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.game = game

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_button")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff = interaction.user
        embed = interaction.message.embeds[0]
        # Update Status field
        embed.set_field_at(3, name=f"{Emojis.STATUS} Status", value=f"🟢 **Claimed by {staff.mention}**", inline=False)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Unclaim", style=discord.ButtonStyle.blurple, custom_id="unclaim_button")
    async def unclaim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.set_field_at(3, name=f"{Emojis.STATUS} Status", value=f"🟡 **Waiting for claim**", inline=False)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Close Request", style=discord.ButtonStyle.red, custom_id="close_button")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

    @discord.ui.button(label="Remind User", style=discord.ButtonStyle.secondary, custom_id="remind_button")
    async def remind_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🔔 {interaction.user.mention} is waiting for you!", ephemeral=False)

    @discord.ui.button(label="Complete Run", style=discord.ButtonStyle.green, custom_id="complete_button")
    async def complete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Logic for finishing the run
        embed = interaction.message.embeds[0]
        embed.set_field_at(3, name=f"{Emojis.STATUS} Status", value=f"✅ **Run Completed**", inline=False)
        
        # Add Vouch button to this specific message
        view = discord.ui.View()
        vouch_btn = discord.ui.Button(label="Vouch Booster", style=discord.ButtonStyle.green, custom_id=f"vouch:{self.user_id}:{self.game}")
        vouch_btn.callback = self.vouch_callback
        view.add_item(vouch_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)

    async def vouch_callback(self, interaction: discord.Interaction):
        # Reuse existing vouch logic
        booster = interaction.user
        game = self.game
        user_id = self.user_id
        
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

        # Post to vouch channel
        if VOUCH_CHANNEL_ID != 0:
            vouch_channel = interaction.guild.get_channel(VOUCH_CHANNEL_ID)
            if vouch_channel:
                total_vouches = 0
                if supabase:
                    res = supabase.table("vouches").select("id", count="exact").eq("booster_id", str(booster.id)).execute()
                    total_vouches = res.count if res.count is not None else 0
                
                img_data = await create_vouch_card(booster.name, game, total_vouches, booster.display_avatar.url)
                file = discord.File(img_data, filename="vouch.png")
                await vouch_channel.send(file=file)
        
        await interaction.response.send_message(f"{Emojis.SUCCESS} Vouch registered!", ephemeral=True)
                
class JoinMethodView(discord.ui.View):
    def __init__(self, game_id: str, game_name: str):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.game_name = game_name

    @discord.ui.button(label="Join by Links", style=discord.ButtonStyle.green, custom_id="join_links")
    async def join_links(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = f"{Emojis.LINK} Join by Links"
        await self.create_ticket(interaction, "Join by Links")

    @discord.ui.button(label="Add Helper", style=discord.ButtonStyle.blurple, custom_id="add_helper")
    async def add_helper(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = f"{Emojis.PLUS} Add Helper"
        await self.create_ticket(interaction, "Add Helper")

    @discord.ui.button(label="Trade Coming Soon", style=discord.ButtonStyle.gray, custom_id="trade_soon", disabled=True)
    async def trade_soon(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.label = f"{Emojis.DIAMOND} Trade Coming Soon"

    async def create_ticket(self, interaction: discord.Interaction, method: str):
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(CATEGORY_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)

        if not category:
            await interaction.response.send_message("❌ Category not configured.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_num = datetime.now().strftime("%H%M") 
        
        channel = await guild.create_text_channel(
            name=f"{self.game_id}-{user.name}",
            category=category,
            overwrites=overwrites
        )

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

        embed = V2Embed(
            title=f"{Emojis.TICKET} Ticket #{ticket_num}",
            description=f"{user.mention} — **Your carry request is active!**"
        )
        
        embed.add_field(name=f"{Emojis.GAME} Gamemode", value=f"```\n{self.game_name}\n```", inline=False)
        embed.add_field(name=f"{Emojis.GOAL} Goal", value="```\nWaiting for details...\n```", inline=False)
        embed.add_field(name=f"{Emojis.LINK} Join via Link?", value=f"```\n{method}\n```", inline=False)
        embed.add_field(name=f"{Emojis.STATUS} Status", value=f"🟡 **Waiting for claim**", inline=False)
        
        embed.set_footer(text="PARADOX Carry Service • Fast & Reliable")
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await channel.send(content=f"{user.mention} {staff_role.mention if staff_role else ''}", embed=embed, view=TicketControlView(user.id, self.game_id))

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
        embed.set_image(url="attachment://header.png")

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

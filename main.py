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

print(f"DEBUG: CATEGORY_ID={CATEGORY_ID}")
print(f"DEBUG: STAFF_ROLE_ID={STAFF_ROLE_ID}")

# Supabase Setup
SUPABASE_URL = os.getenv('SUPABASE_URL', '').replace('/rest/v1/', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "your_supabase_url":
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Emojis:
    # Defaults
    CARRY = "⚔️"
    VOUCH = "⭐"
    STAFF = "🛡️"
    TICKET = "🎫"
    SUCCESS = "✅"
    WAITING = "⏳"
    GAME = "🎮"
    USER = "👤"
    INFO = "ℹ️"
    ARROW = "➔"
    LOCK = "🔒"
    ALS = AG = AC = UTD = AV = BL = SP = ARX = ASTD = AOL = "🎮"
    CLAIM = UNCLAIM = REMIND = COMPLETE = LINK = PLUS = DIAMOND = GOAL = STATUS = "🔹"

    @classmethod
    def update(cls, bot: commands.Bot):
        keys = [
            'CARRY', 'VOUCH', 'STAFF', 'TICKET', 'SUCCESS', 'WAITING', 'GAME', 'USER', 'INFO', 'ARROW', 'LOCK',
            'ALS', 'AG', 'AC', 'UTD', 'AV', 'BL', 'SP', 'ARX', 'ASTD', 'AOL',
            'CLAIM', 'UNCLAIM', 'REMIND', 'COMPLETE', 'LINK', 'PLUS', 'DIAMOND', 'GOAL', 'STATUS'
        ]
        
        for key in keys:
            val = os.getenv(f'EMOJI_{key}')
            if not val:
                continue
                
            if val.isdigit():
                emoji_id = int(val)
                emoji_obj = bot.get_emoji(emoji_id)
                if emoji_obj:
                    setattr(cls, key, emoji_obj)
                else:
                    # If not in cache, we don't know if it's animated. 
                    # We'll assume static for now, but str() on PartialEmoji 
                    # will at least try to render.
                    setattr(cls, key, discord.PartialEmoji(name="p", id=emoji_id, animated=False))
            else:
                setattr(cls, key, val)

class TicketControlView(discord.ui.View):
    def __init__(self, user_id: int, game: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.game = game

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_button")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff = interaction.user
        embed = interaction.message.embeds[0]
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
        embed = interaction.message.embeds[0]
        embed.set_field_at(3, name=f"{Emojis.STATUS} Status", value=f"✅ **Run Completed**", inline=False)
        
        view = discord.ui.View()
        vouch_btn = discord.ui.Button(label="Vouch Booster", style=discord.ButtonStyle.green, custom_id=f"vouch:{self.user_id}:{self.game}")
        vouch_btn.callback = self.vouch_callback
        view.add_item(vouch_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)

    async def vouch_callback(self, interaction: discord.Interaction):
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

class ParadoxTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label="Anime Last Stand (ALS)", emoji=Emojis.ALS, value="ALS"),
            discord.SelectOption(label="Anime Guardians (AG)", emoji=Emojis.AG, value="AG"),
            discord.SelectOption(label="Anime Crusaders (AC)", emoji=Emojis.AC, value="AC"),
            discord.SelectOption(label="Universal Tower Defense (UTD)", emoji=Emojis.UTD, value="UTD"),
            discord.SelectOption(label="Anime Vanguards (AV)", emoji=Emojis.AV, value="AV"),
            discord.SelectOption(label="Bizarre Lineage (BL)", emoji=Emojis.BL, value="BL"),
            discord.SelectOption(label="Sailor Piece (SP)", emoji=Emojis.SP, value="SP"),
            discord.SelectOption(label="Anime Rangers X (ARX)", emoji=Emojis.ARX, value="ARX"),
            discord.SelectOption(label="All Star Tower Defense (ASTD)", emoji=Emojis.ASTD, value="ASTD"),
            discord.SelectOption(label="Anime Overload (AOL)", emoji=Emojis.AOL, value="AOL"),
        ]
        self.select = discord.ui.Select(
            custom_id="paradox_selector",
            placeholder="Select a game to start your ticket!",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        game_id = self.select.values[0]
        game_name = [opt.label for opt in self.select.options if opt.value == game_id][0]
        if CATEGORY_ID == 0:
            await interaction.response.send_message("❌ Category not configured.", ephemeral=True)
            return
        embed = V2Embed(
            title=f"{Emojis.LINK} Select Joining Method",
            description=f"How would you like to join the helper?\n\n**Game:** `{game_name}`\n**Gamemode:** `{game_name}`\n\nPick an option below to create your ticket."
        )
        await interaction.response.send_message(embed=embed, view=JoinMethodView(game_id, game_name), ephemeral=True)

class HelperApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label="Anime Last Stand (ALS)", emoji=Emojis.ALS, value="ALS"),
            discord.SelectOption(label="Anime Guardians (AG)", emoji=Emojis.AG, value="AG"),
            discord.SelectOption(label="Anime Crusaders (AC)", emoji=Emojis.AC, value="AC"),
            discord.SelectOption(label="Universal Tower Defense (UTD)", emoji=Emojis.UTD, value="UTD"),
            discord.SelectOption(label="Anime Vanguards (AV)", emoji=Emojis.AV, value="AV"),
            discord.SelectOption(label="Bizarre Lineage (BL)", emoji=Emojis.BL, value="BL"),
            discord.SelectOption(label="Sailor Piece (SP)", emoji=Emojis.SP, value="SP"),
            discord.SelectOption(label="Anime Rangers X (ARX)", emoji=Emojis.ARX, value="ARX"),
            discord.SelectOption(label="All Star Tower Defense (ASTD)", emoji=Emojis.ASTD, value="ASTD"),
            discord.SelectOption(label="Anime Overload (AOL)", emoji=Emojis.AOL, value="AOL"),
        ]
        self.select = discord.ui.Select(
            custom_id="helper_selector",
            placeholder="Select your specialty!",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        game_id = self.select.values[0]
        game_name = [opt.label for opt in self.select.options if opt.value == game_id][0]
        embed = V2Embed(
            title=f"{Emojis.STAFF} Helper Application",
            description=f"You are applying for the position of **{game_name} Helper**.\n\nPlease answer the questions below to proceed."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ParadoxBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(ParadoxTicketView())
        self.add_view(HelperApplicationView())

    async def on_ready(self):
        Emojis.update(self)
        print(f"BOT LOGGED IN AS {self.user}")
        print(f"Active category: {CATEGORY_ID}")

bot = ParadoxBot()

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    embed = V2Embed()
    file = None
    if os.path.exists("assets/setup_header.png"):
        file = discord.File("assets/setup_header.png", filename="header.png")
        embed.set_image(url="attachment://header.png")
    
    embed.description = (
        f"**@everyone**\n\n"
        f"**{Emojis.CARRY} [ PARADOX CARRY REQUESTS ]**\n\n"
        f"**| {Emojis.INFO} Information**\n"
        f"**| Welcome to the Elite Carry Service!**\n"
        f"**| Your place for fast and professional carries.**\n\n"
        f"**| {Emojis.GAME} Supported Games**\n"
        f"```diff\n"
        f"+ Anime Last Stand (ALS)\n"
        f"+ Anime Vanguards (AV)\n"
        f"+ All Star Tower Defense (ASTD)\n"
        f"+ Anime Rangers X (ARX)\n"
        f"+ and many more...\n"
        f"```\n"
        f"**| {Emojis.ARROW} How to start?**\n"
        f"**| Select your game from the menu below!**\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    )
    embed.set_footer(text="Paradox System • Premium Edition", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    await ctx.send(file=file if file else None, embed=embed, view=ParadoxTicketView())

@bot.command()
@commands.has_permissions(administrator=True)
async def helper_setup(ctx):
    embed = V2Embed()
    file = None
    if os.path.exists("assets/setup_header.png"):
        file = discord.File("assets/setup_header.png", filename="header.png")
        embed.set_image(url="attachment://header.png")
    
    embed.description = (
        f"**@everyone**\n\n"
        f"**{Emojis.STAFF} [ HELPER APPLICATIONS ]**\n\n"
        f"**| {Emojis.INFO} Information**\n"
        f"**| Interested in joining our Elite Staff?**\n"
        f"**| We are looking for professional carriers!**\n\n"
        f"**| {Emojis.ARROW} How to apply?**\n"
        f"**| Select your main game below and answer the**\n"
        f"**| questions in the modal that appears.**\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    )
    embed.set_footer(text="Paradox System • Premium Edition", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    await ctx.send(file=file if file else None, embed=embed, view=HelperApplicationView())

@bot.command()
async def vouch(ctx, target: discord.Member, game: str):
    if target.id == ctx.author.id:
        await ctx.send("❌ You can't vouch for yourself!")
        return
    if supabase:
        try:
            supabase.table("vouches").insert({
                "booster_id": str(target.id),
                "customer_id": str(ctx.author.id),
                "game": game,
                "booster_name": target.name
            }).execute()
            
            res = supabase.table("vouches").select("id", count="exact").eq("booster_id", str(target.id)).execute()
            total_vouches = res.count if res.count is not None else 0
            
            img_data = await create_vouch_card(target.name, game, total_vouches, target.display_avatar.url)
            file = discord.File(img_data, filename="vouch.png")
            await ctx.send(file=file)
        except Exception as e:
            print(f"Vouch error: {e}")
            await ctx.send("❌ Database error.")

@bot.command()
async def profile(ctx, target: discord.Member = None):
    target = target or ctx.author
    total_vouches = 0
    game_count = {}
    if supabase:
        try:
            res = supabase.table("vouches").select("*").eq("booster_id", str(target.id)).execute()
            vouch_list = res.data
            total_vouches = len(vouch_list)
            for vouch in vouch_list:
                g = vouch["game"]
                game_count[g] = game_count.get(g, 0) + 1
        except Exception as e:
            print(f"Profile error: {e}")
            await ctx.send("❌ Database error.")
            return

    if total_vouches == 0:
        await ctx.send(f"**{target.name}** hasn't earned any vouches yet!")
        return
    
    async with ctx.typing():
        img_data = await create_profile_card(target.name, total_vouches, game_count, target.display_avatar.url)
        file = discord.File(img_data, filename="profile.png")
        await ctx.send(file=file)

@bot.command()
@commands.has_permissions(administrator=True)
async def sync(ctx):
    """Refreshes the emoji cache"""
    Emojis.update(bot)
    await ctx.send("✅ Emojis have been refreshed from cache!")

if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN not found in .env file")
    bot.run(TOKEN)

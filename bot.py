import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CATEGORY_ID = int(os.getenv('CATEGORY_ID', 0))
STAFF_ROLE_ID = int(os.getenv('STAFF_ROLE_ID', 0))

class ParadoxTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view for 24/7 operation

    @discord.ui.select(
        custom_id="paradox_selector",
        placeholder="Choose your game...",
        options=[
            discord.SelectOption(label="Anime Last Stand", value="ALS", emoji="⚔️"),
            discord.SelectOption(label="Anime Vanguards", value="AV", emoji="🛡️"),
            discord.SelectOption(label="All Star Tower Defense", value="ASTD", emoji="⭐"),
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
            title="⚔️ Paradox Carry System",
            color=discord.Color.purple()
        )
        embed.description = f"Hello {user.mention}, a booster will help you with **{select.values[0]}** shortly."
        await channel.send(embed=embed)


class ParadoxBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Keeps the dropdown working after restarts
        self.add_view(ParadoxTicketView())

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

    embed = discord.Embed(
        title="⚔️ PARADOX | Carry System",
        description="Select a game below to request a professional carry.",
        color=0x2f3136
    )
    await ctx.send(embed=embed, view=ParadoxTicketView())


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN not found in .env file")
    bot.run(TOKEN)

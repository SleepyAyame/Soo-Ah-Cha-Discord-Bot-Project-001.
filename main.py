import discord
from discord.ext import commands, tasks
from discord import app_commands
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
import pytz
import os
import random
from dotenv import load_dotenv

load_dotenv()  # Initialize loading

# Load image channel IDs from environment variable
IMAGE_CHANNEL_IDS = set(map(int, os.getenv("IMAGE_CHANNEL_IDS", "").split(",")))

# Use full custom emoji format: <name:id>
UPVOTE_EMOJI = "<:ryoucool:1358473086017605733>"
DOWNVOTE_EMOJI = "<:GWnoneMeguDed:835124420291854337>"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.members = True  # Needed to listen for member updates

class VoteBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        # Track users who voted to avoid duplicates
        self.votes = defaultdict(lambda: {"up": set(), "down": set(), "message": None})

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced.")

bot = VoteBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id not in IMAGE_CHANNEL_IDS:
        return

    has_image_attachment = any(
        attachment.content_type and attachment.content_type.startswith("image/")
        for attachment in message.attachments
    )

    has_image_embed = any(
        (embed.image and embed.image.url) or (embed.thumbnail and embed.thumbnail.url)
        for embed in message.embeds
    )

    has_image_url = any(
        word.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
        for word in message.content.split()
    )

    if has_image_attachment or has_image_embed or has_image_url:
        await message.add_reaction(UPVOTE_EMOJI)
        await message.add_reaction(DOWNVOTE_EMOJI)
        bot.votes[message.id]["message"] = message

def is_matching_emoji(reaction_emoji, target_emoji_str):
    try:
        if isinstance(reaction_emoji, str):
            return reaction_emoji == target_emoji_str
        name, emoji_id = target_emoji_str.strip("<:>").split(":")
        return str(reaction_emoji.id) == emoji_id
    except Exception:
        return False

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.channel.id not in IMAGE_CHANNEL_IDS:
        return

    if reaction.message.id in bot.votes:
        if is_matching_emoji(reaction.emoji, UPVOTE_EMOJI):
            bot.votes[reaction.message.id]["up"].add(user.id)
        elif is_matching_emoji(reaction.emoji, DOWNVOTE_EMOJI):
            bot.votes[reaction.message.id]["down"].add(user.id)

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot or reaction.message.channel.id not in IMAGE_CHANNEL_IDS:
        return

    if reaction.message.id in bot.votes:
        if is_matching_emoji(reaction.emoji, UPVOTE_EMOJI):
            bot.votes[reaction.message.id]["up"].discard(user.id)
        elif is_matching_emoji(reaction.emoji, DOWNVOTE_EMOJI):
            bot.votes[reaction.message.id]["down"].discard(user.id)

@bot.tree.command(name="leaderboard", description="Show top voted image posts.")
@app_commands.describe(top="Number of top images to show (default 5)")
async def leaderboard(interaction: discord.Interaction, top: int = 5):
    if not bot.votes:
        await interaction.response.send_message("No votes yet!", ephemeral=True)
        return

    sorted_votes = sorted(
        bot.votes.items(),
        key=lambda x: len(x[1]["up"]) - len(x[1]["down"]),
        reverse=True
    )[:top]

    embed = discord.Embed(title=f"🌟 Top {top} Voted Images", color=discord.Color.gold())

    for i, (msg_id, data) in enumerate(sorted_votes, start=1):
        message = data.get("message")

        if not message:
            for channel_id in IMAGE_CHANNEL_IDS:
                channel = bot.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(msg_id)
                        if message:
                            bot.votes[msg_id]["message"] = message
                            break
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        await asyncio.sleep(1)
                        continue

        if not message:
            continue

        up = len(data["up"])
        down = len(data["down"])
        score = up - down

        embed.add_field(
            name=f"#{i} | Score: {score} ({UPVOTE_EMOJI} {up} / {DOWNVOTE_EMOJI} {down})",
            value=f"[Jump to post]({message.jump_url}) by {message.author.mention}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remind", description="Set a reminder")
@app_commands.describe(message="Reminder text", minutes="Delay in minutes")
async def remind(interaction: discord.Interaction, message: str, minutes: int):
    await interaction.response.send_message(f"⏰ Reminder set! I'll remind you in {minutes} minute(s).", ephemeral=True)

    async def send_reminder():
        try:
            await asyncio.sleep(minutes * 60)
            await interaction.followup.send(f"🔔 Reminder: {message}", ephemeral=True)
        except Exception as e:
            print(f"Failed to send reminder: {e}")

    bot.loop.create_task(send_reminder())

@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"<a:OwO:1358587475215253564> The coin landed on **{result}**!")

@bot.tree.command(name="avatar", description="Get a user's avatar")
@app_commands.describe(user="User to get the avatar of")
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user
    avatar_url = user.display_avatar.url
    embed = discord.Embed(title=f"{user.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=avatar_url)
    await interaction.response.send_message(embed=embed)

# Run the bot using environment variable
bot.run(os.getenv("DISCORD_BOT_TOKEN"))



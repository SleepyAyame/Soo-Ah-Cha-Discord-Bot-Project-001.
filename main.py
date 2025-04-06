import discord
from discord.ext import commands, tasks
from discord import app_commands
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
import pytz
import os
import random

# Replace with your actual image channel ID
IMAGE_CHANNEL_ID = 847169382920618034

# Use full custom emoji format: <name:id>
UPVOTE_EMOJI = "<:ryoucool:1358473086017605733>"
DOWNVOTE_EMOJI = "<:GWnoneMeguDed:835124420291854337>"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True

class VoteBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.votes = defaultdict(lambda: {"up": 0, "down": 0, "message": None})

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced.")

bot = VoteBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != IMAGE_CHANNEL_ID:
        return

    has_image = any(
        attachment.content_type and attachment.content_type.startswith("image/")
        for attachment in message.attachments
    )

    if has_image:
        await message.add_reaction(UPVOTE_EMOJI)
        await message.add_reaction(DOWNVOTE_EMOJI)
        bot.votes[message.id]["message"] = message

def is_matching_emoji(reaction_emoji, target_emoji):
    return str(reaction_emoji) == target_emoji

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.channel.id != IMAGE_CHANNEL_ID:
        return

    if reaction.message.id in bot.votes:
        if is_matching_emoji(reaction.emoji, UPVOTE_EMOJI):
            bot.votes[reaction.message.id]["up"] += 1
        elif is_matching_emoji(reaction.emoji, DOWNVOTE_EMOJI):
            bot.votes[reaction.message.id]["down"] += 1

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot or reaction.message.channel.id != IMAGE_CHANNEL_ID:
        return

    if reaction.message.id in bot.votes:
        if is_matching_emoji(reaction.emoji, UPVOTE_EMOJI):
            bot.votes[reaction.message.id]["up"] -= 1
        elif is_matching_emoji(reaction.emoji, DOWNVOTE_EMOJI):
            bot.votes[reaction.message.id]["down"] -= 1

# Slash command: /leaderboard [top]
@bot.tree.command(name="leaderboard", description="Show top voted image posts.")
@app_commands.describe(top="Number of top images to show (default 5)")
async def leaderboard(interaction: discord.Interaction, top: int = 5):
    if not bot.votes:
        await interaction.response.send_message("No votes yet!", ephemeral=True)
        return

    sorted_votes = sorted(
        bot.votes.items(),
        key=lambda x: x[1]["up"] - x[1]["down"],
        reverse=True
    )[:top]

    embed = discord.Embed(title=f"\ud83c\udfc6 Top {top} Voted Images", color=discord.Color.gold())

    for i, (msg_id, data) in enumerate(sorted_votes, start=1):
        message = data["message"]
        score = data["up"] - data["down"]
        embed.add_field(
            name=f"#{i} | Score: {score} ({UPVOTE_EMOJI} {data['up']} / {DOWNVOTE_EMOJI} {data['down']})",
            value=f"[Jump to post]({message.jump_url}) by {message.author.mention}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# Slash command: /remind [message] [minutes]
@bot.tree.command(name="remind", description="Set a reminder")
@app_commands.describe(message="Reminder text", minutes="Delay in minutes")
async def remind(interaction: discord.Interaction, message: str, minutes: int):
    await interaction.response.send_message(f"⏰ Reminder set! I'll remind you in {minutes} minute(s).", ephemeral=True)

    async def send_reminder():
        await asyncio.sleep(minutes * 60)
        await interaction.followup.send(f"🔔 Reminder: {message}", ephemeral=True)

    bot.loop.create_task(send_reminder())

# Slash command: /coinflip
@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"<:Pokecoin:1358588024438395012> The coin landed on **{result}**!")

# Run the bot using environment variable
bot.run(os.getenv("DISCORD_BOT_TOKEN"))


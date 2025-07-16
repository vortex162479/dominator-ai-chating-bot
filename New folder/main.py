
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from groq import Groq
import json

load_dotenv()

groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

ACTIVE_CHANNELS_FILE = 'active_channels.json'

def load_active_channels():
    try:
        with open(ACTIVE_CHANNELS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_active_channels(channels):
    with open(ACTIVE_CHANNELS_FILE, 'w') as f:
        json.dump(channels, f)

active_channels = load_active_channels()

async def get_ai_response(message_content, user_name):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful Discord bot. Keep responses concise and friendly. You're responding to a user named " + user_name + "."
                },
                {
                    "role": "user",
                    "content": message_content
                }
            ],
            model="llama3-8b-8192",
            max_tokens=500,
            temperature=0.7
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return "Sorry, I'm having trouble processing that right now."

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Active channels: {active_channels}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)
    
    if bot.user in message.mentions:
        response = await get_ai_response(message.content, message.author.display_name)
        await message.reply(response)
        return
    
    if message.channel.id in active_channels:
        response = await get_ai_response(message.content, message.author.display_name)
        await message.reply(response)

@bot.tree.command(name="channel", description="Manage channels for auto-replies")
@app_commands.describe(
    action="What to do (set/remove/list)",
    channel="Channel to modify (optional, uses current channel if not specified)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="set", value="set"),
    app_commands.Choice(name="remove", value="remove"),
    app_commands.Choice(name="list", value="list")
])
async def channel_command(interaction: discord.Interaction, action: app_commands.Choice[str], channel: discord.TextChannel = None):
    global active_channels
    
    if channel is None:
        channel = interaction.channel
    
    if action.value == 'set':
        if channel.id not in active_channels:
            active_channels.append(channel.id)
            save_active_channels(active_channels)
            await interaction.response.send_message(f"✅ Bot will now reply to all messages in {channel.mention}")
        else:
            await interaction.response.send_message(f"❌ Bot is already active in {channel.mention}")
    
    elif action.value == 'remove':
        if channel.id in active_channels:
            active_channels.remove(channel.id)
            save_active_channels(active_channels)
            await interaction.response.send_message(f"✅ Bot will no longer reply to messages in {channel.mention}")
        else:
            await interaction.response.send_message(f"❌ Bot is not active in {channel.mention}")
    
    elif action.value == 'list':
        if active_channels:
            channel_mentions = []
            for channel_id in active_channels:
                channel_obj = bot.get_channel(channel_id)
                if channel_obj:
                    channel_mentions.append(channel_obj.mention)
            await interaction.response.send_message(f"📋 Active channels: {', '.join(channel_mentions)}")
        else:
            await interaction.response.send_message("📋 No active channels set.")

@bot.tree.command(name="help", description="Show bot commands and features")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Discord AI Bot Commands", color=0x00ff00)
    embed.add_field(
        name="/channel set [channel]", 
        value="Make bot reply to all messages in specified channel (or current channel if none specified)", 
        inline=False
    )
    embed.add_field(
        name="/channel remove [channel]", 
        value="Stop bot from replying to all messages in specified channel", 
        inline=False
    )
    embed.add_field(
        name="/channel list", 
        value="Show all active channels", 
        inline=False
    )
    embed.add_field(
        name="@mention", 
        value="Mention the bot anywhere to get a response", 
        inline=False
    )
    embed.add_field(
        name="/help", 
        value="Show this help message", 
        inline=False
    )
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
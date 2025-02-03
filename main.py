import discord
from discord.ext import commands, tasks
import sqlite3
import MySQLdb
from datetime import datetime, timedelta

# Bot setup
TOKEN = "YOURE_BOT_TOKEN"
intents = discord.Intents.default()
intents.members = True  # Enable member tracking
intents.voice_states = True  # Track voice state changes
intents.message_content = True  # Enable message content intent
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # Disable default help command

#Database setup
MYSQL_ENABLED = False  # Set to True to use MYSQL instead
MYSQL_HOST = "DB_HOST"
MYSQL_USER = "DB_USER"
MYSQL_PASSWORD = "DB_PASSWD"
MYSQL_DATABASE = "DB_NAME"

# SQLite setup
SQLITE_DATABASE = "bot_database.db"

if MYSQL_ENABLED:
    db = MySQLdb.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
else:
    db = sqlite3.connect(SQLITE_DATABASE, check_same_thread=False)

cursor = db.cursor()

if MYSQL_ENABLED:
    cursor.execute("CREATE TABLE IF NOT EXISTS allowed_users (user_id BIGINT PRIMARY KEY, username VARCHAR(255))")
    cursor.execute("CREATE TABLE IF NOT EXISTS join_timestamps (user_id BIGINT PRIMARY KEY, join_time DATETIME)")
else:
    cursor.execute("CREATE TABLE IF NOT EXISTS allowed_users (user_id INTEGER PRIMARY KEY, username TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS join_timestamps (user_id INTEGER PRIMARY KEY, join_time TEXT)")

db.commit()

# Auto-kick switch
# Disable for first time setup
auto_kick_enabled = True
spawn_protection_minutes = 5  # Time in minutes a new user is protected from auto-kick
BOT_CHANNEL_NAME = "bot-commands"  # bot channel name

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_users_loop.start()

@bot.event
async def on_message(message):
    # Log the received message
    print(f"Received message: {message.content} from {message.author}")

    # Strip the bot's mention from the message content
    if bot.user.mentioned_in(message):
        message.content = message.content.replace(f"<@{bot.user.id}>", "").strip()

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    join_time = datetime.utcnow()
    if MYSQL_ENABLED:
        cursor.execute("INSERT INTO join_timestamps (user_id, join_time) VALUES (%s, %s) ON DUPLICATE KEY UPDATE join_time=%s", (member.id, join_time, join_time))
    else:
        cursor.execute("INSERT OR REPLACE INTO join_timestamps (user_id, join_time) VALUES (?, ?)", (member.id, join_time))
    db.commit()

@tasks.loop(minutes=2)
async def check_users_loop():
    await check_users()

async def check_users():
    if not auto_kick_enabled:
        return

    guild = bot.guilds[0]  # Assumes bot is only in one server
    cursor.execute("SELECT user_id FROM allowed_users")
    allowed = {row[0] for row in cursor.fetchall()}

    for member in guild.members:
        if member.bot:
            continue

        if MYSQL_ENABLED:
            cursor.execute("SELECT join_time FROM join_timestamps WHERE user_id = %s", (member.id,))
        else:
            cursor.execute("SELECT join_time FROM join_timestamps WHERE user_id = ?", (member.id,))

        result = cursor.fetchone()
        if result:
            if MYSQL_ENABLED:
                join_time = result[0]
            else:
                join_time = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')

            if datetime.utcnow() - join_time < timedelta(minutes=spawn_protection_minutes):
                continue  # Skip if user is still under spawn protection

        if member.id not in allowed:
            if member.voice and member.voice.channel:  # Skip if user is in voice chat
                continue
            await member.kick(reason="Not in database and not in voice chat")
            print(f"Kicked {member.name} ({member.id})")

async def send_to_bot_channel(ctx, message):
    # If the context is in a server (guild), send to the bot channel
    if ctx.guild:
        channel = discord.utils.get(ctx.guild.text_channels, name=BOT_CHANNEL_NAME)
        if channel:
            await channel.send(message)
        else:
            # If the bot channel doesn't exist, send to the context channel
            await ctx.send(f"Bot channel '{BOT_CHANNEL_NAME}' not found. Sending here instead:\n{message}")
    else:
        # If the context is a DM, send the message directly to the user
        await ctx.send(message)

@bot.command()
async def help(ctx):
    help_text = (
        "**Available Commands:**\n"
        "!add @user - Add a user to the allowed list.\n"
        "!drop @user - Remove a user from the allowed list.\n"
        "!list - List all allowed users.\n"
        "!members - Show all members currently in the server.\n"
        "!toggle_autokick - Enable or disable auto-kick.\n"
        "!help - Show this help message."
    )
    await send_to_bot_channel(ctx, help_text)

@bot.command()
async def add(ctx, user: discord.Member):
    await send_to_bot_channel(ctx, f"Adding {user.name} ({user.id}) to the database...")
    if MYSQL_ENABLED:
        cursor.execute("INSERT INTO allowed_users (user_id, username) VALUES (%s, %s) ON DUPLICATE KEY UPDATE username=%s", (user.id, user.name, user.name))
    else:
        cursor.execute("INSERT OR REPLACE INTO allowed_users (user_id, username) VALUES (?, ?)", (user.id, user.name))
    db.commit()
    await send_to_bot_channel(ctx, f"Added {user.name} ({user.id}) to the database.")

@bot.command()
async def drop(ctx, user: discord.Member):
    if MYSQL_ENABLED:
        cursor.execute("DELETE FROM allowed_users WHERE user_id = %s", (user.id,))
    else:
        cursor.execute("DELETE FROM allowed_users WHERE user_id = ?", (user.id,))
    db.commit()
    await send_to_bot_channel(ctx, f"Removed {user.name} from the database.")

@bot.command()
async def list(ctx):
    if MYSQL_ENABLED:
        cursor.execute("SELECT user_id, username FROM allowed_users")
    else:
        cursor.execute("SELECT user_id, username FROM allowed_users")
    users = cursor.fetchall()
    user_list = "\n".join([f"{user[1]} ({user[0]})" for user in users]) if users else "No users in the database."
    await send_to_bot_channel(ctx, f"Allowed users:\n{user_list}")

@bot.command()
async def members(ctx):
    guild = ctx.guild
    if guild is None:
        await send_to_bot_channel(ctx, "This command can only be used in a server.")
        return

    members = "\n".join([f"{m.name} ({m.id})" for m in guild.members])
    await send_to_bot_channel(ctx, f"Server members:\n{members}")

@bot.command()
async def toggle_autokick(ctx):
    global auto_kick_enabled
    auto_kick_enabled = not auto_kick_enabled
    status = "enabled" if auto_kick_enabled else "disabled"
    await send_to_bot_channel(ctx, f"Auto-kick is now {status}.")

bot.run(TOKEN)

# Discord Kick Bot

Discord Kick Bot is a Python bot built with Discord.py that automatically kicks users who are not in the allowed list or in a voice chat after a certain time period.

## Installation

To run the bot, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ParadoxLeon/dc-kick-bot.git
   cd dc-kick-bot
2. **Install dependencies:**
   ```bash
   apt install python3-discord
   apt install python3-sqlite
   apt install python3-mysqldb
3. **Set up the database:**
   - Ensure you have MySQL or SQLite installed and configured.
   - Update main.py with your database credentials.
4. **Run:**
   
   **Set autokick to false in main.py for first time use**
   ```bash
   python3 main.py

or with a systemd unit.


## Configuration
   - Set DB to SQlite or MYSQL
   - Set you're Bot token obtained from the Discord Developer Portal.
   - Ensure your bot has the necessary permissions (e.g., Kick Members) in Discord to perform kicks.

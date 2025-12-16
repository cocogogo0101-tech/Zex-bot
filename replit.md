# Discord Bot - Arabic Management & Welcome System

## Overview
A comprehensive Discord bot written in Python using discord.py. This bot provides advanced server management features including:

- Welcome/Goodbye system with customizable messages
- Moderation commands (kick, ban, timeout, warn)
- Auto-response system
- Ticket system
- Leveling system
- Protection features (anti-spam, anti-link)
- Logging system

## Project Structure
- `main.py` - Main bot entry point
- `database.py` - SQLite database management
- `config_manager.py` - Server settings management
- `helpers.py` - Utility functions
- `embeds.py` - Discord embed templates
- `permissions.py` - Permission system
- `cmd_*.py` - Command modules (moderation, config, utility, fun, info, aliases)
- `system_*.py` - Feature systems (tickets, leveling, warnings, autoresponse, protection)
- `event_*.py` - Event handlers (welcome, logs, messages, voice)

## Setup Requirements
- Python 3.11+
- Dependencies: discord.py, python-dotenv, aiosqlite, Pillow, pytz

## Environment Variables
- `DISCORD_TOKEN` (required) - Bot token from Discord Developer Portal
- `GUILD_ID` (optional) - Guild ID for faster command syncing

## Running the Bot
The bot runs via `python main.py` and requires the DISCORD_TOKEN secret to be set.

## Recent Changes
- December 15, 2025: Initial setup for Replit environment
  - Installed Python 3.11 and dependencies
  - Created missing command modules (cmd_aliases.py, cmd_utility.py, cmd_fun.py, cmd_info.py)
  - Set up Discord Bot workflow

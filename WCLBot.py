import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import time
import datetime
import os
import logging
import json
import signal
import ApiConnector
from ServerInfo import ServerInfoSet, ServerInfo

CMD_PREFIX = "!w"
SERVERINFO_FILE = "data/server_settings.pkl"
server_settings = ServerInfoSet.load_from_file(SERVERINFO_FILE)

client = Bot(CMD_PREFIX)

@client.listen('on_ready')
async def on_ready():
	print('Logged in as {} <{}>'.format(client.user.name, client.user.id))
	print('------')
	print("Current servers:")
	for server in client.guilds:
		print("* {} ({})".format(server.name,server.id))
	print('------')
	logging.info("Logged in successfully")

@client.command()
async def hello(ctx):
	await ctx.send("Hello!")

keys = {
	"discord_token": None,
	"client_id": None,
	"client_secret": None
}
with open(".keyfile") as f:
	keys = json.load(f)

if('DISCORD_TOKEN' in os.environ and os.environ['DISCORD_TOKEN']!=None):
	keys["discord_token"] = os.environ['DISCORD_TOKEN']
if("discord_token" not in keys):
	token = input("You must specify the discord bot token: ")
	keys["discord_token"] = token

# Ensure logfile exists
file = open("logs/bot.log", "a+")
file.close()
logging.basicConfig(filename="logs/bot.log",format="(%(asctime)s) %(levelname)s:%(message)s",level=logging.INFO)
logging.info("Logging configured.")

wcl = ApiConnector.ApiConnector(keys["client_id"], keys["client_secret"], logging)

client.run(keys["discord_token"])
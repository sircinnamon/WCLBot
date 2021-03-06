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
	print('Current Time: {}'.format(datetime.datetime.now()))
	print('------')
	print("Current servers:")
	for server in client.guilds:
		print("* {} ({})".format(server.name,server.id))
	print('------')
	logging.info("Logged in successfully")
	client.get_cog("Autochecker").start_event_loop()

@client.command(hidden=True)
async def hello(ctx):
	await ctx.send("Hello!")

@client.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.MissingRequiredArgument):
		await ctx.send(error)
	elif isinstance(error, commands.BadArgument):
		await ctx.send(error)
	elif isinstance(error, commands.CheckFailure):
		await ctx.send(error)
	elif isinstance(error, commands.CommandNotFound):
		await ctx.send(error)
	elif isinstance(error, commands.UserInputError):
		logging.warning("Badly handled error!")
		print(error)
		print(type(error))
		await ctx.send(error)
	else:
		logging.warning("Badly handled error!")
		print(error)
		print(type(error))
		await ctx.send("Unknown error.")

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

client.load_extension("cogs.logger")
client.get_cog("Logger").init(logging)
client.load_extension("cogs.settings")
client.load_extension("cogs.auth")
client.get_cog("Settings").initSettings(server_settings)
client.load_extension("cogs.wcl")
client.get_cog("WCL").init(wcl)
client.load_extension("cogs.autochecker")

client.run(keys["discord_token"])
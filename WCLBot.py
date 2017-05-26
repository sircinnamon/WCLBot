import discord
import asyncio
import time
import os
import pickle
import pycraftlogs as pcl

client = discord.Client()

player_lock = asyncio.Lock()
tts_lock = asyncio.Lock()

enabled = True
message_channel = None
current_key = ""

@client.event
@asyncio.coroutine
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
@asyncio.coroutine
def on_message(message):
    global message_channel
    global enabled
    global current_key

    print(message.author.name)
    print(message.content)

    if(message.content.startswith("!report ")):
        report = message.content.split(" ")[1]
        table = pcl.wow_report_tables("damage-done",report, end=9999999, key=current_key)
        yield from client.send_message(message.channel, table[0].name)
    if(message.content.startswith("!key ")):
        new_key = message.content.split(" ")[1]
        current_key = new_key
        yield from client.send_message(message.channel, "Key updated to " + current_key)

@client.event
@asyncio.coroutine
def on_voice_state_update(before, after):
    global message_channel
    global enabled
    print("Voice state change for user " + before.name)

if(os.environ.get('DISCORD_TOKEN') == None):
    token = input("You must specify the discord bot token: ")
    os.environ['DISCORD_TOKEN'] = token

while(True):
    try:
        client.run(os.environ.get('DISCORD_TOKEN'))
    except discord.ConnectionClosed:
        print("ConnectionClosed error. Restarting")

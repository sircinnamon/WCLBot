import discord
import asyncio
import time
import os
import pickle

client = discord.Client()

player_lock = asyncio.Lock()
tts_lock = asyncio.Lock()

enabled = True
message_channel = None

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

    print(message.author.name)
    print(message.content)

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

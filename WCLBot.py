import discord
import asyncio
import time
import os
import pickle
import pycraftlogs as pcl

from ServerInfo import ServerInfo

client = discord.Client()

player_lock = asyncio.Lock()
tts_lock = asyncio.Lock()

enabled = True
current_key = None
server_settings = dict()

@client.event
@asyncio.coroutine
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    load_server_settings()

@client.event
@asyncio.coroutine
def on_message(message):
    global enabled
    global current_key

    print(message.author.name)
    print(message.content)

    if(message.content.startswith("!winitialize")):
        yield from initialize_new_server(message)
    elif(message.content.startswith("!wguild ") and verify_user_admin(message.author.id, message.server.id)):
        #format <guildname> <realmname>-<region>
        yield from update_server_guild_info(message)
    elif(message.content.startswith("!wchannel") and verify_user_admin(message.author.id, message.server.id)):
        #no extra arguments - set speaking channel to channel message is sent in
        yield from update_server_default_channel(message) 
    elif(message.content.startswith("!wadmin ") and verify_user_admin(message.author.id, message.server.id)):
        #argument should be user IDs OR @ messages to the user(s)
        yield from add_server_admin(message) 
    elif(message.content.startswith("!wreport ")):
        report = message.content.split(" ")[1]
        table = pcl.wow_report_tables("damage-done",report, end=9999999, key=current_key)
        yield from client.send_message(message.channel, table[0].name)
    elif(message.content.startswith("!wkey ")):
        new_key = message.content.split(" ")[1]
        current_key = new_key
        yield from client.send_message(message.channel, "Key updated to " + current_key)
    elif(message.content.startswith("!wtest")):
        string = str(server_settings[message.server.id])
        yield from client.send_message(message.channel, "```"+string+"```")

@client.event
@asyncio.coroutine
def on_voice_state_update(before, after):
    global message_channel
    global enabled
    print("Voice state change for user " + before.name)

def initialize_new_server(msg):
    global server_settings
    if msg.server.id in server_settings:
        return False
    else:
        new_server_info = ServerInfo(msg.server.id)
        print(msg.author.id)
        new_server_info.add_admin(msg.author.id)
        new_server_info.set_default_channel(msg.server.default_channel)
        server_settings[msg.server.id] = new_server_info
        save_server_settings()
        yield from client.send_message(msg.channel, "Added new server and admin.")
        return True

def verify_user_admin(userID, serverID):
    global server_settings
    if(serverID not in server_settings):
        return False
    serv_info = server_settings[serverID]
    if userID in serv_info.admins:
        return True
    else:
        return False

def update_server_guild_info(msg):
    global server_settings
    serv_info = server_settings[msg.server.id]
    serv_info.update_guild(msg.content.split(" ")[1], 
                           msg.content.split(" ")[2].split("-")[0], 
                           msg.content.split(" ")[2].split("-")[1]
                           )
    server_settings[msg.server.id] = serv_info
    save_server_settings()
    yield from client.send_message(msg.channel, "Server guild set to "
                                   +serv_info.guild_name
                                   +" "
                                   +serv_info.guild_realm
                                   +"-"
                                   +serv_info.guild_region)
    return True

def update_server_default_channel(msg):
    global server_settings
    serv_info = server_settings[msg.server.id]
    serv_info.set_default_channel(msg.channel.id)
    server_settings[msg.server.id] = serv_info
    save_server_settings()
    yield from client.send_message(msg.channel, "This is now the default channel!")
    return True

def add_server_admin(msg):
    global server_settings
    serv_info = server_settings[msg.server.id]
    for admin in msg.mentions:
        serv_info.add_admin(admin.id)
    else:
        for admin in msg.content.split(" "):
            if msg.server.get_member(admin) != None:
                serv_info.add_admin()
    server_settings[msg.server.id] = serv_info
    save_server_settings()
    yield from client.send_message(msg.channel, "Admins updated!")
    return True

def save_server_settings():
    global server_settings
    pkl_file = open('data/server_settings.pkl', 'wb')
    pickle.dump(server_settings, pkl_file)
    pkl_file.close()

def load_server_settings():
    global server_settings
    if(os.path.isfile('data/server_settings.pkl') == True):
        pkl_file = open('data/server_settings.pkl', 'rb')
        server_settings = pickle.load(pkl_file)
        pkl_file.close()

def get_key(key_name):
    with open(".keyfile") as f:
        keylist = f.readlines()
    for x in keylist:
        if(x.split(":"))[0] == key_name:
            return x.split(":")[1].strip()
    print(str("Key "+key_name+" not found."))
    return None

os.environ['DISCORD_TOKEN'] = get_key("discord_bot_token")
current_key = get_key("warcraftlogs_public_key")
if(os.environ.get('DISCORD_TOKEN') == None):
    token = input("You must specify the discord bot token: ")
    os.environ['DISCORD_TOKEN'] = token
if(current_key==None):
    current_key = input("You must specify the WCL API key: ")

while(True):
    try:
        client.run(os.environ.get('DISCORD_TOKEN'))
    except discord.ConnectionClosed:
        print("ConnectionClosed error. Restarting")

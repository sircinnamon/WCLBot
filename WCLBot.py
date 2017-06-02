import discord
import asyncio
import time
import datetime
import os
import pickle
import pycraftlogs as pcl
from threading import Timer, Thread
from collections import deque

from ServerInfo import ServerInfo

client = discord.Client()

player_lock = asyncio.Lock()
tts_lock = asyncio.Lock()

enabled = True
current_key = None
server_settings = dict()
thread_list = list()
report_queue = deque()

serv_not_registered_msg = ("Whoops! This server is not yet registered. Please "
                          + "have your server admin use the !winitialize command "
                          + "(!whelp for more info)!"
                          )
help_msg = ("Hello! I'm Weasel the WarcraftLogs API Discord bot! I can be "
           + "used to view logs at a glance, track attendance, brag about "
           + "parses and more! For help with setup, type '!wsetup'. For a "
           + "full command list, type '!wcommands'. I was created by "
           + "sircinnamon@gmail.com."
           )
setup_help_msg = ("If you are an admin, start by typing '!winitialize' to "
                 + "add your server to the registry. This will allow you "
                 + "to use the bot. To set up automatic log tracking, "
                 + "first type '!wguild <guildname> <realm>-<region>'."
                 + "To enable automatic log reporting, type '!wautolog'."
                 + "To enable long form reporting, type '!wlonglog'."
                 + "To change the channel the bot posts in, type '!wchannel' "
                 + "in a channel the bot can view. To allow others to change "
                 + "these settings, type '!wadmin' followed by an @ to all the " 
                 + "desired users."
                 )
command_list_msg = ("Command list to be added.")
@client.event
@asyncio.coroutine
def on_ready():
    global thread_list
    load_server_settings()
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    thread_list = startup_auto_report()
    asyncio.ensure_future(check_report_queue())
    asyncio.ensure_future(check_server_memberships())

@client.event
@asyncio.coroutine
def on_message(message):
    global enabled
    global current_key

    print(message.author.name)
    print(message.content)

    if(message.content.startswith("!winitialize")):
        yield from initialize_new_server(message)
    elif(message.content.startswith("!whelp")):
        yield from client.send_message(message.channel, help_msg)
    elif(message.content.startswith("!wsetup")):
        yield from client.send_message(message.channel, setup_help_msg)
    elif(message.content.startswith("!wcommands")):
        yield from client.send_message(message.channel, command_list_msg)
    elif(message.content.startswith("!w") and not verify_server_registered(message.server.id)):
        yield from client.send_message(message.channel, serv_not_registered_msg)
    elif(message.content.startswith("!wguild ") and verify_user_admin(message.author.id, message.server.id)):
        #format <guildname> <realmname>-<region>
        yield from update_server_guild_info(message)
    elif(message.content.startswith("!wchannel") and verify_user_admin(message.author.id, message.server.id)):
        #no extra arguments - set speaking channel to channel message is sent in
        yield from update_server_default_channel(message) 
    elif(message.content.startswith("!wadmin ") and verify_user_admin(message.author.id, message.server.id)):
        #argument should be user IDs OR @ messages to the user(s)
        yield from add_server_admin(message) 
    elif(message.content.startswith("!wreport")):
        if(len(message.content.split(" ")) < 2): 
            string = report_summary_string_long(most_recent_report(message.server.id))
        else: 
            report = message.content.split(" ")[1]
            string = report_summary_string_long(get_report(report))
        yield from client.send_message(message.channel, "```"+string+"```")
    elif(message.content.startswith("!wfights")):
        if(len(message.content.split(" ")) < 2): report = most_recent_report(message.server.id).id
        else: report = message.content.split(" ")[1]
        string = fight_list_string_long(pcl.generate_fight_list(report, key=current_key))
        string = report_summary_string(get_report(report)) + string
        yield from client.send_message(message.channel, "```"+string+"```")
    elif(message.content.startswith("!wauto") and verify_user_admin(message.author.id, message.server.id)):
        yield from toggle_auto_report(message)
    elif(message.content.startswith("!wlongmode") and verify_user_admin(message.author.id, message.server.id)):
        yield from toggle_auto_report_mode(message)
    elif(message.content.startswith("!wtest") and verify_user_admin(message.author.id, message.server.id)):
        string = str(server_settings[message.server.id])
        yield from client.send_message(message.channel, "```"+string+"```")
    elif(message.content.startswith("!wcheat") and verify_user_admin(message.author.id, message.server.id)):
        num = int(message.content.split()[1])
        __test(message, num)

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

def verify_server_registered(serverID):
    global server_settings
    if(serverID not in server_settings):
        return False
    else:
        return True

def update_server_guild_info(msg):
    global server_settings
    serv_info = server_settings[msg.server.id]
    guildname = " ".join(msg.content.split(" ")[1:(len(msg.content.split(" "))-1)])
    serv_info.update_guild(guildname, 
                           msg.content.split(guildname+" ")[1].split("-")[0], 
                           msg.content.split(guildname+" ")[1].split("-")[1]
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

def report_summary_string(report):
    date = datetime.datetime.fromtimestamp(report.start/1000).strftime('%Y-%m-%d')
    string = (report.title + ". Uploaded by " + report.owner + ". - " 
              + str(report.id) + " (" + date + ")\n")
    return string

def report_summary_string_long(report):
    global current_key
    string = report_summary_string(report) + "\n"
    fightlist = pcl.generate_fight_list(report.id, key=current_key)
    fightlist_string = fight_list_string_short(fightlist)
    string += "\n*FIGHTS* \n" + fightlist_string
    topdmg_table = pcl.wow_report_tables("damage-done", report.id, key=current_key, end=report.end-report.start)
    topdmg_string = "\n*DAMAGE DONE* \n" + table_string(topdmg_table, 3)
    topheal_table = pcl.wow_report_tables("healing", report.id, key=current_key, end=report.end-report.start)
    topheal_string = "\n*HEALING* \n" + table_string(topheal_table, 3)
    string += topdmg_string + topheal_string
    return string

def table_string(table, length):
    #Takes a table with a total (healing, damage-done, damage-taken, casts and summons)
    string = ""
    table.sort(key=lambda x: x.total)
    table.reverse()
    total = 0
    for entry in table:
        total += entry.total
    for i in range(0,min(length,len(table))):
        string += table_string_row(table[i], total)+"\n"
    return string


def table_string_row(table_entry, total):
    format_str = "{0.name:<13}".format(table_entry)
    format_str += "{0:>12} ".format(abbreviate_num(table_entry.total))
    format_str += "{:.2%} ".format(table_entry.total/total)
    return format_str

def abbreviate_num(num):
    for unit in ['K','M','B','T','Q']:
        if(abs(num)<1000):
            return "{0:3.2f}{1:s}".format(num, unit)
        num /= 1000
    return "{0:.2f}{1:2}".format(num, "Qt")

def fight_list_string_short(fightlist):
    string = ""
    newlist = list()
    for fight in fightlist:
        if fight.boss != 0:
            newlist.append((fight.name,fight.difficulty))
    fightlist = newlist
    counted = list()
    for fight in fightlist:
        if(fight not in counted):
            difficulty = get_difficulty(fight[1])[0]
            string += "{0} {1:<25}".format(difficulty,fight[0])
            if(fightlist.count(fight)>1):
                string+=" x"+str(fightlist.count(fight))
            string+="\n"
            counted.append(fight)
    return string

def fight_list_string_long(fightlist):
    string = ""
    for fight in fightlist:
        if(fight.boss != 0):
            print(str(fight.id) + " " + fight.name + " " + str(fight.boss) + str(fight.kill))
            difficulty = get_difficulty(fight.difficulty)[0]
            string += "{0:>3}: {1} {2:<25} - ".format(fight.id, difficulty, fight.name)
            if(fight.kill == False):
                string+=" Wipe:{:{align}{width}.2%}".format(fight.fightPercentage/10000,width=6,align=">")
            else:
                string+=" Kill"
            string+="\n"
    return string

def get_difficulty(int):
    difficulties = ["","","LFR","Normal","Heroic","Mythic"]
    return difficulties[int]

def get_report(reportID):
    global current_key
    return pcl.wow_get_report(reportID, key=current_key)

def most_recent_report(serverID):
    global server_settings
    global current_key
    info = server_settings[serverID]
    if not info.has_guild:
        return None
    else:
        reports = pcl.generate_guild_report_list(info.guild_name, info.guild_realm, info.guild_region, key=current_key)
        return reports[len(reports)-1]

def toggle_auto_report(msg):
    global server_settings
    global thread_list
    if not (server_settings[msg.server.id].has_guild()):
        yield from client.send_message(msg.channel, "You must set a server guild first!")
        return
    server_settings[msg.server.id].toggle_auto_report()
    save_server_settings()
    #start thread for server
    t = Timer(3, auto_report_trigger, args=(serv.server_id,))
    t.daemon = True
    t.start()
    t.name = serv.server_id
    #print(serv.server_id)
    thread_list.append(t)
    yield from client.send_message(msg.channel, "Auto Report mode is now set to "+str(server_settings[msg.server.id].auto_report)+".")

def toggle_auto_report_mode(msg):
    global server_settings
    server_settings[msg.server.id].toggle_auto_report_mode()
    save_server_settings()
    yield from client.send_message(msg.channel, "Long Auto Report mode is now set to "+str(server_settings[msg.server.id].auto_report_mode_long)+".")

def auto_report_trigger(serverID):
    print("Timer fired for server "+serverID, flush=True)
    global server_settings
    global current_key
    global thread_list
    global report_queue

    if(serverID not in server_settings):
        return
    serv_info = server_settings[serverID]
    if(serv_info.auto_report == False):
        #Cancel the auto report without refreshing
        return
    elif(serv_info.most_recent_log_start == 0):
        #If it's never been run, dont report old logs
        serv_info.most_recent_log_start = most_recent_report(serverID).start
    #Check for reports newer than the newest known by auto
    reports = list()
    try:
        reports = pcl.generate_guild_report_list(serv_info.guild_name, 
                                                 serv_info.guild_realm, 
                                                 serv_info.guild_region, 
                                                 start=serv_info.most_recent_log_start+1,
                                                 key=current_key)
    except HTTPError:
        print("HTTP Error: "+str(HTTPError))
    for r in reports:
        if(serv_info.auto_report_mode_long):
            string = report_summary_string_long(r)
        else:
            string = report_summary_string(r)
        #print(string, flush=True)
        #yield from client.send_message(serv_info.default_channel, "```"+string+"```")
        server = discord.utils.get(client.servers, id=serv_info.server_id)
        channel = discord.utils.get(server.channels, id=serv_info.default_channel)
        report_queue.append((channel, "```"+string+"```"))
    if(len(reports) != 0):
        serv_info.update_recent_log(reports[len(reports)-1].start)
        server_settings[serverID] = serv_info
        save_server_settings()
    #trigger timer for next auto check
    t = Timer(300, auto_report_trigger, args=(serverID,))
    t.daemon = True
    t.start()
    thread_list.append(t)
    #print("New Thread "+serverID, flush=True)

def startup_auto_report():
    global server_settings
    global client
    timers = list()
    for serv in server_settings.values():
        if(serv.auto_report and serv.has_guild()):
            t = Timer(3, auto_report_trigger, args=(serv.server_id,))
            t.daemon = True
            t.start()
            t.name = serv.server_id
            #print(serv.server_id)
            timers.append(t)
    return timers

def __test(msg, num):
    global server_settings
    global thread_list
    # print("Threads:")
    # for thread in thread_list:
    #     print(thread.name)
    #     print(str(thread.is_alive()))
    server_settings[msg.server.id].most_recent_log_start = num

@asyncio.coroutine
def send_msg(channel, msg):
    yield from client.send_message(channel, msg)

@asyncio.coroutine
def check_report_queue():
    global report_queue
    while(len(report_queue)==0):
        yield from asyncio.sleep(15)
    while(len(report_queue)>0):
        rep = report_queue.popleft()
        yield from client.send_message(rep[0], rep[1])
    asyncio.ensure_future(check_report_queue())

@asyncio.coroutine
def check_server_memberships():
    global server_settings
    yield from asyncio.sleep(3600)
    active_servers = list([x.id for x in client.servers])
    for entry in server_settings:
        if entry.id not in active_servers:
            del server_settings[entry.id]
            print("Server "+entry.id + " removed from memory.")
            save_server_settings()
    asyncio.ensure_future(check_server_memberships())


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

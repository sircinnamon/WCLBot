import discord
import asyncio
import time
import datetime
import os
import _pickle as pickle
import pycraftlogs as pcl
import logging
from threading import Timer, Thread
from collections import deque
from urllib.request import HTTPError

from ServerInfo import ServerInfo

client = discord.Client()

player_lock = asyncio.Lock()
tts_lock = asyncio.Lock()

enabled = True
current_key = None
server_settings = dict()
thread_list = list()
report_queue = deque()

CMD_PREFIX = "/w"
serv_not_registered_msg =   ("""```Whoops! This server is not yet registered. Please have your server admin use the !winitialize command (!whelp for more info)!```""")
help_msg =                  ("""```Hello! I'm Weasel the WarcraftLogs API Discord bot! I can be used to view logs at a glance, track attendance, brag about parses and more! For help with setup, type '!wsetup'. For a full command list, type '!wcommands'. I was created by sircinnamon@gmail.com.```""")
setup_help_msg =            ("""```If you are an admin, start by typing '!winitialize' to add your server to the registry. This will allow you to use the bot. To set up automatic log tracking, first type '!wguild <guildname> <realm>-<region>'. To enable automatic log reporting, type '!wautolog'. To enable long form reporting, type '!wlonglog'. To change the channel the bot posts in, type '!wchannel' in a channel the bot can view. To allow others to change these settings, type '!wadmin' followed by an @ to all the desired users.```""")
command_list_msg =          ("""```Here are the available commands. Some arguments must be described with <argname>=<arg>. These are often optional.
!winitialize - Add a server to the register to allow bot use.
!whelp - Show help message.
!wsetup - Show setup instructions.
!wadmin - Give users permissions to edit serverwide bot settings. Format: "!wadmin @user"
!wguild - Set the guild to default to on a server. Format: "!wguild Guild Name Server-Region"
!wchannel - Set the default channel for auto messages. Simply say command in desired channel.
!wauto - Toggle auto reporting on/off.
!wlongmode - Toggle between short and long report summaries.
!wreport - Summarize a particular report. Defaults to most recent. Format "!wreport ReportCode"
!wfights - List boss pulls in a rpeort. Defaults to most recent. Format "!wfights ReportCode"
!wtable - Show a table of a particular view. View is required. Fight defaults to all, length defaults to 20.
          Format: "!wtable view=[Healing/dps/Tank] fight=[all/fightname/fightid] length=[20/num] report=[recent/code]"
!wchar - Show a table of a particular view for a particular character. Char is required, other args same as wtable.
          Format: "!wchar char=[charname] view=[Healing/dps/Tank] fight=[all/fightname/fightid] length=[20/num] report=[recent/code]"
!watt - Show a table of characters in attendance over the last 16 reports. All arguments optional.
          Format: "!watt length=25 range=16 page=1" Range is the page size of reports, page is how mane pages back to display.
```""")
private_message_warning =   ("""\n`Sorry, only help messages can be whispered. Other private messages are not supported. Try !wcommands.`""")
admin_only_warning =   ("""\n`Sorry, only admins can execute that command.`""")

server_settings_file = "data/server_settings.pkl"

@client.event
@asyncio.coroutine
def on_ready():
    global thread_list
    load_server_settings()
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    print("Current servers:")
    for server in client.servers:
        print(server.name + " ("+server.id+")")
    print('------')
    logging.info("Logged in successfully")
    thread_list = startup_auto_report()
    asyncio.ensure_future(check_report_queue())
    asyncio.ensure_future(check_server_memberships())

@client.event
@asyncio.coroutine
def on_message(message):
    global enabled
    global current_key

    if(message.server is not None): print("["+message.server.name+"/"+message.channel.name+"] "+message.author.name+":")
    elif(message.channel.is_private and message.channel.type is discord.ChannelType.group): print("[PRIVATE/"+message.channel.name+"] "+message.author.name+":")
    elif(message.channel.is_private): print("[PRIVATE] "+message.author.name+":")
    print(message.content)

    if(message.author == client.user):
        #Ignore own messages
        return
    for command in command_set:
        for command_str in command["commands"]:
            if message.content.startswith(CMD_PREFIX+command_str):
                yield from client.send_typing(message.channel)
                if(command["allow_private"]==False and message.server is None):
                    yield from client.send_message(message.channel, shuffle_case(message.clean_content)+" "+private_message_warning)
                    return
                if(command["admin_only"] and not verify_user_admin(message.author.id, message.server.id)):
                    yield from client.send_message(message.channel, admin_only_warning)
                    return
                if(command["require_initialized"] and not verify_server_registered(message.server.id)):
                    yield from client.send_message(message.channel, serv_not_registered_msg)
                    return
                yield from command["function"](message)
                return


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
        new_server_info.add_admin(msg.author.id)
        new_server_info.set_default_channel(msg.server.default_channel.id)
        server_settings[msg.server.id] = new_server_info
        save_server_settings()
        yield from client.send_message(msg.channel, "Added new server and admin.")
        logging.info("New server "+str(msg.server.id)+" initialized.")
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
    yield from client.send_message(msg.channel, "Server guild set to <{} {}-{}>".format(serv_info.guild_name, serv_info.guild_realm, serv_info.guild_region))
    logging.info("Server {} guild info updated to <{} {}-{}>".format(str(msg.server.id),serv_info.guild_name,serv_info.guild_realm,serv_info.guild_region))
    return True

def update_server_default_channel(msg):
    global server_settings
    serv_info = server_settings[msg.server.id]
    serv_info.set_default_channel(msg.channel.id)
    server_settings[msg.server.id] = serv_info
    save_server_settings()
    yield from client.send_message(msg.channel, "This is now the default channel!")
    logging.info("Server {} default channel updated to {}".format(str(msg.server.id),str(msg.channel.id)))
    return True

def add_server_admin(msg):
    global server_settings
    serv_info = server_settings[msg.server.id]
    for admin in msg.mentions:
        serv_info.add_admin(admin.id)
        logging.info("Admin {} added to server {}".format(str(admin.id),str(msg.server.id)))
    else:
        for admin in msg.content.split(" "):
            if msg.server.get_member(admin) != None:
                serv_info.add_admin()
                logging.info("Admin {} added to server {}".format(str(admin.id),str(msg.server.id)))
    server_settings[msg.server.id] = serv_info
    save_server_settings()
    yield from client.send_message(msg.channel, "Admins updated!")
    return True

def save_server_settings():
    global server_settings
    pkl_file = open(server_settings_file, 'wb')
    pickle.dump(server_settings, pkl_file)
    pkl_file.close()

def load_server_settings():
    global server_settings
    if(os.path.isfile(server_settings_file) == True):
        pkl_file = open(server_settings_file, 'rb')
        server_settings = pickle.load(pkl_file)
        pkl_file.close()

def get_key(key_name):
    try:
        with open(".keyfile") as f:
            keylist = f.readlines()
        for x in keylist:
            if(x.split(":"))[0] == key_name:
                return x.split(":")[1].strip()
        print(str("Key "+key_name+" not found."))
        return None
    except:
        return None

def report_summary_embed(report):
    date = datetime.datetime.fromtimestamp((report.start/1000)-18000).strftime('%Y-%m-%d')
    embed = discord.Embed()
    embed.title = "{0}   -   {1}".format(report.title, str(report.id))
    embed.url="https://www.warcraftlogs.com/reports/"+str(report.id)
    embed.set_author(name="Uploaded by "+report.owner)
    embed.set_footer(text=date)
    return embed

def report_summary_embed_long(report):
    global current_key
    embed = report_summary_embed(report)
    try:
        fightlist = pcl.generate_fight_list(report.id, key=current_key)
        logging.info("Requested fight list for report "+report.id)
        if(len(fightlist)==0):raise ValueError("Fight list array is empty.")
        embed.add_field(name="**FIGHTS**", 
                        value="```"+fight_list_string_short(fightlist)+"```", 
                        inline=False)

        topdmg_table = pcl.wow_report_tables("damage-done", report.id, key=current_key, end=report.end-report.start)
        logging.info("Requested damage-done table for report "+report.id)
        embed.add_field(name="**DAMAGE DONE**", 
                        value="```"+table_string(topdmg_table, 3)+"```", 
                        inline=False)
        
        topheal_table = pcl.wow_report_tables("healing", report.id, key=current_key, end=report.end-report.start)
        logging.info("Requested healing table for report "+report.id)
        embed.add_field(name="**HEALING**", 
                        value="```"+table_string(topheal_table, 3)+"```", 
                        inline=False)
    except ValueError as ex:
        # print("Val Error: "+str(ValueError))
        logging.warning("Val Error: "+str(ex)+"-"+str(ex.args))
    return embed

def table_string(table, length, name_width=18, total=0):
    #Takes a table with a total (healing, damage-done, damage-taken, casts and summons)
    #Works for any set of entries with a total and a name
    string = ""
    table.sort(key=lambda x: x.total)
    table.reverse()
    if(total==0):
        for entry in table:
            total += entry.total
    for i in range(0,min(length,len(table))):
        string += table_string_row(table[i], total, name_width)+"\n"
    return string


def table_string_row(table_entry, total, width=18):
    name = table_entry.name
    if(len(name)>width-3):
        name = name[:width-3]+"..."
    format_str = "{0:<{width}}".format(name, width=width)
    format_str += "{0:>8} ".format(abbreviate_num(table_entry.total))
    format_str += "{:.2%} ".format(table_entry.total/total if total!= 0 else 0)
    return format_str

def abbreviate_num(num):
    for unit in ['','K','M','B','T','Q']:
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
            difficulty = get_difficulty(fight.difficulty)[0]
            string += "{0:>3}: {1} {2:<25} - ".format(fight.id, difficulty, fight.name)
            if(fight.kill == False):
                string+=" Wipe:{:{align}{width}.2%}".format(fight.fightPercentage/10000,width=6,align=">")
            else:
                string+=" Kill"
            string+="\n"
    return string

def get_difficulty(num):
    difficulties = ["","","LFR","Normal","Heroic","Mythic"]
    if(num > len(difficulties)-1):return "?"
    return difficulties[num]

def get_report(reportID):
    global current_key
    report = pcl.wow_get_report(reportID, key=current_key)
    logging.info("Requested report "+reportID)
    return report

def most_recent_report(serverID):
    global server_settings
    global current_key
    info = server_settings[serverID]
    if not info.has_guild:
        return None
    else:
        reports = pcl.generate_guild_report_list(info.guild_name, info.guild_realm, info.guild_region, key=current_key)
        logging.info("Requested guild reports for server "+serverID)
        return reports[0]

def toggle_auto_report(msg):
    global server_settings
    global thread_list
    if not (server_settings[msg.server.id].has_guild()):
        yield from client.send_message(msg.channel, "You must set a server guild first!")
        return
    server_settings[msg.server.id].toggle_auto_report()
    save_server_settings()
    #start thread for server
    t = Timer(3, auto_report_trigger, args=(msg.server.id,))
    t.daemon = True
    t.start()
    t.name = msg.server.id
    #print(serv.server_id)
    thread_list.append(t)
    logging.info("Auto report set to {} for server {}".format(str(server_settings[msg.server.id].auto_report),str(msg.server.id)))
    yield from client.send_message(msg.channel, "Auto Report mode is now set to {}.".format(str(server_settings[msg.server.id].auto_report)))

def toggle_auto_report_mode(msg):
    global server_settings
    server_settings[msg.server.id].toggle_auto_report_mode()
    save_server_settings()
    logging.info("Long auto report set to "+str(server_settings[msg.server.id].auto_report_mode_long)+" for server "+str(msg.server.id))
    yield from client.send_message(msg.channel, "Long Auto Report mode is now set to "+str(server_settings[msg.server.id].auto_report_mode_long)+".")

def auto_report_trigger(serverID, refresh=True):
    print("Timer fired for server "+serverID, flush=True)
    logging.info("Auto Report timer fired for server "+serverID)
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
    #Check for reports after and including the newest known
    #if newest known has a later end time, check it again and update report
    #if newer reports exist, summarize them and send
    reports = list()
    try:
        reports = pcl.generate_guild_report_list(serv_info.guild_name, 
                                                 serv_info.guild_realm, 
                                                 serv_info.guild_region, 
                                                 start=serv_info.most_recent_log_start,
                                                 key=current_key)
        logging.info("Requested guild reports for server "+str(serverID))
        if(len(reports)>0 and reports[0].end > serv_info.most_recent_log_end):
            if(serv_info.most_recent_log_end == 0):
                #just set it and forget it
                serv_info.most_recent_log_end = reports[0].end
            else:
                #need to update and edit report summary
                logging.info("Update to newest log ({}) found for server {}".format(str(reports[0].id),str(serverID)))
                if(serv_info.auto_report_mode_long):
                    string = report_summary_string_long(reports[0])
                else:
                    string = report_summary_string(reports[0])
                server = discord.utils.get(client.servers, id=serv_info.server_id)
                channel = discord.utils.get(server.channels, id=serv_info.default_channel)
                messageID = server_settings[serverID].most_recent_log_summary
                report_queue.append((channel, report_url(reports[0].id)+"\n```"+string+"```", messageID)) #edit message messageID to be this info now
        for r in reports[1:]:
            #ignore empty logs
            if(r.end - r.start > 1000):
                logging.info("New log {} found for server {}".format(str(r.id),str(serverID)))
                if(serv_info.auto_report_mode_long):
                    string = report_summary_string_long(r)
                else:
                    string = report_summary_string(r)
                server = discord.utils.get(client.servers, id=serv_info.server_id)
                channel = discord.utils.get(server.channels, id=serv_info.default_channel)
                report_queue.append((channel, report_url(r.id)+"\n```"+string+"```", 0)) #0 for message id to edit - ie there is none
        if(len(reports) >= 1 and (reports[len(reports)-1].end-reports[len(reports)-1].start > 1000)):
            serv_info.update_recent_log(reports[len(reports)-1].start,reports[len(reports)-1].end)
            server_settings[serverID] = serv_info
            save_server_settings()
    except HTTPError as ex:
        # print("HTTP Error: "+str(HTTPError))
        logging.warning("HTTP Error: "+str(ex)+"-"+str(ex.args))
    except KeyError as ex:
        # print("Key Error: "+str(KeyError))
        logging.warning("Key Error: "+str(ex)+"-"+str(ex.args))
    except ValueError as ex:
        # print("Val Error: "+str(ValueError))
        logging.warning("Val Error: "+str(ex)+"-"+str(ex.args))
    except Exception as ex:
        # print("Unexpected error")
        # print(type(ex))
        # print(ex.args)
        # print(str(ex))
        logging.warning("Unexpected error\n"+str(type(ex))+"\n"+str(ex.args)+"\n"+str(ex))

    #trigger timer for next auto check
    if(refresh):
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
    logging.info("Auto report started")
    return timers

@asyncio.coroutine
def send_msg(channel, msg):
    yield from client.send_message(channel, msg)

@asyncio.coroutine
def check_report_queue():
    global report_queue
    global server_settings
    while(len(report_queue)==0):
        yield from asyncio.sleep(15)
    while(len(report_queue)>0):
        rep = report_queue.popleft()
        if(rep[2]==0):
            message = yield from client.send_message(rep[0], rep[1])
        else:
            try:
                message = yield from client.get_message(rep[0],rep[2])
            except discord.NotFound:
                message = None
            if(message is None):
                message = yield from client.send_message(rep[0], rep[1])
            else:
                message = yield from client.edit_message(message, rep[1])
        server_settings[message.server.id].most_recent_log_summary = message.id
    asyncio.ensure_future(check_report_queue())

@asyncio.coroutine
def check_server_memberships():
    global server_settings
    yield from asyncio.sleep(3600)
    active_servers = list([x.id for x in client.servers])
    for entry in server_settings.values():
        if entry.server_id not in active_servers:
            del server_settings[entry.server_id]
            logging.warning("Server "+entry.server_id + " removed from memory.")
            # print("Server "+entry.id + " removed from memory.")
            save_server_settings()
    asyncio.ensure_future(check_server_memberships())

def report_url(reportID):
    return "https://www.warcraftlogs.com/reports/{}/".format(reportID)

def table_command(msg):
    global current_key
    global server_settings
    args = msg.content[8:].split(" ")
    view = None
    report = "recent"
    fight = "all"
    length = 20
    starttime = 0
    endtime = 0
    for arg in args:
        if(arg.lower().startswith("view=")):
            if(arg.lower() == "view=dps"):
                view="damage-done"
            elif(arg.lower() == "view=healer" or arg.lower() == "view=hps"):
                view="healing"
            elif(arg.lower() == "view=tank"):
                view="damage-taken"
            else:
                view=arg.lower()[5:]
        elif(arg.lower().startswith("report=")):
            report=arg[7:]
        elif(arg.lower().startswith("fight=")):
            fight=arg[6:]
        elif(arg.lower().startswith("length=")):
            length=int(arg[7:])
    if(report == "recent"):
        report = most_recent_report(msg.server.id)
    else:
        report = pcl.wow_get_report(report, key=current_key)
        logging.info("Requested report "+report.id)
    endtime=report.end-report.start
    if(fight!="all"):
        fightlist=pcl.generate_fight_list(report.id, key=current_key)
        logging.info("Requested fight list for report "+report.id)
        if(fight.isdigit()):
            #Assume its a fight id
            for f in fightlist:
                if(f.id == int(fight)):
                    starttime = f.start_time
                    endtime = f.end_time
                    bossname = f.name.upper()
        else:
            #Assume its a bossname and get kill or latest attempt
            searchkey = searchable(fight.lower())
            fightlist.reverse()
            found = False
            for f in fightlist:
                if(isinstance(f, pcl.TrashFight)):
                    pass
                elif(f.kill and (searchkey in f.name.lower() or searchkey in searchable(f.name.lower()))):
                    starttime = f.start_time
                    endtime = f.end_time
                    bossname = f.name.upper()
                    found = True
                    break
            if(not found):
                for f in fightlist:
                    if(searchkey in f.name.lower() or searchkey in searchable(f.name.lower())):
                        starttime = f.start_time
                        endtime = f.end_time
                        bossname = f.name.upper()
                        break
    else:
        bossname = "ALL"

    if(view is None):
        yield from client.send_message(msg.channel, "Please provied a view (damage-done, damage-taken, healing).")
    table = pcl.wow_report_tables(view, report.id, key=current_key, start=starttime, end=endtime)
    logging.info("Requested "+view+" table from report "+str(report.id)+" for server "+str(msg.server.id))
    embed = discord.Embed()
    embed.title = "**{0}** {1:<30}{2:>50}".format(view.upper(), bossname, "("+report.id+")")
    embed.add_field(name="Top {} values".format(length),
                    value="```{}```".format(table_string(table, length)),
                    inline=False)
    yield from client.send_message(msg.channel, embed=embed)
    return embed

def char_command(msg):
    global current_key
    global server_settings
    args = msg.content[7:].split(" ")
    view = None
    charname = None
    report = "recent"
    fight = "all"
    length = 10
    starttime = 0
    endtime = 0
    target_mode = False
    for arg in args:
        if(arg.lower().startswith("view=")):
            if(arg.lower() == "view=dps"):
                view="damage-done"
            elif(arg.lower() == "view=healer" or arg.lower() == "view=hps"):
                view="healing"
            elif(arg.lower() == "view=tank"):
                view="damage-taken"
            else:
                view=arg.lower()[5:]
        elif(arg.lower().startswith("report=")):
            report=arg[7:]
        elif(arg.lower().startswith("fight=")):
            fight=arg[6:]
        elif(arg.lower().startswith("length=")):
            length=int(arg[7:])
        elif(arg.lower().startswith("char=")):
            charname=arg[5:].lower()
        elif(arg == "-t"):
            target_mode = True
    if(report == "recent"):
        report = most_recent_report(msg.server.id)
    else:
        report = pcl.wow_get_report(report, key=current_key)
        logging.info("Requested report "+report.id)
    endtime=report.end-report.start
    fightlist=pcl.generate_fight_list(report.id, key=current_key)
    logging.info("Requested fight list for report "+report.id)
    attendance_list=get_full_attendance(fightlist)

    char=attendance_list[0]
    for player in attendance_list:
        if(charname in player.name.lower()):
            char = player
            break
    charname = player.name.lower()


    if(fight!="all"):
        bossname = "err" 
        if(fight.isdigit()):
            #Assume its a fight id
            for f in fightlist:
                if(f.id == int(fight)):
                    starttime = f.start_time
                    endtime = f.end_time
                    bossname = f.name.upper()
        else:
            #Assume its a bossname and get kill or latest attempt from chars attended fights
            attended_fights = list()
            for f in fightlist:
                if(char.attended(f.id)):
                    attended_fights.append(f)
            fightlist = attended_fights

            searchkey = searchable(fight.lower())
            fightlist.reverse()
            found = False
            for f in fightlist:
                if(f.boss!=0 and f.kill and (searchkey in f.name.lower() or searchkey in searchable(f.name.lower()))):
                    starttime = f.start_time
                    endtime = f.end_time
                    bossname = f.name.upper()
                    found = True
                    break
            if(not found):
                for f in fightlist:
                    if(searchkey in f.name.lower() or searchkey in searchable(f.name.lower())):
                        starttime = f.start_time
                        endtime = f.end_time
                        bossname = f.name.upper()
                        break
    else:
        bossname = "ALL"

    if(view is None):
        yield from client.send_message(msg.channel, "Please provied a view (damage-done, damage-taken, healing).")
    table = pcl.wow_report_tables(view, report.id, key=current_key, start=starttime, end=endtime, sourceid=char.id)
    logging.info("Requested {} table for {} from report {} for server {}".format(view,charname,str(report.id),str(msg.server.id)))
    total = 0
    for entry in table:
        total += entry.total

    string = "*{} {}* {} - {}\n".format(charname.upper(),view.upper(),bossname,report.id) + table_string(table, length, total=total)
    yield from client.send_message(msg.channel, "```"+string+"```")
    return string

def att_command(msg):
    global current_key
    global server_settings
    args = msg.content[6:].split(" ")
    page_range = 16
    page = 1
    length = 25
    for arg in args:
        if(arg.lower().startswith("range=")):
            page_range=min(int(arg.lower()[6:]),16)
        elif(arg.lower().startswith("page=")):
            page=int(arg[5:])
        elif(arg.lower().startswith("length=")):
            if(arg.lower() == "length=all"):
                length = 0
            else:
                length=int(arg[7:])
    
    #Indexed by name, data is an array of length range with the number of attended fights in report n in array[n]
    full_attendance = dict() 
    full_report_list = pcl.generate_guild_report_list(server_settings[msg.server.id].guild_name, 
                                                      server_settings[msg.server.id].guild_realm, 
                                                      server_settings[msg.server.id].guild_region, 
                                                      key=current_key)
    logging.info("Requested guild reports for server "+str(msg.server.id))
    for rep in full_report_list:
        if rep.zone == -1:
            full_report_list.remove(rep)
    report_days=""
    for i in range((page-1)*(page_range),(page*page_range)):
        print(str(page)+" "+str(i))
        report = full_report_list[i]
        report_days += datetime.datetime.fromtimestamp((report.start/1000)-18000).strftime('%a')[0]
        fightlist=pcl.generate_fight_list(report.id, key=current_key)
        logging.info("Requested fight list for report "+str(report.id))
        attendance_list=get_full_attendance(fightlist)
        for player in attendance_list:
            if player.name not in full_attendance:
                full_attendance[player.name] = [0]*page_range
            full_attendance[player.name][i-(page-1)*(page_range)] = len(player.fights.attendedFights)

    attendance_rows = [(x[0],x[1],get_attendance_percent(x[1])) for x in list(full_attendance.items())]
    attendance_rows.sort(key=lambda x: x[0])
    attendance_rows.sort(key=lambda x: x[2])
    attendance_rows.reverse()
    for row in attendance_rows:
        print(row[0]+" "+str(row[2]))
    if(length==0):length=len(attendance_rows)

    startdate = datetime.datetime.fromtimestamp((full_report_list[(page-1)*(page_range)].start/1000)-18000).strftime('%Y-%m-%d')
    enddate = datetime.datetime.fromtimestamp((full_report_list[(page)*(page_range)].start/1000)-18000).strftime('%Y-%m-%d')
    embed = discord.Embed()
    embed.title = "{0:=^50}".format("ATTENDANCE CHART")
    embed.set_footer(text=startdate+" to "+enddate)
    headers = "NAME           | % |"+report_days.upper()+"\n"
    embed.add_field(name="Table for last {} raids".format(page_range),
                    value="```"+headers+attendance_table_string(attendance_rows,length)+"```",
                    inline=False)
    yield from client.send_message(msg.channel, embed=embed)
    return embed

def searchable(string):
    for char in string:
        if char not in " abcdefghijklmnopqrstuvwxyz":
            string = string.replace(char, "")
    return string

def get_full_attendance(fightlist):
    players = {}
    for fight in fightlist:
        for player in fight.friendlies:
            if((player.id not in players) and (player.type != "NPC" and (player.type != "Unknown") and (player.type != "Pet"))):
                players[player.id] = player
    return list(players.values())

def shuffle_case(string):
    upper_string = string.upper()
    lower_string = string.lower()
    new_string = ""
    odd = False
    for upp,low in zip(upper_string,lower_string):
        if(odd): new_string = new_string+upp
        else: new_string = new_string+low
        odd = not odd
    return new_string

def get_attendance_percent(array):
    #from an array of fights attended per night, what percent are non-0
    return round(100*(len(array)-array.count(0))/len(array))

def attendance_table_string(table, length):
    #Takes a list of tuples formatted as (name,array of attended fights by report, percent attendance)
    string = ""
    table.sort(key=lambda x: x[2])
    table.reverse()
    for i in range(0,min(length,len(table))):
        string += attendance_table_string_row(table[i])+"\n"
    return string


def attendance_table_string_row(table_entry):
    name = table_entry[0]
    if(len(name)>13):
        name = name[:13]+"..."
    format_str = "{0:<{width}}".format(name, width=16)
    format_str += "{0:<4}".format(table_entry[2])
    for day in table_entry[1]:
        if(day==0): format_str+="_"
        else: format_str+="X"
    return format_str

def help_command(message):
    yield from client.send_message(message.channel, help_msg)

def setup_command(message):
    yield from client.send_message(message.channel, setup_help_msg)

def commands_command(message):
    if(message.channel.is_private):
        yield from client.send_message(message.channel, command_list_msg)
    else:
        yield from client.send_message(message.author, command_list_msg)

def report_command(message):
    yield from client.send_typing(message.channel)
    if(len(message.content.split(" ")) < 2): 
        embed = report_summary_embed_long(most_recent_report(message.server.id))
    else: 
        report = message.content.split(" ")[1]
        embed = report_summary_embed_long(get_report(report))
    yield from client.send_message(message.channel,  embed=embed)

def fights_command(message):
    if(len(message.content.split(" ")) < 2): report = most_recent_report(message.server.id).id
    else: report = message.content.split(" ")[1]
    string = fight_list_string_long(pcl.generate_fight_list(report, key=current_key))
    logging.info("Requested fight list for report "+report)
    string = report_summary_string(get_report(report)) + string
    yield from client.send_message(message.channel, "```"+string+"```")

def check_command(message):
    yield from client.send_message(message.channel, "Checking for updates...")
    auto_report_trigger(message.server.id, refresh=False)

command_set = [
    {
        "commands":["initialize","init","i"],
        "function": initialize_new_server,
        "allow_private": False,
        "admin_only": False,
        "require_initialized": False,
    },
    {
        "commands":["help"],
        "function": help_command,
        "allow_private": True,
        "admin_only": False,
        "require_initialized": False,
    },
    {
        "commands":["setup"],
        "function": setup_command,
        "allow_private": True,
        "admin_only": False,
        "require_initialized": False,
    },
    {
        "commands":["commands"],
        "function": commands_command,
        "allow_private": True,
        "admin_only": False,
        "require_initialized": False,
    },
    {
        "commands":["guild"],
        "function": update_server_guild_info,
        "allow_private": False,
        "admin_only": True,
        "require_initialized": True,
    },
    {
        "commands":["channel"],
        "function": update_server_default_channel,
        "allow_private": False,
        "admin_only": True,
        "require_initialized": True,
    },
    {
        "commands":["att", "attendance"],
        "function": att_command,
        "allow_private": False,
        "admin_only": False,
        "require_initialized": True,
    },
    {
        "commands":["admin"],
        "function": add_server_admin,
        "allow_private": False,
        "admin_only": True,
        "require_initialized": True,
    },
    {
        "commands":["report"],
        "function": report_command,
        "allow_private": False,
        "admin_only": False,
        "require_initialized": True,
    },
    {
        "commands":["fights","fight"],
        "function": fights_command,
        "allow_private": False,
        "admin_only": False,
        "require_initialized": True,
    },
    {
        "commands":["auto"],
        "function": toggle_auto_report,
        "allow_private": False,
        "admin_only": True,
        "require_initialized": True,
    },
    {
        "commands":["longmode","long"],
        "function": toggle_auto_report_mode,
        "allow_private": False,
        "admin_only": True,
        "require_initialized": True,
    },
    {
        "commands":["check"],
        "function": check_command,
        "allow_private": False,
        "admin_only": True,
        "require_initialized": True,
    },
    {
        "commands":["table","tbl"],
        "function": table_command,
        "allow_private": False,
        "admin_only": False,
        "require_initialized": True,
    },
    {
        "commands":["char"],
        "function": char_command,
        "allow_private": False,
        "admin_only": False,
        "require_initialized": True,
    },
]

current_key = get_key("warcraftlogs_public_key")
discord_token = get_key("discord_bot_token")
if(discord_token == None):
    token = input("You must specify the discord bot token: ")
    os.environ['DISCORD_TOKEN'] = token
os.environ['DISCORD_TOKEN'] = discord_token
if(current_key == None):
    current_key = input("You must specify the WCL API key: ")

file = open("logs/bot.log", "a+")
file.close()
logging.basicConfig(filename="logs/bot.log",format="(%(asctime)s) %(levelname)s:%(message)s",level=logging.INFO)
logging.info("Logging configured.")

while(True):
    try:
        client.run(os.environ.get('DISCORD_TOKEN'))
    except discord.ConnectionClosed:
        print("ConnectionClosed error. Restarting")

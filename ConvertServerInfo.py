#This script will open a pickle file of an older version of the server info class and update it to a newer version
#rename NewServerInfo.py to ServerInfo.py after
import pickle
import ServerInfo
import NewServerInfo
import os

server_settings = dict()

def write_file(dest):
    global server_settings
    pkl_file = open(dest, 'wb')
    pickle.dump(server_settings, pkl_file)
    pkl_file.close()

def read_file(sourcefile):
    global server_settings
    #read and backup settings
    if(os.path.isfile(sourcefile) == True):
        pkl_file = open(sourcefile, 'rb')
        server_settings = pickle.load(pkl_file)
        pkl_file.close()
        backup_pkl_file = open(sourcefile+"-backup", 'wb')
        pickle.dump(server_settings, backup_pkl_file)
        backup_pkl_file.close()

def create_new_entry(old_entry):
    #Modify this to construct a new entry from an old one
    new_entry = NewServerInfo.ServerInfo(old_entry.server_id)
    new_entry.admins = old_entry.admins
    new_entry.guild_name = old_entry.guild_name
    new_entry.guild_realm = old_entry.guild_realm
    new_entry.guild_region = old_entry.guild_region
    new_entry.auto_report = old_entry.auto_report
    new_entry.default_channel = old_entry.default_channel
    new_entry.auto_report_mode_long = old_entry.auto_report_mode_long
    new_entry.most_recent_log_start = old_entry.most_recent_log_start
    return new_entry

source = input("Specify the source file: ")
destination = input("Specify the output file: ")
read_file(source)
updated_server_settings = dict()
for old_entry in server_settings.items():
    new_entry = create_new_entry(old_entry[1])
    new_entry.__class__ = ServerInfo.ServerInfo
    updated_server_settings[old_entry[0]] = new_entry
server_settings = updated_server_settings
write_file(destination)



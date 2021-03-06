class ServerInfo(object):
    """Stores server settings and information in an accessible dictionary"""
    def __init__(this, server_id):
        this.server_id = server_id
        this.admins = []
        this.guild_name = None
        this.guild_realm = None
        this.guild_region = None
        this.auto_report = False
        this.default_channel = None
        this.auto_report_mode_long = False
        this.most_recent_log_start = 0

    def update_guild(self, name, realm, region):
        self.guild_name = name
        self.guild_realm = realm
        self.guild_region = region

    def has_guild(self):
        return ((self.guild_name is not None)
                and (self.guild_realm is not None)
                and (self.guild_region is not None))

    def toggle_auto_report(self):
        self.auto_report = (self.auto_report==False)

    def toggle_auto_report_mode(self):
        self.auto_report_mode_long = (self.auto_report_mode_long==False)

    def add_admin(self, userID):
        self.admins.append(userID)

    def set_default_channel(self, channelID):
        self.default_channel = channelID

    def update_recent_log(self, timestamp):
        if(self.most_recent_log_start > timestamp):
            print("Updating log time for "+this.server_id +", but something has gone wrong.")
        self.most_recent_log_start = timestamp

    def __str__(self):
        string = ("server_id="+self.server_id+"\n"
               + "admins="+str(self.admins)+"\n"
               + "guild_name="+self.guild_name+"\n"
               + "guild_realm="+self.guild_realm+"\n"
               + "guild_region="+self.guild_region+"\n"
               + "auto_report="+str(self.auto_report)+"\n"
               + "default_channel="+self.default_channel+"\n"
               + "auto_report_mode_long="+str(self.auto_report_mode_long)+"\n"
               + "most_recent_log_start="+str(self.most_recent_log_start)+"\n")
        return string
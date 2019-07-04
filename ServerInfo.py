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
        this.most_recent_log_end = 0
        this.most_recent_log_summary = 0 #the messageID (within default channel) to edit if need be

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
        self.most_recent_log_summary = 0

    def update_recent_log(self, start, end):
        if(self.most_recent_log_start > start):
            print("Updating log time for "+this.server_id +", but something has gone wrong.")
        self.most_recent_log_start = start
        self.most_recent_log_end = end

    def update_log_summary(self, messageID):
        self.most_recent_log_summary = messageID

    def __str__(self):
        string = ("server_id="+str(self.server_id)+"\n"
               + "admins="+str(self.admins)+"\n"
               + "guild_name="+str(self.guild_name)+"\n"
               + "guild_realm="+str(self.guild_realm)+"\n"
               + "guild_region="+str(self.guild_region)+"\n"
               + "auto_report="+str(self.auto_report)+"\n"
               + "default_channel="+str(self.default_channel)+"\n"
               + "auto_report_mode_long="+str(self.auto_report_mode_long)+"\n"
               + "most_recent_log_start="+str(self.most_recent_log_start)+"\n"
               + "most_recent_log_end="+str(self.most_recent_log_end)+"\n"
               + "most_recent_log_summary="+str(self.most_recent_log_summary)+"\n")
        return string
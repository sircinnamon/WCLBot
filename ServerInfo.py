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

    def update_guild(self, name, realm, region):
        self.guild_name = name
        self.guild_realm = realm
        self.guild_region = region

    def toggle_auto_report(self):
        self.auto_report = (auto_report==False)

    def toggle_auto_report_mode(self):
        self.auto_report_mode_long = (auto_report_mode_long==False)

    def add_admin(self, userID):
        self.admins.append(userID)

    def set_default_channel(self, channelID):
        self.default_channel = channelID

    def __str__(self):
        string = ("server_id="+self.server_id+"\n"
               + "admins="+str(self.admins)+"\n"
               + "guild_name="+self.guild_name+"\n"
               + "guild_realm="+self.guild_realm+"\n"
               + "guild_region="+self.guild_region+"\n"
               + "auto_report="+str(self.auto_report)+"\n"
               + "default_channel="+self.default_channel+"\n"
               + "auto_report_mode_long="+str(self.auto_report_mode_long)+"\n")
        return string
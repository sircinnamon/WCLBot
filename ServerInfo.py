import os
import _pickle as pickle
from collections.abc import MutableMapping

class ServerInfoSet(MutableMapping):
	def __init__(self):
		self.file = ""
		self.dict = {}

	@staticmethod
	def load_from_file(file):
		if(os.path.isfile(file)):
			with open(file, 'rb') as pkl_file:
				inst = pickle.load(pkl_file)
				if not isinstance(inst, ServerInfoSet): return ServerInfoSet()
				inst.file = file
				return inst
		else:
			sis = ServerInfoSet()
			sis.file = file
			sis.save_to_file()
			return sis

	def save_to_file(self, file=None):
		if(file): self.file = file
		else: file = self.file
		self.file = file
		with open(file, 'wb') as pkl_file:
			pickle.dump(self, pkl_file)
		return

	# MutableMapping Reqs
	def __str__(self): return str(self.dict)
	def __len__(self): return len(self.dict)
	def __iter__(self): return iter(self.dict)
	def __getitem__(self,k): return self.dict[k]
	def __setitem__(self,k,v): self.dict[k] = v
	def __delitem__(self,k): del self.dict[k]


class ServerInfo(object):
	"""Stores server settings and information in an accessible dictionary"""
	def __init__(self, server_id):
		self.server_id = int(server_id)
		self.admins = []
		self.guild_name = None
		self.guild_realm = None
		self.guild_region = None
		self.auto_report = False
		self.default_channel = None
		self.auto_report_mode_long = False
		self.most_recent_log_start = 0
		self.most_recent_log_end = 0
		self.most_recent_log_summary = 0 #the messageID (within default channel) to edit if need be

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

	def remove_admin(self, userID):
		if(userID in self.admins):
			self.admins.remove(userID)

	def set_default_channel(self, channelID):
		self.default_channel = channelID
		self.most_recent_log_summary = 0

	def update_recent_log(self, start, end):
		if(self.most_recent_log_start > start):
			print("Updating log time for "+self.server_id +", but something has gone wrong.")
		self.most_recent_log_start = start
		self.most_recent_log_end = end

	def update_log_summary(self, messageID):
		self.most_recent_log_summary = messageID

	def enforce_format(self):
		# Convert certain values to integers
		self.server_id = int(self.server_id)
		self.admins = list(map(lambda x: int(x), self.admins))
		self.default_channel = int(self.default_channel)
		self.most_recent_log_summary = int(self.most_recent_log_summary)

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
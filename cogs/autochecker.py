import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
from collections import deque

class Autochecker(commands.Cog):

	# COG SETUP

	def __init__(self, bot):
			self.bot = bot
			self.UPDATE_INTERVAL = 3600
			self.AUTOREPORT_TRIGGER_INTERVAL = 300
			self.SERVER_CHECK_SPACING = 3
			self.REPORTQUEUE_CHECK_INTERVAL = 10
			self.report_queue = deque()

	def start_event_loop(self):
		self.bot.loop.create_task(self.startup_auto_report())
		self.bot.loop.create_task(self.check_report_queue())

	def initialized_only():
		def pred(ctx):
				return ctx.bot.get_cog("Auth").initialized_only(ctx)
		return commands.check(pred)

	def guild_defined():
		def pred(ctx):
				return ctx.bot.get_cog("Auth").guild_defined(ctx)
		return commands.check(pred)

	def loginfo(self, *args):
		# print(*args)
		return self.bot.get_cog("Logger").info(*args)

	def logdebug(self, *args):
		# print(*args)
		return self.bot.get_cog("Logger").debug(*args)

	def logwarn(self, *args):
		# print(*args)
		return self.bot.get_cog("Logger").warn(*args)

	async def startup_auto_report(self):
		# Get reports newer than last seen for servers
		all_settings = self.bot.get_cog("Settings").settings
		for serv in all_settings.values():
			if(serv.has_guild() and serv.auto_report):
				self.bot.loop.create_task(self.auto_report_trigger(serv.server_id))
				self.loginfo("Report query task started for <{} {}-{}>[{}]".format(
					serv.guild_name, 
					serv.guild_realm, 
					serv.guild_region, 
					serv.server_id
				))
				await asyncio.sleep(self.SERVER_CHECK_SPACING)

	def start_new_report_loop(self, serverID):
		ss = self.bot.get_cog("Settings").settings[serverID]
		if ss.has_guild() and ss.auto_report:
			self.bot.loop.create_task(self.auto_report_trigger(serverID))
			self.loginfo("Report query task started for <{} {}-{}>[{}]".format(
				ss.guild_name, 
				ss.guild_realm, 
				ss.guild_region, 
				ss.server_id
			))

	async def auto_report_trigger(self, serverID, refresh=True):
		self.logdebug("Auto Report triggered for server {}".format(serverID))
		ss = self.bot.get_cog("Settings").settings[serverID]
		if not ss.auto_report:
			# Cancel auto report, dont refresh
			self.logdebug("Auto Report cancelled for server {}".format(serverID))
			return
		if(ss.most_recent_log_start == 0):
			# Never run an autoreport for this server
			# Set to most recent log start
			recent = self.bot.get_cog("WCL").most_recent_report(serverID)["startTime"]
			ss.update_recent_log(recent, 0)
			self.bot.get_cog("Settings").settings[serverID] = ss

		# Check for reports after and including newest known
		# If newest know end time has incresed, update summary
		# If new reports exist, create summary
		reports = self.bot.get_cog("WCL").generate_guild_report_list(
			ss.guild_name,
			ss.guild_realm,
			ss.guild_region,
			startTime = ss.most_recent_log_start
		)
		if reports == None: reports = []
		# Filter reports to ones longer than 1 second (Bugged uploads, etc)
		# Sort in reverse
		def f(r): return (r["endTime"] - r["startTime"] > 1000)
		reports = list(filter(f, reports))
		reports.reverse()
		if len(reports) == 0:
			self.logdebug("No reports found for server {}".format(serverID))
			await asyncio.sleep(self.AUTOREPORT_TRIGGER_INTERVAL)
			return self.bot.loop.create_task(self.auto_report_trigger(serverID))

		for r in reports:
			if(r["startTime"] < ss.most_recent_log_start):
				# Ignore it, its older than we want to consider
				continue
			elif(r["startTime"] == ss.most_recent_log_start and r["endTime"] > ss.most_recent_log_end):
				# This is probably the most recent log and endtime has increased
				if(ss.most_recent_log_end == 0):
					# Not set yet, just set it
					ss.most_recent_log_end = r["endTime"]
				else:
					# Update to a previously seen log
					self.loginfo("Update to newest log ({}) found for server {}".format(r["code"],serverID))
					if(ss.auto_report_mode_long):
						full_rep_data = self.bot.get_cog("WCL").get_report_summary_data(r["code"])
						embed = self.bot.get_cog("WCL").report_summary_embed_long(full_rep_data)
					else:
						embed = self.bot.get_cog("WCL").report_summary_embed(r)
					channel = await self.bot.fetch_channel(ss.default_channel)
					messageID = ss.most_recent_log_summary
					self.report_queue.append((channel, embed, messageID))
			elif(r["startTime"] > ss.most_recent_log_start):
				# New reports
				self.loginfo("New log {} found for server {}".format(r["code"],serverID))
				if(ss.auto_report_mode_long):
					full_rep_data = self.bot.get_cog("WCL").get_report_summary_data(r["code"])
					embed = self.bot.get_cog("WCL").report_summary_embed_long(full_rep_data)
				else:
					embed = self.bot.get_cog("WCL").report_summary_embed(r)
				channel = await self.bot.fetch_channel(ss.default_channel)
				self.report_queue.append((channel, embed, 0))
		newest_rep = reports[-1]
		if(newest_rep["endTime"] > ss.most_recent_log_end):
			ss.update_recent_log(reports[-1]["startTime"], reports[-1]["endTime"])
			self.logdebug("Server {} most recent report updated: start={}, end={}, messageid={}".format(
				serverID,
				reports[-1]["startTime"],
				reports[-1]["endTime"],
				ss.most_recent_log_summary
			))
			self.bot.get_cog("Settings").settings[serverID] = ss
			self.bot.get_cog("Settings").force_save()

		if(refresh):
			await asyncio.sleep(self.AUTOREPORT_TRIGGER_INTERVAL)
			return self.bot.loop.create_task(self.auto_report_trigger(serverID))

	async def check_report_queue(self):
		while(len(self.report_queue) == 0):
			await asyncio.sleep(self.REPORTQUEUE_CHECK_INTERVAL)
		while(len(self.report_queue) > 0):
			self.logdebug("Reports in queue")
			rep = self.report_queue.popleft()
			if(rep[2] == 0):
				# Create a new summary msg
				message = await rep[0].send(embed=rep[1])
			else:
				try:
					message = await rep[0].fetch_message(rep[2])
				except discord.NotFound:
					self.logwarn("Wanted to edit message {}, was not found!".format(rep[2]))
					message = None
				if message:
					self.loginfo("Editing message {} with updates".format(rep[2]))
					await message.edit(embed=rep[1])
				else:
					message = await rep[0].send(embed=rep[1])
			self.logdebug("Updating server [{}] most recent log summary msg id = {}".format(message.guild.id, message.id))
			self.bot.get_cog("Settings").settings[message.guild.id].most_recent_log_summary = message.id
			self.bot.get_cog("Settings").force_save()
		self.bot.loop.create_task(self.check_report_queue())

	@commands.command()
	@commands.guild_only()
	@initialized_only()
	@guild_defined()
	async def check(self, ctx):
		"""Force a check for new reports"""
		await ctx.send("Checking for updates...")
		self.bot.loop.create_task(self.auto_report_trigger(ctx.guild.id, refresh=False))


def setup(bot):
	bot.add_cog(Autochecker(bot))
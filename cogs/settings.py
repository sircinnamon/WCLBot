from discord.ext import commands
from ServerInfo import ServerInfo
from datetime import datetime
import re

class Settings(commands.Cog):
	def __init__(self, bot):
			self.bot = bot
			self.settings = {}

	def initSettings(self, s):
		self.settings = s

	def admin_only():
		def pred(ctx):
				return ctx.bot.get_cog("Auth").admin_only(ctx)
		return commands.check(pred)

	def initialized_only():
		def pred(ctx):
				return ctx.bot.get_cog("Auth").initialized_only(ctx)
		return commands.check(pred)

	def guild_defined():
		def pred(ctx):
				return ctx.bot.get_cog("Auth").guild_defined(ctx)
		return commands.check(pred)

	def loginfo(self, *args):
		return self.bot.get_cog("Logger").info(*args)

	def logwarning(self, *args):
		return self.bot.get_cog("Logger").warning(*args)

	def force_save(self):
		self.settings.save_to_file()

	@commands.command(aliases=["set", "setty", "debug"])
	@commands.guild_only()
	@admin_only()
	async def settings(self, ctx):
		"""Display currently stored settings and data about your server
		"""
		await ctx.send("```{}```".format(self.settings[ctx.guild.id]))

	@commands.command(aliases=["initialize","i"])
	@commands.guild_only()
	async def init(self, ctx):
		"""Add server to the database, allowing data to be stored.
		
		This is required to do many other commands. It only needs to be run once, unless you have kicked the bot from your server.
		"""
		if ctx.guild.id in self.settings:
			await ctx.send("Server already initialized.")
			return
		new_server_info = ServerInfo(ctx.guild.id)
		new_server_info.add_admin(ctx.message.author.id)
		new_server_info.set_default_channel(ctx.message.channel.id)
		self.settings[ctx.guild.id] = new_server_info
		self.settings.save_to_file()
		self.loginfo("New server {} initialized.".format(str(ctx.guild.id)))
		await ctx.send("Server initialized. You are now an admin. This is now the default channel.")

	@commands.command()
	@commands.guild_only()
	@admin_only()
	@initialized_only()
	async def guild(self, ctx, *, guildstring):
		"""Set default WoW Guild for server. Format: Guild Name Server-REGION

		Remove special characters if possible.
		Example: Vitium MalGanis-US
		"""
		m = re.match(r"([A-z ]+) ([A-z']+)-([A-z]{2})", guildstring)
		if m is None:
			await ctx.send("Couldn't parse guild name. Format is \"Guild Name Server-REGION\"")
			return
		ss = self.settings[ctx.guild.id]
		gName = m.group(1)
		gServer = m.group(2).replace("'","")
		gReg = m.group(3).upper()
		ss.update_guild(gName, gServer, gReg)
		self.settings[ctx.guild.id] = ss
		self.settings.save_to_file()
		self.loginfo("Server {} guild info updated to <{} {}-{}>".format(ctx.guild.id, gName, gServer, gReg))
		await ctx.send("Server guild set to <{} {}-{}>".format(gName, gServer, gReg))

	@commands.command()
	@commands.guild_only()
	@admin_only()
	@initialized_only()
	async def channel(self, ctx):
		"""Set current channel as the default for the bot to use"""
		ss = self.settings[ctx.guild.id]
		ss.set_default_channel(ctx.channel.id)
		self.settings[ctx.guild.id] = ss
		self.settings.save_to_file()
		self.loginfo("Server {} default channel updated to {}".format(ctx.guild.id, ctx.channel.id))
		await ctx.send("This is now the default channel!")

	@commands.command()
	@commands.guild_only()
	@admin_only()
	@initialized_only()
	async def admin(self, ctx):
		"""Set mentioned users as admins"""
		ss = self.settings[ctx.guild.id]
		for member in ctx.message.mentions:
			ss.add_admin(member.id)
			self.loginfo("Admin {} added to server {} by {}".format(member.id, ctx.guild.id, ctx.message.author.id))
		self.settings[ctx.guild.id] = ss
		self.settings.save_to_file()
		await ctx.send("Admins added!")

	@commands.command()
	@commands.guild_only()
	@admin_only()
	@initialized_only()
	async def unadmin(self, ctx):
		"""Remove mentioned users from admins"""
		ss = self.settings[ctx.guild.id]
		rank = ss.admins.index(ctx.message.author.id)
		for member in ctx.message.mentions:
			rmrank = ss.admins.index(member.id)
			if(rmrank == -1):
				self.loginfo("Admin removal failed: {} tried to remove {} from {}".format(ctx.message.author.id, member.id, ctx.guild.id))
				await ctx.send("{} is not an admin!".format(member.nick))
			elif(rmrank < rank):
				self.loginfo("Admin removal failed: {} tried to remove {} from {}".format(ctx.message.author.id, member.id, ctx.guild.id))
				await ctx.send("{} outranks you!".format(member.nick))
			elif(len(ss.admins) == 1):
				self.loginfo("Admin removal failed: {} tried to remove {} from {}".format(ctx.message.author.id, member.id, ctx.guild.id))
				await ctx.send("{} is the only admin! Can't remove them.".format(member.nick))
			else:
				self.loginfo("Admin {} removed from server {} by {}".format(member.id, ctx.guild.id, ctx.message.author.id))
				ss.remove_admin(member.id)
		self.settings[ctx.guild.id] = ss
		self.settings.save_to_file()
		await ctx.send("Admins updated!")

	@commands.command()
	@commands.guild_only()
	@admin_only()
	@initialized_only()
	@guild_defined()
	async def auto(self, ctx):
		"""Toggle auto reporting

		When autoreporting is enabled, the bot will query your default guild for reports on warcraftlogs.
		If a new report is found, it will display a summary of that report and a link in the default channel.
		"""
		ss = self.settings[ctx.guild.id]
		ss.toggle_auto_report()
		autochecker = self.bot.get_cog("Autochecker")
		if(autochecker):
			autochecker.start_new_report_loop(ctx.guild.id)
		self.settings[ctx.guild.id] = ss
		self.settings.save_to_file()
		self.loginfo("Auto report set to {} for server {}".format(ss.auto_report, ctx.guild.id))
		await ctx.send("Auto Report mode is now set to {}.".format(ss.auto_report))

	@commands.command(aliases=["longmode"])
	@commands.guild_only()
	@admin_only()
	@initialized_only()
	@guild_defined()
	async def long(self, ctx):
		"""Toggle long summaries of auto reports

		When enabled, report summaries will show a fight list as well as top dps and healers.
		"""
		ss = self.settings[ctx.guild.id]
		ss.toggle_auto_report_mode()
		self.settings[ctx.guild.id] = ss
		self.settings.save_to_file()
		self.loginfo("Long auto report set to {} for server {}".format(ss.auto_report_mode_long, ctx.guild.id))
		await ctx.send("Long Auto Report mode is now set to {}.".format(ss.auto_report_mode_long))

	@commands.command(aliases=["resethistory"])
	@commands.guild_only()
	@admin_only()
	@initialized_only()
	@guild_defined()
	async def reset(self, ctx):
		"""Reset settings related to autoreporting

		If timestamps become corrupted this may allow them to be easily fixed.

		This can happen if multiple overlapping logs are uploaded at once, or if a log is corrupted during upload.
		"""
		ss = self.settings[ctx.guild.id]
		ss.toggle_auto_report_mode()
		recent = self.bot.get_cog("WCL").most_recent_report(ctx.guild.id)["startTime"]
		ss.most_recent_log_start = recent
		ss.most_recent_log_end = recent
		ss.most_recent_log_summary = 0
		self.settings[ctx.guild.id] = ss
		self.settings.save_to_file()
		self.logwarning("Restting report history for server {}".format(ctx.guild.id))
		await ctx.send("Reset server history.")


def setup(bot):
	bot.add_cog(Settings(bot))

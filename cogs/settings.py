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

	@commands.command(aliases=["set", "setty", "debug"])
	@commands.guild_only()
	@admin_only()
	async def settings(self, ctx):
		await ctx.send("```{}```".format(self.settings[ctx.guild.id]))

	@commands.command(aliases=["initialize","i"])
	@commands.guild_only()
	async def init(self, ctx):
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
	async def guild(self, ctx, *, arg):
		m = re.match(r"([A-z ]+) ([A-z']+)-([A-z]{2})", arg)
		if m is None:
			await ctx.send("Couldn't parse guild name. Format is \"Guild Name ServerName-REGION\"")
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
		ss = self.settings[ctx.guild.id]
		ss.toggle_auto_report()
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
		ss = self.settings[ctx.guild.id]
		ss.toggle_auto_report_mode()
		now = int(datetime.now().timestamp() * 1000) # Current time as ms since epoch
		ss.most_recent_log_start = now
		ss.most_recent_log_end = now
		ss.most_recent_log_summary = 0
		self.settings[ctx.guild.id] = ss
		self.settings.save_to_file()
		self.logwarning("Restting report history for server {}".format(ctx.guild.id))
		await ctx.send("Reset server history.")


def setup(bot):
	bot.add_cog(Settings(bot))

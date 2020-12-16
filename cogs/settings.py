from discord.ext import commands
from ServerInfo import ServerInfo
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

	@commands.command(aliases=["set", "setty"])
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
		await ctx.send("Server guild set to <{} {}-{}>".format(gName, gServer, gReg))


def setup(bot):
	bot.add_cog(Settings(bot))

from discord.ext import commands
from discord import TextChannel

class Auth(commands.Cog):
	def __init__(self, bot):
			self.bot = bot

	def admin_only(self, ctx):
		settings = ctx.bot.get_cog("Settings").settings
		author = ctx.message.author.id
		if not isinstance(ctx.message.channel, TextChannel):
			return False
		serv = ctx.message.guild.id
		if(serv not in settings): return False
		if(author in settings[serv].admins):
			return True
		return	False

	def initialized_only(self, ctx):
		settings = ctx.bot.get_cog("Settings").settings
		serv = ctx.message.guild.id
		if(serv not in settings): return False
		return True

	def guild_defined(self, ctx):
		settings = ctx.bot.get_cog("Settings").settings
		serv = ctx.message.guild.id
		return settings[serv].has_guild()

def setup(bot):
	bot.add_cog(Auth(bot))
from discord.ext import commands
from ServerInfo import ServerInfo
class Settings(commands.Cog):
	def __init__(self, bot):
			self.bot = bot
			self.settings = {}

	def initSettings(self, s):
		self.settings = s

	def adminCheck(ctx):
		return ctx.bot.get_cog("Auth").adminCheck(ctx)

	@commands.command(aliases=["set", "setty"])
	@commands.guild_only()
	@commands.check(adminCheck)
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

def setup(bot):
	bot.add_cog(Settings(bot))

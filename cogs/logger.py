from discord.ext import commands

class Logger(commands.Cog):
	def __init__(self, bot):
			self.bot = bot
			self.logger = None

	def owner_only():
		def pred(ctx):
				return ctx.bot.get_cog("Auth").owner_only(ctx)
		return commands.check(pred)

	def init(self, lgr):
		self.logger = lgr

	@commands.command(aliases=["ll"])
	@commands.guild_only()
	@owner_only()
	async def loglevel(self, ctx):
		level="UNKNOWN"
		if not self.logger:
			await ctx.send("No logger defined.")
			return
		elif self.logger.getLogger().getEffectiveLevel() != self.logger.INFO:
			self.logger.getLogger.setLevel(self.logger.info)
			level="INFO"
		else:
			self.logger.getLogger.setLevel(self.logger.debug)
			level="DEBUG"
		await ctx.send("Log level set to {}.".format(level))

	def debug(self, *args):
		if(self.logger):
			return self.logger.debug(*args)

	def info(self, *args):
		if(self.logger):
			return self.logger.info(*args)

	def warn(self, *args):
		if(self.logger):
			return self.logger.warning(*args)


def setup(bot):
	bot.add_cog(Logger(bot))
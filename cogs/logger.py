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

	@commands.command(aliases=["ll"], hidden=True)
	@commands.guild_only()
	@owner_only()
	async def loglevel(self, ctx):
		level="UNKNOWN"
		if not self.logger:
			await ctx.send("No logger defined.")
			return
		elif self.logger.getLogger().getEffectiveLevel() != self.logger.INFO:
			self.logger.getLogger().setLevel(self.logger.INFO)
			level="INFO"
		else:
			self.logger.getLogger().setLevel(self.logger.DEBUG)
			level="DEBUG"
		await ctx.send("Log level set to {}.".format(level))

	def debug(self, *args):
		if(self.logger):
			return self.logger.debug(*args)

	def info(self, *args):
		if(self.logger):
			return self.logger.info(*args)

	def warning(self, *args):
		if(self.logger):
			return self.logger.warning(*args)

	def error(self, *args):
		if(self.logger):
			return self.logger.error(*args)


def setup(bot):
	bot.add_cog(Logger(bot))
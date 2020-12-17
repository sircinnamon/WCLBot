from discord.ext import commands
from discord import Embed
from datetime import datetime, timezone
import dateutil.tz
import typing

class WCL(commands.Cog):

	# COG SETUP

	def __init__(self, bot):
			self.bot = bot
			self.wcl = None

	def init(self, connector):
		self.wcl = connector

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

	def logdebug(self, *args):
		return self.bot.get_cog("Logger").debug(*args)

	def logwarning(self, *args):
		return self.bot.get_cog("Logger").warning(*args)

	def logerror(self, *args):
		return self.bot.get_cog("Logger").error(*args)

	# WCL API GENERICS

	def get_report(self, reportId):
		"""Request a single report by ID
		"""
		query = """
		query {{
			reportData {{
				report(
					code: "{code}"
				) {{
					code
					title
					owner {{ name }}
					startTime
					endTime
					zone {{ id }}
				}}
			}}
		}}
		""".format(code=reportId)
		try:
			json_data = self.wcl.generic_request(query)
			json_data = json_data["data"]["reportData"]["report"]
		except ValueError as e:
			logerror("Parse error in generate_guild_report_list: {}".format(e.args))
			#If the website is not a json obj, just return an empty set
			json_data = {}
		return json_data

	def generate_guild_report_list(self, guild_name, server_name, server_region, start=None, end=None):
		"""Request a set of uploaded reports for a specified guild.

		Keyword arguments:
		start -- UNIX start time to contain search
		end -- UNIX end time to contain search
		"""
		optionals = ""
		optionals += "startTime: {} ".format(start) if start else ""
		optionals += "endTime: {} ".format(end) if end else ""
		query = """
		query {{
			reportData {{
				reports(
					guildName: "{name}"
					guildServerSlug: "{server}"
					guildServerRegion: "{region}"
					{optionals}
				) {{
					data {{
						code
						title
						owner {{ name }}
						startTime
						endTime
						zone {{ id }}
					}}
				}}
			}}
		}}
		""".format(name=guild_name, server=server_name, region=server_region, optionals=optionals)
		try:
			json_data = self.wcl.generic_request(query)
			json_data = json_data["data"]["reportData"]["reports"]["data"]
		except ValueError as e:
			logerror("Parse error in generate_guild_report_list: {}".format(e.args))
			#If the website is not a json obj, just return an empty set
			json_data = {}
		return json_data

	def most_recent_report(self, serverId):
		ss = self.bot.get_cog("Settings").settings[serverId]
		if not ss.has_guild():
			return None
		reports = self.generate_guild_report_list(ss.guild_name, ss.guild_realm, ss.guild_region)
		self.logdebug("Requested guild report list for server {}".format(serverId))
		if(len(reports) > 0): return reports[0]

	def report_summary_embed(self, report):
		date = datetime.fromtimestamp(report["startTime"]/1000, tz=dateutil.tz.gettz("UTC"))
		date.replace(tzinfo=dateutil.tz.gettz("US/Eastern"))
		date = date.strftime("%Y-%m-%d")
		embed = Embed()
		embed.title = "**{0:<60}** {1:>18}".format(report["title"], "("+str(report["code"])+")")
		embed.url = "https://www.warcraftlogs.com/reports/"+str(report["code"])
		embed.set_footer(text="Report uploaded by {} on {}".format(report["owner"]["name"],date))
		return embed

	def report_summary_embed_long(self, report):
		embed = self.report_summary_embed(report)
		return embed

	# BOT COMMANDS

	@commands.command()
	async def temp(self, ctx, *args):
		ss = ctx.bot.get_cog("Settings").settings[ctx.guild.id]
		# start = None
		# end = None
		# for a in args:
		# 	if a.startswith("start="):
		# 		start = int(a.split("start=")[1])
		# 	elif a.startswith("end="):
		# 		end = int(a.split("end=")[1])
		# raw = self.generate_guild_report_list(ss.guild_name, ss.guild_realm, ss.guild_region, start=start, end=end)
		raw = self.most_recent_report(ctx.guild.id)
		rep = self.get_report(raw["code"])
		await ctx.send("```{}```".format(rep))

	@commands.command(aliases=["rep"])
	@initialized_only()
	async def report(self, ctx, rep_id: typing.Optional[str]):
		async with ctx.channel.typing():
			ss = ctx.bot.get_cog("Settings").settings[ctx.guild.id]
			if rep_id:
				embed = self.report_summary_embed_long(self.get_report(rep_id))
			elif ss.has_guild():
				embed = self.report_summary_embed_long(self.most_recent_report(ctx.guild.id))
			else: await ctx.send("No guild or report id provided!"); return

			await ctx.send(embed=embed)

def setup(bot):
	bot.add_cog(WCL(bot))

from discord.ext import commands
from discord import Embed, Colour
from datetime import datetime, timezone
from time import time
from requests.exceptions import HTTPError
import dateutil.tz
import typing

class WCL(commands.Cog):

	# COG SETUP

	def __init__(self, bot):
			self.bot = bot
			self.wcl = None
			self.ZONE_IMAGE_URL = "https://assets.rpglogs.com/img/warcraft/zones/zone-{}.png"
			self.CLASS_COLOURS = {
				"DeathKnight":0xC41F3B,
				"DemonHunter":0xA330C9,
				"Druid":0xFF7D0A,
				"Hunter":0xABD473,
				"Mage":0x40C7EB,
				"Monk":0x00FF96,
				"Paladin":0xF58CBA,
				"Priest":0xFFFFFF,
				"Rogue":0xFFF569,
				"Shaman":0x0070DE,
				"Warlock":0x8787ED,
				"Warrior":0xC79C6E
			}
			self.DIFFICULTY_COLOURS = {
				"LFR":0x1eff00,
				"Normal":0x0070dd,
				"Heroic":0xa335ee,
				"Mythic":0xff8000
			}
			self.TABLE_QUERY_ALL = "{alias}: table(dataType: {view} startTime: {startTime} endTime: {endTime})\n"
			self.TABLE_QUERY_SOURCE = "{alias}: table(dataType: {view} startTime: {startTime} endTime: {endTime} sourceID: {sourceID})\n"
			self.ACTOR_QUERY = "{alias}: masterData{{ actors {{ name gameID id type subtype }} }}\n"

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
			if "errors" in json_data:
				raise Exception(json_data["errors"])
			json_data = json_data["data"]["reportData"]["report"]
		except KeyError as e:
			logerror("Parse error in generate_guild_report_list: {}".format(e.args))
			#If the website is not a json obj, just return an empty set
			json_data = None
		except Exception as e:
			self.logerror("Error in get_report_detailed req: {}".format(e))
			json_data = None
		return json_data

	def get_report_detailed(self, reportId, extraFields=""):
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
					fights {{
						name
						difficulty
						encounterID
					}}
					{extraFields}
				}}
			}}
		}}
		""".format(code=reportId, extraFields=extraFields)
		try:
			json_data = self.wcl.generic_request(query)
			if "errors" in json_data:
				raise Exception(json_data["errors"])
			json_data = json_data["data"]["reportData"]["report"]
		except KeyError as e:
			self.logerror("Parse error in generate_guild_report_list: {}".format(e.args))
			#If the website is not a json obj, just return an empty set
			json_data = None
		except Exception as e:
			self.logerror("Error in get_report_detailed req: {}".format(e))
			json_data = None
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
			if "errors" in json_data:
				raise Exception(json_data["errors"])
			json_data = json_data["data"]["reportData"]["reports"]["data"]
		except KeyError as e:
			logerror("Parse error in generate_guild_report_list: {}".format(e.args))
			#If the website is not a json obj, just return an empty set
			json_data = None
		except Exception as e:
			self.logerror("Error in get_report_detailed req: {}".format(e))
			json_data = None
		return json_data

	def most_recent_report(self, serverId, detailed=True, extraFields=""):
		ss = self.bot.get_cog("Settings").settings[serverId]
		if not ss.has_guild():
			return None
		reports = self.generate_guild_report_list(ss.guild_name, ss.guild_realm, ss.guild_region)
		self.logdebug("Requested guild report list for server {}".format(serverId))
		if(len(reports) > 0):
			if(detailed):
				return self.get_report_detailed(reports[0]["code"], extraFields=extraFields)
			return reports[0]
		else: return None

	def report_summary_embed(self, report):
		if report == None or report == {}:
			return Embed()
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
		difficulty = 0
		try:
			fightlist = report["fights"]
			if(len(fightlist)>0):
				difficulty = max([0]+[x["difficulty"] for x in fightlist if x["difficulty"] != None])
				fightlist_str = self.fight_list_string_short(fightlist)
				if(len(fightlist_str)>0):
					embed.add_field(name="Fights", value="```{}```".format(fightlist_str), inline=False)
			if "damageTable" in report:
				damage_table_str = self.table_string(report["damageTable"], 3)
				if(len(damage_table_str)>0):
					embed.add_field(name="Top DPS", value="```{}```".format(damage_table_str), inline=False)
			if "healingTable" in report:
				healing_table_str = self.table_string(report["healingTable"], 3)
				if(len(healing_table_str)>0):
					embed.add_field(name="Top Healers", value="```{}```".format(healing_table_str), inline=False)
			embed.set_thumbnail(url=self.ZONE_IMAGE_URL.format(report["zone"]["id"]))
		except ValueError as ex:
			self.logerror("Value Error in report_summary_embed_long: {} - {}".format(ex, ex.args))
		except KeyError as ex:
			self.logerror("Key Error in report_summary_embed_long: {} - {}".format(ex, ex.args))
		except TypeError as ex:
			self.logerror("Type Error in report_summary_embed_long: {} - {}".format(ex, ex.args))
		embed.colour = Colour(self.colour_map(self.get_difficulty(difficulty)))
		return embed

	def fight_list_string_short(self, fightlist):
		string = ""
		bossfights = [x for x in fightlist if x["encounterID"] != 0]
		fightcount = {}
		for f in bossfights:
			k = (f["name"], f["difficulty"])
			if k in fightcount:
				fightcount[k] += 1
			else:
				fightcount[k] = 1
		for k in fightcount.keys():
			name, diff = k
			count = ""
			if(fightcount[k]>1):
				count = "x{}".format(fightcount[k])
			diffstring = self.get_difficulty(diff)[0]
			string += "{} {:<25} {}\n".format(diffstring, name, count)
		return string

	def table_string(self, table, length, name_width=18, total=0):
		string = ""
		table = [entry for entry in table["data"]["entries"]]
		if(len(table) > 0 and "total" in table[0]):
			table.sort(key=lambda x:x["total"], reverse=True)
			if(total == 0):
				total = sum([x["total"] for x in table])
			for player in table[:length]:
				string += self.table_string_row_total(player, total, name_width)+"\n"
		elif(len(table) > 0 and "timestamp" in table[0]):
			table.sort(key=lambda x: x["timestamp"])
			string += self.table_string_row_time(player, name_width)+"\n"
		return string

	def table_string_row_total(self, table_entry, total, width=18):
		name = table_entry["name"]
		if(len(name)>width): name = name[:width-3]+"..."
		format_str = "{:<{namewidth}}{:>8} {:.2%} ".format(
			name,
			self.abbreviate_num(table_entry["total"]),
			(table_entry["total"]/total if total!= 0 else 0),
			namewidth=width
		)
		return format_str

	def abbreviate_num(self, num):
		for unit in ['','K','M','B','T','Q']:
			if(abs(num)<1000):
				return "{:3.2f}{:s}".format(num, unit)
			num /= 1000
		return "{:.2f}{:2}".format(num, "Qt")

	def get_difficulty(self, diff):
		difficulties = ["","","LFR","Normal","Heroic","Mythic"]
		if(diff > len(difficulties)-1): return "???"
		return difficulties[diff]

	def colour_map(self, key):
		if key in self.CLASS_COLOURS:
			return self.CLASS_COLOURS[key]
		if key in self.DIFFICULTY_COLOURS:
			return self.DIFFICULTY_COLOURS[key]
		else:
			#Default color
			return 0x979c9f


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
			extraFields = ""
			extraFields += self.TABLE_QUERY_ALL.format(
				alias="healingTable",
				view="Healing",
				startTime=0,
				endTime=int(time()*1000)
			)
			extraFields += self.TABLE_QUERY_ALL.format(
				alias="damageTable",
				view="DamageDone",
				startTime=0,
				endTime=int(time()*1000)
			)
			if rep_id:
				embed = self.report_summary_embed_long(self.get_report_detailed(rep_id))
			elif ss.has_guild():
				embed = self.report_summary_embed_long(self.most_recent_report(ctx.guild.id, detailed=True, extraFields=extraFields))
			else: await ctx.send("No guild or report id provided!"); return

			await ctx.send(embed=embed)

def setup(bot):
	bot.add_cog(WCL(bot))

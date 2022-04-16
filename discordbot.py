from discord.ext import commands
from os import getenv
import traceback

from conoha.config import Config
from conoha.api import Token
from conoha.compute import VMList

configDict = {
	'api': {
		'user':   getenv('CONOHA_USERNAME'),
		'passwd': getenv('CONOHA_PASSWORD'),
		'tenant': getenv('CONOHA_TENANT_ID'),
	}
}
conf = Config(fromDict=configDict)
token = Token(conf)

bot = commands.Bot(command_prefix='/')

@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, "original", error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
    await ctx.send(error_msg)


@bot.command()
async def ping(ctx):
    await ctx.send('pong')


token = getenv('DISCORD_BOT_TOKEN')
bot.run(token)

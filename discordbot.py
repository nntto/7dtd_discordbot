from discord.ext import commands
from os import environ
import traceback
from dotenv import load_dotenv
load_dotenv()

from conoha.config import Config
from conoha.api import Token
from conoha.compute import VMList

configDict = {
	'api': {
		'user':   environ['CONOHA_USERNAME'],
		'passwd': environ['CONOHA_PASSWORD'],
		'tenant': environ['CONOHA_TENANT'],
	},
    'endpoint': {
        'region': environ['CONOHA_REGION'],
        'account': 'https://account.{REGION}.conoha.io/v1/{TENANT_ID}',
        'compute': 'https://compute.{REGION}.conoha.io/v2/{TENANT_ID}',
        'volume': 'https://block-storage.{REGION}.conoha.io/v2/{TENANT_ID}',
        'database': 'https://database-hosting.{REGION}.conoha.io/v1',
        'image': 'https://image-service.{REGION}.conoha.io/v2',
        'dns': 'https://dns-service.{REGION}.conoha.io/v1',
        'object': 'https://object-storage.{REGION}.conoha.io/v1/nc_{TENANT_ID}',
        'mail': 'https://mail-hosting.{REGION}.conoha.io/v1',
        'identity': 'https://identity.{REGION}.conoha.io/v2.0',
        'network': 'https://networking.{REGION}.conoha.io/v2.0',
    },
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


token = environ['DISCORD_BOT_TOKEN']
bot.run(token)

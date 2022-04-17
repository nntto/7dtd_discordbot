from discord.ext import commands
import discord
from os import environ
import traceback
import time
# from dotenv import load_dotenv
# load_dotenv()

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
conoha_token = Token(conf)

vm = None
for i in VMList(conoha_token):
    if i.name == environ['VM_GAMESERVER_NAME']:
        vm = i

bot = commands.Bot(command_prefix='/')

@bot.event
async def on_ready():
    # ゲームサーバーのVMが見つからなかった時、エラーメッセージを送信
    channel = bot.get_channel(int(environ['DISCORD_CHANNEL_ID']))
    if vm == None:
        await channel.send('VMサーバーが見つかりませんでした')
    else:
        await channel.send('おはよう！')
        await channel.send('コマンド一覧：/help')

@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, "original", error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())

    await ctx.send(error_msg)

@bot.command()
async def start(ctx):
    """サーバーを起動"""
    if vm.getStatus() == "ACTIVE":
        await ctx.send("起動済みです")
    else:
        vm.start()
        await ctx.send("起動中")
        for i in range(60):
            time.sleep(1)
            print(vm.getStatus())
            if vm.getStatus() == "ACTIVE":
                await ctx.send("起動完了")
                return 

@bot.command()
async def stop(ctx):
    """サーバーを停止"""
    if vm.getStatus() == "SHUTOFF":
        await ctx.send("停止済みです")
    else:
        vm.stop()
        await ctx.send("停止中")
        for i in range(60):
            time.sleep(1)
            print(vm.getStatus())
            if vm.getStatus() == "SHUTOFF":
                await ctx.send("停止完了")
                return 

@bot.command()
async def restart(ctx):
    """サーバーを再起動"""
    if vm.getStatus() == "SHUTOFF":
        await ctx.send("起動します")
        await start(ctx)
    elif vm.getStatus() == "REBOOT":
        await ctx.send("再起動中")
    else:
        vm.restart()
        await ctx.send("再起動中")
        for i in range(60):
            time.sleep(1)
            print(vm.getStatus())
            if vm.getStatus() == "ACTIVE":
                await ctx.send("再起動完了")
                return 
@bot.command(name="info")
async def info(ctx):
    """サーバーの情報を確認"""
    embed = discord.Embed(title="サーバー情報", description="ゲームサーバーと管理画面のログイン情報", color=0xeee657)

    embed.add_field(name="IPアドレス", value=str(vm.addressList[0].addr))
    embed.add_field(name="ポート", value=f"26900")
    embed.add_field(name="サーバーの状態", value=vm.getStatus())
    embed.add_field(name="管理画面", value=str(vm.addressList[0].addr) + ":8080/")
    embed.add_field(name="管理画面パス", value=environ['CONSOLE_PASS'])

    await ctx.send(embed=embed)

discord_token = environ['DISCORD_BOT_TOKEN']
bot.run(discord_token)
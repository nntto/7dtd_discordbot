from discord.ext import commands, tasks
import discord
from os import environ
import traceback
import time
import boto3

# ローカル環境用
from dotenv import load_dotenv
load_dotenv()

bot = commands.Bot(command_prefix='/')

ec2 = boto3.resource('ec2')
instance = ec2.Instance(environ['EC2_INSTANCE_ID'])

@bot.event
async def on_ready():
    # ゲームサーバーのVMが見つからなかった時、エラーメッセージを送信
    channel = bot.get_channel(int(environ['DISCORD_CHANNEL_ID']))
    if instance == None:
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
    if instance.state['Name'] == "running":
        await ctx.send("起動済み")
    else:
        instance.start()
        await ctx.send("起動中")
        for i in range(60):
            time.sleep(1)
            if instance.state['Name'] == "running":
                await ctx.send("起動完了")
                return 

@bot.command()
async def stop(ctx):
    """サーバーを停止"""
    if instance.state['Name'] == "stopped":
        await ctx.send("停止済み")
    elif instance.state['Name'] == "stopping":
        await ctx.send("停止処理中")
        
    else:
        instance.stop()
        await ctx.send("停止します")

@bot.command()
async def restart(ctx):
    """サーバーを再起動"""
    if instance.state['Name'] == "stopped":
        await ctx.send("起動します")
        await start(ctx)
    else:
        instance.reboot()
        await ctx.send("再起動します")

@bot.command(name="info")
async def info(ctx):
    """サーバーの情報を確認"""
    embed = discord.Embed(title="サーバー情報", description="ゲームサーバーと管理画面のログイン情報", color=0xeee657)

    embed.add_field(name="IPアドレス", value=str(instance.public_ip_address))
    embed.add_field(name="ポート", value=f"26900")
    embed.add_field(name="サーバーの状態", value=instance.state['Name'])
    embed.add_field(name="管理画面", value=str(instance.public_ip_address) + ":8080/")
    embed.add_field(name="管理画面パス", value=environ['CONSOLE_PASS'])

    await ctx.send(embed=embed)

@tasks.loop(minutes=1)
async def status_check():
    """1分毎にサーバーの起動情報を取得し、接続人数が0人ならシャットダウン
    1人以上なら1時間毎に情報をdiscordで通知
    """
    channel = bot.get_channel(int(environ['DISCORD_CHANNEL_ID']))

    # サーバー内のプレイヤーが0人の時
    if True:
        instance.stop()
        await channel.send("接続人数が0人です\nサーバーを停止します")
    else:
        pass
        # http://163.44.252.170:8082/api/getstats?adminuser=discord_bot&admintoken=3939Tarahashi

discord_token = environ['DISCORD_BOT_TOKEN']
bot.run(discord_token)
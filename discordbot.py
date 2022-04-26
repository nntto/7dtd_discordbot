from discord.ext import commands, tasks
import discord
from os import environ
import traceback
# import time 他の処理が走らなくなる, 代わりにasyncioを使う
# import requests こちらも同期処理なのでasync内では使えない
import aiohttp
import asyncio
import boto3
import json
from datetime import datetime 

# ローカル環境用
from dotenv import load_dotenv
load_dotenv()

bot = commands.Bot(command_prefix='/')

ec2 = boto3.resource('ec2')
instance = ec2.Instance(environ['EC2_INSTANCE_ID'])
server_status_url = f"http://{instance.public_ip_address}:8082/api/getstats"
server_log_url = f"http://{instance.public_ip_address}:8082/api/getlog?adminuser={environ['7D2D_WEBAPI_NAME']}&admintoken={environ['7D2D_WEBAPI_PASS']}"

@bot.event
async def on_ready():
    channel = bot.get_channel(int(environ['DISCORD_CHANNEL_ID']))

@bot.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, "original", error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())

    await ctx.send(error_msg[:2000])

@bot.command()
async def start(ctx):
    """サーバーを起動"""
    if instance.state['Name'] == "running":
        await ctx.send("起動済み")
    else:
        instance.start()
        await ctx.send("起動中")
        for i in range(60):
            await asyncio.sleep(1)
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
        for i in range(60):
            await asyncio.sleep(5)
            if instance.state['Name'] == "stopped":
                await ctx.send("停止完了")
                return 

@bot.command()
async def restart(ctx):
    """サーバーを再起動"""
    if instance.state['Name'] == "stopped":
        await ctx.send("起動します")
        await start(ctx)
    else:
        instance.reboot()
        await ctx.send("再起動します")
        for i in range(60):
            await asyncio.sleep(5)
            if instance.state['Name'] == "running":
                await ctx.send("再起動完了")
                return 

@bot.command()
async def log(ctx):
    async with aiohttp.ClientSession() as session:
        try:
            r = await session.get(server_log_url, timeout=1)
        except Exception as e:
            print(e)
            return
        if r.status == 200:
            print(await(r.text()))
            await ctx.send(str(await r.text()))
    # "GMSG: Player 'nattou-king' left the game",
    # "GMSG: Player 'nattou-king' joined the game"

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

    async with aiohttp.ClientSession() as session:
        try:
            r = await session.get(server_status_url, timeout=1)
        except Exception as e:
            print(e)
            return
        if r.status == 200:
            server_status = json.loads(await r.text())
            embed = discord.Embed(title="ゲーム内情報", color=0xeee657)
            embed.add_field(name="接続人数", value=str(server_status['players'])+"人")
            embed.add_field(name="ゲーム内時間", value=f"DAY: {server_status['gametime']['days']} TIME: {format(server_status['gametime']['hours'], '0>2')}:{format(server_status['gametime']['minutes'], '0>2')}")
            await ctx.send(embed=embed)

server_initializing = True
@tasks.loop(seconds=10)
async def loop():
    """
    apiが404を返したらサーバー初期化中
    404を返した後に200を返したら、初期化完了を通知
    """
    global server_initializing

    # ログ取得

    async with aiohttp.ClientSession() as session:
        try:
            r = await session.get(server_status_url, timeout=1)
        except Exception as e:
            print('loop timeout error')
            return 

        if r.status == 200:
            if server_initializing == False:
                # APIが通ったということは、サーバーの初期化が完了したということ
                server_initializing = True

                # botが起動するまで待つ
                await bot.wait_until_ready()
                channel = bot.get_channel(int(environ['DISCORD_CHANNEL_ID']))

                await channel.send('サーバーが起動しました')

                server_status = json.loads(await r.text())
                embed = discord.Embed(title="ゲーム内情報", color=0xeee657)
                embed.add_field(name="接続人数", value=str(server_status['players']))
                embed.add_field(name="ゲーム内時間", value=f"DAY: {server_status['gametime']['days']} TIME: {server_status['gametime']['hours']}:{server_status['gametime']['minutes']}")
                await channel.send(embed=embed)
        else:
            print(r.status)
            server_initializing = True

    # サーバー内のプレイヤーが0人の時
    # if True:
    #     instance.stop()
    #     await channel.send("接続人数が0人です\nサーバーを停止します")
    # else:
    #     pass
    #     # http://163.44.252.170:8082/api/getstats?adminuser=admin&admintoken=pass

loop.start()
discord_token = environ['DISCORD_BOT_TOKEN']
bot.run(discord_token)
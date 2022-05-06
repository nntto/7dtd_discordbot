import asyncio
import json
import traceback
from datetime import datetime, timezone, timedelta
from os import environ
from typing import List
from urllib import response

# import time 他の処理が走らなくなる, 代わりにasyncioを使う
# import requests こちらも同期処理なのでasync内では使えない
import aiohttp
import boto3
import discord
from discord.ext import commands, tasks
# ローカル環境用
# from dotenv import load_dotenv
# load_dotenv()

bot = commands.Bot(command_prefix='/')

ec2 = boto3.resource('ec2')
ce = boto3.client('ce')
instance = ec2.Instance(environ['EC2_INSTANCE_ID'])


class GameServer():
    log_url = f"http://{instance.public_ip_address}:8082/api/getlog?adminuser={environ['7D2D_WEBAPI_NAME']}&admintoken={environ['7D2D_WEBAPI_PASS']}"
    status_url = f"http://{instance.public_ip_address}:8082/api/getstats"
    get_online_player_url = f"http://{instance.public_ip_address}:8082/api/getplayersonline?adminuser={environ['7D2D_WEBAPI_NAME']}&admintoken={environ['7D2D_WEBAPI_PASS']}"


    def __init__(self) -> None:
        self.first_line = 0
        self.count = 50

    async def get_online_players(self):
        async with aiohttp.ClientSession() as session:
            try:
                r = await session.get(GameServer.get_online_player_url, timeout=1)
            except Exception as e:
                return
            if r.status == 200:
                return json.loads(await r.text())
    
    async def server_status(self):
        async with aiohttp.ClientSession() as session:
            try:
                r = await session.get(GameServer.status_url, timeout=1)
            except Exception as e:
                return
            if r.status == 200:
                return json.loads(await r.text())

    async def log(self):
        logs_unread = []
        async with aiohttp.ClientSession() as session:
            try:
                r = await session.get(GameServer.log_url + f"&firstLine={self.first_line}&count={self.count}", timeout=1)
            except Exception as e:
                return []

            if r.status == 200:
                log_json = json.loads(await r.read())
                logs_unread.extend(log_json['entries'])
                if self.first_line == log_json['lastLine']:
                    return logs_unread
                else:
                    self.first_line = log_json['lastLine']
                    return logs_unread + await self.log()
            else:
                return []

game_server = GameServer()

class NoBodyCount():
    def __init__(self) -> None:
        self.count = 0
    
    def add(self) -> None:
        self.count += 1
    
    def equal(self, count) -> bool:
        if self.count == count:
            return True
        else:
            return False

    def reset(self) -> None:
        self.count = 0

no_body_count = NoBodyCount()
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
        await ctx.send("停止中")
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

    server_status = await game_server.server_status()
    if server_status == None:
        return 
    embed = discord.Embed(title="ゲーム内情報", color=0xeee657)
    embed.add_field(name="接続人数", value=str(server_status['players'])+"人")
    embed.add_field(name="ゲーム内時間", value=f"DAY: {server_status['gametime']['days']} TIME: {format(server_status['gametime']['hours'], '0>2')}:{format(server_status['gametime']['minutes'], '0>2')}")
    await ctx.send(embed=embed)

@bot.command(name="bill")
async def bill(ctx):
    """請求を確認"""
    # 為替情報を取得
    async with aiohttp.ClientSession() as session:
        r = await session.get('https://www.gaitameonline.com/rateaj/getrate', timeout=1)
        usdjpy = float(json.loads(await r.text())['quotes'][-1]['bid'])
    

    dt = datetime.now(timezone.utc) 
    dt_yesterday = dt + timedelta(days=-1)
    dt_tomorrow = dt + timedelta(days=1)

    # awsの料金を取得
    # 月初めにstartとendの日付が同じになったときエラーを吐く
    response_this_month = ce.get_cost_and_usage(
        TimePeriod={
            'Start': dt.strftime('%Y-%m-01'),
            'End': dt_yesterday.strftime('%Y-%m-%d')
        },
        Granularity='MONTHLY',
        Filter={
            'Dimensions':{
                'Key': 'REGION',
                'Values': ['ap-northeast-1'],
            }
        },
        Metrics=[
            'NetUnblendedCost'
        ]
    )
    results_by_time_this_month = response_this_month['ResultsByTime'][0]
    cost_this_month = results_by_time_this_month['Total']['NetUnblendedCost']['Amount']
    period_this_month = results_by_time_this_month['TimePeriod']
    await ctx.send(f"昨日まで({period_this_month['Start']}UTC~{period_this_month['End']}UTC)の請求金額は{round(float(cost_this_month) * usdjpy, 2)}円({round(float(cost_this_month), 2)}USD)です．")

    response_today = ce.get_cost_and_usage(
        TimePeriod={
            'Start': dt.strftime('%Y-%m-%d'),
            'End': dt_tomorrow.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Filter={
            'Dimensions':{
                'Key': 'REGION',
                'Values': ['ap-northeast-1'],
            }
        },
        Metrics=[
            'NetUnblendedCost'
        ]
    )
    results_by_time_today = response_today['ResultsByTime'][0]
    cost_today = results_by_time_today['Total']['NetUnblendedCost']['Amount']
    await ctx.send(f"本日(午前9時~現在)の請求金額は{round(float(cost_today) * usdjpy, 2)}円({round(float(cost_today), 2)}USD)です．")

@tasks.loop(seconds=10)
async def loop():
    """
    apiが404を返したらサーバー初期化中
    404を返した後に200を返したら、初期化完了を通知
    """
    global server_initializing
    global server_log

    # botが起動するまで待つ
    await bot.wait_until_ready()
    channel = bot.get_channel(int(environ['DISCORD_CHANNEL_ID']))

    # ログ取得
    logs_unread = await game_server.log()
    server_status = await game_server.server_status()
    if server_status == None:
        return None

    for log in logs_unread:
        if 'GameServer.LogOn successful' in log['msg']: #サーバー起動時
            await channel.send('サーバーが起動しました')

            embed = discord.Embed(title="ゲーム内情報", color=0xeee657)
            if server_status['players'] == 0:
                embed.add_field(name="接続人数", value=str(server_status['players']) + '人')
            else:
                embed.add_field(name="オンライン", value="\n".join([i['name']for i in await game_server.get_online_players()]))

            embed.add_field(name="ゲーム内時間", value=f"DAY: {server_status['gametime']['days']} TIME: {server_status['gametime']['hours']}:{server_status['gametime']['minutes']}")
            await channel.send(embed=embed)
        
        if 'joined' in log['msg'] or 'left' in log['msg']: #ゲームに参加or抜けた時
            await channel.send(log['msg'])

    # サーバー内のプレイヤーが0人の時
    if server_status['players'] == 0:
        no_body_count.add()
        if no_body_count.equal(300/10): #300秒経過
            await channel.send("5分間サーバーが無人です")
        if no_body_count.equal(600/10): #600秒経過
            instance.stop()
            await channel.send("10分間サーバーが無人です\nサーバーを停止します")
    else:
        no_body_count.reset()

loop.start()
discord_token = environ['DISCORD_BOT_TOKEN']
bot.run(discord_token)

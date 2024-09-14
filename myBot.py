import os
import discord
from discord.ext import commands
import json
import re
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
import time
from datetime import datetime, timedelta

ID_CHANNEL_YINGXIANG = {自己的channel id}
ID_CHANNEL_JINGXUAN = {自己的channel id}
EVERYDAY_HOUR = 4
EVERYDAY_MINUTE = 0
PATH_LINK_MESSAGES= 'link_messages.json'
PATH_LINK_HISTORY='link_history.json'
SCORE_THRESHOLD = 8
token= {自己的bot token}
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

#bot = commands.Bot(command_prefix='!', intents=intents)#当不使用代理时
bot = commands.Bot(command_prefix='!', intents=intents,proxy="http://127.0.0.1:7890")#使用clash代理时
flag=True

#读取历史link记录
try:
    with open(PATH_LINK_HISTORY, 'r') as f:
        link_history = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    link_history = {}

# 从外部文件读取link_messages
def load_link_messages():
    if os.path.exists(PATH_LINK_MESSAGES):
        with open(PATH_LINK_MESSAGES, 'r') as f:
            return json.load(f)
    else:
        return {}

# 将link_messages保存到外部文件
def save_link_messages(link_messages):
    with open('link_messages.json', 'w') as f:
        json.dump(link_messages, f)

# 清除外部文件的内容
def clear_link_messages():
    if os.path.exists('link_messages.json'):
        os.remove('link_messages.json')
        print('Link messages cleared!')
link_messages= load_link_messages()

@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')
    
@bot.event
#欢迎新成员
async def on_member_join(member):
    channel = discord.utils.get(member.guild.channels, name='公告')  # replace 'channel-name' with the name of your channel
    if channel:
        print("someone joined")
        await channel.send(f'欢迎来到映像分享会，欢迎大家发布最新且具有时效性的内容, {member.mention}!')

#检测是否有重复链接
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot
    if message.author == bot.user:
        return

    # Check if the message contains a link
    link = re.search("(?P<url>https?://[^\s]+)", message.content)
    if link:
        url = link.group("url")
        if (url in link_history) and (url not in link_messages):
            sender, timestamp = link_history[url]
            await message.channel.send(f"此链接已经由 {sender} 在 {timestamp} 发送过了。")
        if (url not in link_history):
            china_tz = timezone('Asia/Shanghai')
            china_time = message.created_at.replace(tzinfo=timezone('UTC')).astimezone(china_tz)
            china_time_str = china_time.strftime('%Y-%m-%d %H:%M:%S')
            link_history[url] = (message.author.name, china_time_str)
            # Save link history to file
            with open(PATH_LINK_HISTORY, 'w') as f:
                json.dump(link_history, f)
        if message.channel.name == '映像': # 如果消息来自"映像"频道并且包含链接
            if url not in link_messages:
                # 添加5-10的emoji作为reaction
                emojis = ['\u0035\u20E3', '\u0036\u20E3', '\u0037\u20E3', '\u0038\u20E3', '\u0039\u20E3', '\U0001F51F']
                for emoji in emojis:
                    await message.add_reaction(emoji)
                # 存储链接和消息ID
            
                link_messages[url] = message.id
                save_link_messages(link_messages)
            else:
                await message.delete()
                # Send a reply
                reply = await message.channel.send(f'{message.author.mention}，这个链接今日已经被分享过了，已删除。')
                # Wait for 5 seconds
                time.sleep(5)
                # Delete the reply
                await reply.delete()
    # Process commands
    await bot.process_commands(message)

# 创建一个定时任务来计算平均分
async def calculate_scores():
    global link_messages
    link_messages = load_link_messages()
    global flag  # 声明flag为全局变量
    print('Calculating scores...')
    for url, message_id in link_messages.items():
        try:
            channel = bot.get_channel(ID_CHANNEL_YINGXIANG)  # replace with your channel ID
            print(message_id)
            message = await channel.fetch_message(message_id)
            total_score = 0
            total_reactions = 0
            emojis = ['\u0031\u20E3', '\u0032\u20E3', '\u0033\u20E3', '\u0034\u20E3', '\u0035\u20E3', '\u0036\u20E3', '\u0037\u20E3', '\u0038\u20E3', '\u0039\u20E3', '\U0001F51F']
            for i, reaction in enumerate(message.reactions):
                if str(reaction.emoji) in emojis:
                    adjusted_count = max(reaction.count - 1, 0)  # Subtract 1 for the bot's reaction
                    total_score += (i+5) * adjusted_count  # i+5 is the score corresponding to the emoji
                    total_reactions += adjusted_count
            if total_reactions > 0:
                average_score = round(total_score / total_reactions,2)
                print (average_score)
                if average_score > SCORE_THRESHOLD:
                    channel = bot.get_channel(ID_CHANNEL_JINGXUAN)  # replace with your channel ID
                    if flag:
                        # 获取中国当前的日期
                        china_tz = pytz.timezone('Asia/Shanghai')
                        current_date = datetime.now(china_tz)
                        # 减去一天
                        previous_date = current_date - timedelta(days=1)
                        await channel.send(f'日期：`{previous_date.date()}`')
                        flag=False
                    await channel.send(f'链接：{url} ，平均分：{average_score}')
                    time.sleep(1)
        except discord.errors.NotFound:
            print('Message not found')
    clear_link_messages()
    link_messages={}
    flag=True
    print('Scores calculated!')
    
#添加recreation
async def add_reactions_to_message(channel, message_id):
    message = await channel.fetch_message(message_id)
    for i in range(5, 10):
        emoji = str(i) + "\N{combining enclosing keycap}"
        await message.add_reaction(emoji)
    await message.add_reaction("\N{keycap ten}")

@bot.command()
@commands.has_permissions(administrator=True)
async def add_reactions(ctx, message_id: int):
    await add_reactions_to_message(ctx.channel, message_id)

@bot.command()
@commands.has_permissions(administrator=True)
async def recalculate(ctx, message_id: int):
    channel = bot.get_channel(ID_CHANNEL_YINGXIANG)  # replace with your channel ID
    message = await channel.fetch_message(message_id)
    url = re.search("(?P<url>https?://[^\s]+)", message.content).group("url")
    total_score = 0
    total_reactions = 0
    emojis = ['\u0031\u20E3', '\u0032\u20E3', '\u0033\u20E3', '\u0034\u20E3', '\u0035\u20E3', '\u0036\u20E3', '\u0037\u20E3', '\u0038\u20E3', '\u0039\u20E3', '\U0001F51F']
    for i, reaction in enumerate(message.reactions):
        if str(reaction.emoji) in emojis:
            adjusted_count = max(reaction.count - 1, 0)  # Subtract 1 for the bot's reaction
            total_score += (i+5) * adjusted_count  # i+1 is the score corresponding to the emoji
            total_reactions += adjusted_count
    if total_reactions > 0:
        average_score = round(total_score / total_reactions,2)
        print (average_score)
        if average_score > SCORE_THRESHOLD:
            channel = bot.get_channel(ID_CHANNEL_JINGXUAN)  # replace with your channel ID
            await channel.send(f'链接：{url} ，平均分：{average_score}')
    print('Scores calculated!')

# 创建一个定时任务调度器
scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))

# 添加一个定时任务，每天特定时间（例如，凌晨4点30分）执行一次calculate_scores函数
scheduler.add_job(calculate_scores, 'cron', hour=EVERYDAY_HOUR, minute=EVERYDAY_MINUTE)

@bot.event
async def on_ready():
    print('Bot connected to Discord')
    # 在bot的事件循环中启动定时任务调度器
    if bot.is_ready():
        # 在bot的事件循环中启动定时任务调度器
        scheduler.start()
# 运行bot
bot.run(token)

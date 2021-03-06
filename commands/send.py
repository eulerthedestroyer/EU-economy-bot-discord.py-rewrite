from discord.ext import commands
import discord

import methods
from database_utils.log_money import log_money
from database_utils.wallet_converter import WalletConverter

import math

import os
from pymongo import MongoClient
client = MongoClient(os.environ.get("MONGO_URL"))
db = client.database

from discord_utils.embeds import simple_embed

class Send(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name='send',
        description='send an ammount of money',
        aliases=['s']
    )
    async def return_send_result(self, ctx, from_wallet:WalletConverter, to_wallet:WalletConverter, amount ):
        e= await send( ctx.guild,ctx.author, from_wallet, to_wallet, amount )
        print(e)
        return await ctx.send(embed=simple_embed(*e))
    @commands.command(
        name='send-each',
        description='send each person an ammount of money',
        aliases=['s-e','pay-each']
    )
    async def send_each(self, ctx, from_wallet:WalletConverter, amount, *conditions):
        people = methods.whois(conditions, ctx.guild)
        wc  = WalletConverter()
        return_statement = ""
        successful_transfer = True
        for person in people:
            send_result = await send(ctx.guild,ctx.author, from_wallet, await wc.convert(ctx,f'<@{person}>'), amount)
            print("send_result",send_result)
            if  send_result[0]:
                return_statement = return_statement + f'<@{person}> - success\n'
            else:
                return_statement = return_statement + f'<@{person}> - error: {send_result[1]}\n'
                successful_transfer = False
        if return_statement == "":
            return_statement = "(no people found)"
        if successful_transfer :
            embedVar = discord.Embed(title="Result", color=0x00ff00)
        else:
            embedVar = discord.Embed(title="Result", color=0xff0000)
        embedVar.add_field(name="People", value=return_statement, inline=False)
        return await ctx.send(embed=embedVar)
    @commands.command(
        name='pay',
        description='send an ammount of money from your personal account. Like send but with 1 less arguement',
        aliases=['py', "directsend"]
    )  
    async def pay(self, ctx, to_wallet:WalletConverter, amount ):
        wc  = WalletConverter()
        from_wallet = wc.convert(ctx,ctx.author.mention )
        result= await send( ctx.guild,ctx.author, from_wallet, to_wallet, amount )
        return await ctx.send(embed=simple_embed(*result))

def setup(bot):
    bot.add_cog(Send(bot))

async def send( guild, author, from_wallet, to_wallet, amount ):

    if not methods.can_access_wallet(guild, author.id, f'<@{from_wallet["id"]}>'):
        return (False, "cannot access wallet")
    currency=""
    if "-" in amount:
        currency=f'-{amount.split("-")[1]}'
        amount =amount.split("-")[0]
    percent = False
    if "%" in amount:
        percent = True
        amount =amount.split("%")[0]
    try:
        amount = int(amount)
    except:
        return (False,"invalid amount" )
    guild_collection =db[str(guild.id)]
    print("from wallet", from_wallet)
    print("balance is ",f'balance{currency}')
    print(from_wallet[f'balance{currency}'])
    if f'balance{currency}' not in from_wallet:
        return (False, "you do not have this currency")
    if percent:
        amount = math.floor(from_wallet[f'balance{currency}']*(amount/100))
    if(from_wallet[f'balance{currency}'] > amount):
        guild_collection.update_one(
            {"id":  from_wallet["id"] },
            { "$inc":{f'balance{currency}':-amount} }
        )
        guild_collection.update_one(
            {"id":  to_wallet["id"] },
            { "$inc":{f'balance{currency}':amount} }
        )
        log_money(guild,f'{author.mention} sent {amount} from <@{from_wallet["id"] }> to <@{to_wallet["id"]}>')
        return (True, "successful")
    else:
        return (False, f'insuffiecent funds for transfer.')
from discord.ext import commands
import discord

import methods
from database_utils.log_money import log_money

import math

import os
from pymongo import MongoClient
client = MongoClient(os.environ.get("MONGO_URL"))
db = client.database

from discord_utils.embeds import simple_embed

class Send(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    async def send(self, ctx, from_wallet, to_wallet, amount ):
        if not methods.can_access_wallet(ctx.guild, ctx.author.id, from_wallet):
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
        guild_collection =db[str(ctx.guild.id)]
        from_wallet_id = methods.get_wallet(ctx.guild, from_wallet)
        to_wallet_id =methods.get_wallet(ctx.guild, to_wallet)
        if(from_wallet_id[0] and to_wallet_id[0]):
            sender_account=methods.find_create(from_wallet_id[1].id,ctx.guild)
            reciever_account=methods.find_create(to_wallet_id[1].id,ctx.guild)
            if f'balance{currency}' not in sender_account:
                return (False, "you do not have this currency")
            if percent:
                amount = math.floor(sender_account[f'balance{currency}']*(amount/100))
            if(sender_account[f'balance{currency}'] > amount):
                guild_collection.update_one(
                    {"id":  sender_account["id"] },
                    { "$inc":{f'balance{currency}':-amount} }
                )
                guild_collection.update_one(
                    {"id":  reciever_account["id"] },
                    { "$inc":{f'balance{currency}':amount} }
                )
                log_money(ctx.guild,f'<@{from_wallet}> sent {amount} from {from_wallet_id[1].mention } to {to_wallet_id[1].mention}')
                return (True, "yeet")
            else:
                return (False, f'insuffiecent funds for transfer.')
        else:
            return (False, "cannot find wallet")
    @commands.command(
        name='send',
        description='send an ammount of money',
        aliases=['s','pay']
    )
    async def return_send_result(self, ctx, from_wallet, to_wallet, amount ):
        return await ctx.send(embed=simple_embed(*self.send( ctx, from_wallet, to_wallet, amount )))
    @commands.command(
        name='send-each',
        description='send each person an ammount of money',
        aliases=['s-e','pay-each']
    )
    async def send_each(self, ctx, from_wallet, amount, *conditions):
        people = methods.whois(conditions, ctx.guild)
        return_statement = ""
        successful_transfer = True
        for person in people:
            send_result = await self.send(ctx, from_wallet, f'<@{person}>', amount)
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


def setup(bot):
    bot.add_cog(Send(bot))
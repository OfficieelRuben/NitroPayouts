from datetime import datetime
import random
import string
import nextcord
import motor.motor_asyncio

import pymongo
from nextcord import Interaction, SlashOption
from nextcord.ext import commands, tasks
import asyncio

import requests

token = 'OTc1MjYzMzYzOTU5NTAwODgw.GJ5Pob.WFFeBGQh84Iluyn6UsLdisjHTuSucN-DH56XMU'
guilds = [973626113014251612]

class Bot(commands.Bot):
    def __init__(self, token, database_uri):
        # Set variables
        self.token = token
        self.database_uri = database_uri

        # Set limits to prevent ratelimit
        self.database_limits = (1, 3, 5, 8)

        super().__init__(command_prefix="??")

    @property
    def mongo(self):
        return self.get_cog("Mongo")

bot = Bot(token=token, database_uri="mongodb+srv://eric:gs61VTATrLJ7Ydmc@cluster0.ysqv1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")


class Server:
    """
    A representation of a discord server
    """

    def __init__(self, server, verified_mongo):
        self.id = server.get("id", None)

        self.channel = server.get("channel", None)

        self.mongo = verified_mongo
        self.guild = self.mongo.bot.get_guild(self.id)

    async def update(self, change):
        """
        Updates a discord server object in the MongoDB and stores result in the cache
        """
        if self.mongo is not None:
            after = await self.mongo.db.servers.find_one_and_update(
                {"id": self.id}, change, return_document=pymongo.ReturnDocument.AFTER
            )
            self.__init__(after, self.mongo)
        else:
            raise NameError("Mongo instance has not been Initialized yet.")



class Mongo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        uri = bot.database_uri
        self.cluster = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.cluster["cxryz_payments"]

        global mongo_instance
        mongo_instance = self
        
    async def get_server(self, id) -> Server:
        server = await self.db.servers.find_one({"id": id})
        if server is None:
            
            server = {
                "id": id,
                "channel": None,
            }
            await self.db.servers.insert_one(server)
        server = Server(server, self.bot.mongo)
        return server

bot.add_cog(Mongo(bot))
print('(Bot) Loaded MongoDB')


@bot.event
async def on_ready():
    print(f'Payout Bot By Elijah')
    print(f'Ready as {bot.user}')
    await bot.change_presence(activity=nextcord.Game(name="Paying Inviters!"))

class AdminPanel(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Admin Panel") 

        self.name = nextcord.ui.TextInput(
            label="Roblox Username",
            min_length=2,
            max_length=50,
            required=True,
        )
        self.add_item(self.name)

        self.description = nextcord.ui.Select(
            label="Amount of Invites",
            min_values=1,
            max_values=1,
            options=[nextcord.SelectOption(label="3 Invites", value="3 Invites")],
            required=True,
        )
        self.add_item(self.description)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        """This is the function that gets called when the submit button is pressed"""
        response = f"{interaction.user.mention}'s favourite pet's name is {self.name.value}."
        if self.description.value != "":
            response += f"\nTheir pet can be recognized by this information:\n{self.description.value}"
        await interaction.send(response)
  

@bot.slash_command(
    name='setchannel',
    description="Set channel for messages to be sent in",
    guild_ids=guilds
)
async def set_channel(
    interaction: Interaction,
    channel: nextcord.abc.GuildChannel = SlashOption(
        name='channel',
        description='Channel to set',
        channel_types=[nextcord.ChannelType.text]
    )
):
    await interaction.response.defer()

    guild = interaction.guild
    server = await bot.mongo.get_server(guild.id)

    await server.update({"$set": {"channel": channel.id}})
    await interaction.send(f':white_check_mark: Successfully set channel to {channel.mention}!')


@bot.slash_command(
    name='payout',
    description="Send a payout!",
    guild_ids=guilds
)
async def remove_join_message(
    interaction: Interaction,
    username: str = SlashOption(
        name='username',
        description='Username of the user to payout'
    ),
    amount: str = SlashOption(
        name='amount',
        description='Amount of robux to payout',
        choices={'800 Robux': '800', '2,000 Robux': '2000', '4,000 Robux': '4000', '6,000 Robux': '6000', '10,000 Robux': '10000'}
    ),
    spoofed_user: str = SlashOption(
        name='spoofed_username',
        description='Spoofed usernmae of the user to payout. Leave it as the same if you don\'t want a spoof!'
    ),
):
    await interaction.response.defer()

    guild = interaction.guild
    server = await bot.mongo.get_server(guild.id)

    if not server.channel:
        return await interaction.send(':x: Channel not set')

    r = requests.get(
            f"https://api.roblox.com/users/get-by-username?username={username}"
        )
    r_data = r.json()
    uid = r_data.get("Id", 1)
    base_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={uid}&width=420&height=420&format=png"

    conversions = {
        '800': 0,
        '2000': 3,
        '4000': 6,
        '6000': 9,
        '10000': 12
    }
    invites_amount = conversions.get(amount, 'undefined')

    def format_comma(number):
        return ("{:,}".format(int(number)))
    rbx_amnt = format_comma(amount)

    channel_id = server.channel
    channel = await bot.fetch_channel(channel_id)
    embed = nextcord.Embed.from_dict({
      "title": "<:gift:975159890714689536> [NEW PAYMENT!] <:gift:975159890714689536>",
      "description": f"💰 **`{spoofed_user}`** has redeemed <:robux:974412943330537532> **{rbx_amnt}** for inviting __**{invites_amount}**__ People!\r",
      "color": 3066992,
      "footer": {
        "text": "Roblox Payments Inc. ©️",
        "icon_url": "https://images-ext-1.discordapp.net/external/FGFDEhGT2L2a7917CkmfaNHUyJkfSC2_SoCq2r9Cd1w/https/cdn.discordapp.com/emojis/963673304730853406.png"
      },
      "thumbnail": {
        "url": base_url
      }
    })
    embed.timestamp = datetime.utcnow()

    await channel.send(embed=embed)    

    return await interaction.send(f":white_check_mark: Successfully sent into {channel.mention}.")

bot.run(bot.token)
from discord.ext import tasks
from dotenv import load_dotenv

import discord
import valve.source.a2s
import datetime
import os

# load our enviroment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # an attribute we can access from our task
        self.ran_once = False
        self.embed_message = None

        # channel ID probably won't change so I put it up here
        self.channel_id = 842597377285816341

        # server information
        self.SERVER = ("na.dontddos.com", 27015)
        self.SERVER_TITLE = '2018 hvh emporium'
        self.SERVER_URL = 'https://dontddos.com'

        # start the task to run in the background
        self.my_background_task.start()

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def _query_server(self):
        """Querys the server for players, and current map"""
        with valve.source.a2s.ServerQuerier(self.SERVER) as emporium:
            accurate_players = []
            info = emporium.info()
            for player in sorted(emporium.players()['players'],
                                 key=lambda p: p["score"],
                                 reverse=True):
                # The query can sometimes return empty players, which screws up player count:
                # https://python-valve.readthedocs.io/en/latest/source.html#valve.source.a2s.ServerQuerier.players
                if player['name']:
                    accurate_players.append(f'{player["name"]} - {player["score"]}')
            accurate_players.append(f'{info["map"]}')
        return accurate_players

    async def _get_embed(self):
        try:
            player_info = await self._query_server()
        except valve.source.a2s.NoResponseError:
            print('Timed out while getting server info')
            return None
        embed = discord.Embed(title=f'{self.SERVER_TITLE} info',
                              url=f'{self.SERVER_URL}',
                              color=0x99ff00 if len(player_info) - 1 > 0 else 0xFF5733)
        embed.add_field(name=f'Player Count ({len(player_info) - 1})',
                        value='\n'.join(player_info[:-1]) if len(player_info) - 1 > 0 else 'None',
                        inline=True)
        embed.add_field(name='Map',
                        value=player_info[-1],
                        inline=True)
        # Assume that today is... today? 
        # todo; No hardcoded date
        embed.set_footer(text=f'This information updates every 5 minutes. Updated: Today at {datetime.datetime.now().strftime("%-I:%M:%S %p")} PST')
        return embed

    @tasks.loop(minutes=5)  # task runs every 5 minutes
    async def my_background_task(self):
        channel = self.get_channel(self.channel_id)
        embed = await self._get_embed()

        if not(self.ran_once):
            self.embed_message = await channel.send(embed=embed)
            self.ran_once = True
            print('Sent first embed!')
        else:
            if embed:
                await self.embed_message.edit(embed=embed)
                print('Edited embed!')

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in
        # Delete old messages in the channel
        channel = self.get_channel(self.channel_id)
        await channel.purge()

client = MyClient()
client.run(TOKEN)

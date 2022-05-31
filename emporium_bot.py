from http.client import HTTPException
from discord.ext import tasks
from dotenv import load_dotenv
from datetime import datetime

import discord
import a2s
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
        print('Logged in as:')
        print(self.user.name)
        print(self.user.id)
        print('------')
        
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{self.SERVER[0]}"))

    async def _query_server(self):
        """Querys the server for players, and current map"""
        accurate_players = []
        info = a2s.info(self.SERVER).map_name
        players = a2s.players(self.SERVER)
        for player in sorted(players,
                             key=lambda p: p.score,
                             reverse=True):
            # The query can sometimes return empty players, which screws up player count:
            # https://python-valve.readthedocs.io/en/latest/source.html#valve.source.a2s.ServerQuerier.players
            if player.name:
                accurate_players.append(f'{player.name} - {player.score}')
        accurate_players.append(f'{info}')
        return accurate_players

    async def _get_embed(self):
        try:
            player_info = await self._query_server()
        except TimeoutError: # Okay we timed out... Not good! Maybe it was a fluke? Retry 2 times.
            for attempt in range(2):
                print(f'Timed out from {self.SERVER[0]}, retrying... ({attempt + 1}/2)')
                try:
                    player_info = await self._query_server()
                except TimeoutError:
                    continue
                else:
                    break
            else: # Not a fluke, server is offline.
                player_info = None
        embed = discord.Embed(title=f'{self.SERVER_TITLE}',
                              url=f'{self.SERVER_URL}',
                              description='Status: Online' if player_info else 'Status: Offline',
                              color=0x99ff00 if player_info else 0xFF0000,
                              timestamp=datetime.utcnow())
        embed.add_field(name=f'Player Count ({len(player_info) - 1})' if player_info else f'Player Count (0)',
                        value='\n'.join(player_info[:-1]) if player_info and len(player_info) - 1 > 0 else 'None',
                        inline=True)
        embed.add_field(name='Map',
                        value=player_info[-1] if player_info else 'Unknown',
                        inline=True)
        if not(player_info):
            embed.add_field(name=':rotating_light: Critical Error :rotating_light:',
                            value='If this issue still persists please contact: Car#5159',
                            inline=False)
        embed.set_footer(text='\u200b',icon_url='https://i.imgur.com/iBtPVkB.png')
        return embed

    @tasks.loop(minutes=1)  # task runs every 1 minutes
    async def my_background_task(self):
        channel = self.get_channel(self.channel_id)
        embed = await self._get_embed()

        if not(self.ran_once):
            self.embed_message = await channel.send(embed=embed)
            self.ran_once = True
            print('Sent embed!')
        else:
            if embed:
                try:
                    await self.embed_message.edit(embed=embed)
                except discord.errors.HTTPException: # If edit fails purge channel and send new embed
                    await channel.purge()
                    self.embed_message = await channel.send(embed=embed)
                    print('Embed deleted, or missing! Sending new embed!')
                else:
                    print('Edited embed!')


    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in
        # Delete old messages in the channel
        channel = self.get_channel(self.channel_id)
        await channel.purge()

client = MyClient()
client.run(TOKEN)

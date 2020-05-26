# voice.py
#
# Author: Jacky Zhang (jackyeightzhang)
# Contributor:  Fanny Avila (Fa-Avila),
#               Marcos Avila (DaiconV)
# Date created: 12/16/2019
# Date last modified: 5/10/2020
# Python Version: 3.8.1
# License: MIT License

from discord import ClientException
from discord.ext import commands

from blabber.audio import TTSAudio
from blabber.checks import *
from blabber.errors import *
from blabber.request import TTSRequest


class Voice(commands.Cog):
    """
    Collection of commands for handling connection to Discord voice channel.

    parameters:
        bot [Bot]: client object representing a Discord bot
    """
    def __init__(self, bot):
        self.pool = bot.pool
        self.voices = bot.voices
        self.voice_profiles = bot.voice_profiles

    async def _connect(self, ctx):
        """
        Helper method for connecting Blabber to the command invoker's voice
        channel.

        parameters:
            ctx [Context]: context object generated by a command invocation
        returns:
            str: voice channel operation performed by Blabber
        """
        # Check if Blabber is currently connected to a voice channel
        if ctx.voice_client:
            await can_disconnect(ctx)
            await blabber_has_required_permissions(ctx)

            # Clear audio channel before moving Blabber
            player = ctx.voice_client._player
            if player is not None:
                player.source.clear()

            # Move Blabber to the command invoker's voice channel
            await ctx.voice_client.move_to(ctx.author.voice.channel)
            return 'Moved'
        else:
            await blabber_has_required_permissions(ctx)

            # Connect Blabber to the command invoker's voice channel
            await ctx.author.voice.channel.connect()
            return 'Connected'

    @commands.command(name='disconnect', aliases=['dc'])
    async def disconnect(self, ctx):
        """
        Disconnects Blabber from the voice channel it is connected to.

        parameters:
            ctx [Context]: context object generated by a command invocation
        """
        # Check if Blabber is currently connected to a voice channel
        if not ctx.voice_client:
            await ctx.send(":information_source: **Blabber is not connected to any voice channel**")
        else:
            await can_disconnect(ctx)

            # Disconnect Blabber from voice channel
            await ctx.voice_client.disconnect()
            await ctx.send(":white_check_mark: **Successfully disconnected**")

    @commands.command(name='connect', aliases=['c'])
    @commands.check(is_connected)
    async def connect(self, ctx):
        """
        Connects Blabber to the voice channel the command invoker is connected
        to.

        parameters:
            ctx [Context]: context object produced by a command invocation
        """
        # Check if Blabber is connected to command invoker's voice channel
        if ctx.voice_client and ctx.author.voice.channel == ctx.voice_client.channel:
            await ctx.send(":information_source: **Blabber is already in this voice channel**")
        else:
            operation = await self._connect(ctx)
            await ctx.send(f":white_check_mark: **{operation} to** `{ctx.author.voice.channel.name}`")
        
    @commands.command(name='say', aliases=['s'])
    @commands.check(is_connected)
    @commands.check(tts_message_is_valid)
    async def say(self, ctx, *, message:str):
        """
        Recites a message into the voice channel the command invoker is
        connected to.

        parameters:
            ctx [Context]: context object produced by a command invocation
            message [str]: message to recite
        """
        # Ensure Blabber is connected to command invoker's voice channel
        if not ctx.voice_client or ctx.author.voice.channel != ctx.voice_client.channel:
            await self._connect(ctx)
        
        # Check if AudioSource object already exists
        if ctx.voice_client._player:
            audio = ctx.voice_client._player.source
        else:
            audio = TTSAudio(self.pool)

        # Retrieve command invoker's voice profile
        alias = self.voice_profiles[(ctx.author, ctx.channel)]
        voice = self.voices[alias]

        # Submit TTS request
        request = TTSRequest(message, **voice)
        await audio.submit_request(request)

        # Ensure AudioSource object is playing
        if not ctx.voice_client.is_playing():
            ctx.voice_client.play(audio)

        await ctx.message.add_reaction('📣')

    @connect.error
    async def connect_error(self, ctx, error):
        """
        Local error handler for Blabber's connect command.

        parameters:
            ctx [Context]: context object produced by a command invocation
            error [Exception]: error object thrown by command function
        """
        # Check what type of voice channel operation caused the error
        operation = 'move' if ctx.voice_client else 'connect'

        await ctx.send(f":x: **Unable to {operation}**\n{error}")
    
    @disconnect.error
    async def disconnect_error(self, ctx, error):
        """
        Local error handler for Blabber's disconnect command.

        parameters:
            ctx [Context]: context object produced by a command invocation
            error [Exception]: error object thrown by command
        """
        await ctx.send(f":x: **Unable to disconnect**\n{error}")

    @say.error
    async def say_error(self, ctx, error):
        """
        Local error handler for Blabber's say command.

        parameters:
            ctx [Context]: context object produced by a command invocation
            error [Exception]: error object thrown by command function
        """
        if isinstance(error, BlabberConnectError):
            await self.connect_error(ctx, error)
        else:
            await ctx.send(f":x: **Unable to convert to speech**\n{error}")
                
def setup(bot):
    """
    Adds Voice Cog to bot.

    parameter: 
        bot [discord.Bot]: discord Bot object
    """
    bot.add_cog(Voice(bot))

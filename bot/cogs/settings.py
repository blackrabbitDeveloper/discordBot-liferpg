import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.guild_config import set_channel, get_channel, remove_channel


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setchannel", description="채널 용도를 설정합니다 (관리자 전용)")
    @app_commands.describe(
        config_type="설정할 채널 종류",
        channel="설정할 채널 (비워두면 현재 설정 해제)",
    )
    @app_commands.choices(config_type=[
        app_commands.Choice(name="환영 메시지", value="welcome"),
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setchannel(
        self,
        interaction: discord.Interaction,
        config_type: app_commands.Choice[str],
        channel: discord.TextChannel | None = None,
    ):
        with get_session() as session:
            guild_id = str(interaction.guild_id)

            if channel is None:
                removed = remove_channel(session, guild_id, config_type.value)
                if removed:
                    await interaction.response.send_message(
                        f"**{config_type.name}** 채널 설정을 해제했어요.", ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"**{config_type.name}** 채널이 설정되어 있지 않아요.", ephemeral=True
                    )
                return

            set_channel(session, guild_id, config_type.value, str(channel.id))
            await interaction.response.send_message(
                f"**{config_type.name}** 채널을 {channel.mention}(으)로 설정했어요!", ephemeral=True
            )

    @setchannel.error
    async def setchannel_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "이 명령어는 서버 관리 권한이 필요해요.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))

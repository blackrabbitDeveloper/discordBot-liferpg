# bot/cogs/admin.py
import json
import discord
from discord.ext import commands
from discord import app_commands
from core.database import get_session
from core.analytics import generate_analytics


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="analyze", description="[개발자 전용] AI 분석용 데이터를 출력합니다")
    @app_commands.describe(days="분석 기간 (일, 기본 7)")
    async def analyze(self, interaction: discord.Interaction, days: int = 7):
        # 봇 소유자(개발자)만 사용 가능
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            await interaction.response.send_message(
                "개발자만 사용할 수 있는 명령어예요.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        session = get_session()
        try:
            data = generate_analytics(session, period_days=days)
            json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)

            # Discord 메시지 제한 2000자 → 파일로 전송
            if len(json_str) > 1800:
                # 요약 Embed + JSON 파일 첨부
                retention = data.get("retention", {})
                engagement = data.get("engagement", {})
                quest = data.get("quest_analysis", {})
                risk = data.get("risk", {})

                embed = discord.Embed(
                    title=f"분석 리포트 ({data['period']})",
                    color=discord.Color.gold(),
                )
                embed.add_field(
                    name="유저",
                    value=f"전체: {data['total_users']} / 활성: {data['active_users']}",
                    inline=True,
                )
                embed.add_field(
                    name="위험 유저",
                    value=f"{risk.get('risk_users_count', 0)}명",
                    inline=True,
                )
                embed.add_field(name="\u200b", value="\u200b", inline=True)

                # 유지율
                embed.add_field(
                    name="유지율 (핵심 지표)",
                    value=(
                        f"온보딩 완료: {retention.get('onboarding_completion_rate', 0)}%\n"
                        f"첫 퀘스트 선택: {retention.get('first_quest_selection_rate', 0)}%\n"
                        f"첫날 완료: {retention.get('first_day_completion_rate', 0)}%\n"
                        f"Day1: {retention.get('day1_retention', 0)}% / "
                        f"Day2: {retention.get('day2_retention', 0)}% / "
                        f"Day3: {retention.get('day3_retention', 0)}%\n"
                        f"Day7: {retention.get('day7_retention', 0)}%"
                    ),
                    inline=False,
                )

                # 참여도
                embed.add_field(
                    name="참여도",
                    value=(
                        f"일일 완료율: {engagement.get('avg_daily_completion_rate', 0)}%\n"
                        f"평균 스트릭: {engagement.get('streak_avg', 0)}일"
                    ),
                    inline=True,
                )

                flow = engagement.get("flow_distribution", {})
                if flow:
                    flow_text = " / ".join(f"{k}: {v}" for k, v in flow.items())
                    embed.add_field(name="플로우 분포", value=flow_text, inline=True)

                # 퀘스트 분석
                most_completed = quest.get("most_completed_category")
                most_skipped = quest.get("most_skipped_category")
                if most_completed or most_skipped:
                    embed.add_field(
                        name="카테고리",
                        value=f"완료 최다: {most_completed or '-'}\n건너뜀 최다: {most_skipped or '-'}",
                        inline=False,
                    )

                diff_rates = quest.get("difficulty_completion_rates", {})
                if diff_rates:
                    diff_text = " / ".join(f"{k}: {v}%" for k, v in diff_rates.items())
                    embed.add_field(name="난이도별 완료율", value=diff_text, inline=False)

                flow = summary.get("flow_distribution", {})
                if flow:
                    flow_text = " / ".join(f"{k}: {v}회" for k, v in flow.items())
                    embed.add_field(name="플로우 분포", value=flow_text, inline=False)

                replaced = summary.get("most_replaced_quests", [])
                if replaced:
                    embed.add_field(
                        name="교체 많은 퀘스트",
                        value="\n".join(f"- {q}" for q in replaced[:5]),
                        inline=False,
                    )

                embed.set_footer(text="상세 데이터는 첨부 JSON 파일을 AI에게 전달하세요")

                # JSON 파일로 첨부
                file = discord.File(
                    fp=__import__("io").BytesIO(json_str.encode("utf-8")),
                    filename=f"analytics_{data['period'].replace(' ', '').replace('~', '_')}.json",
                )
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            else:
                await interaction.followup.send(f"```json\n{json_str}\n```", ephemeral=True)
        finally:
            session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))

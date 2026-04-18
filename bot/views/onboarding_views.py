# bot/views/onboarding_views.py
import discord
from core.onboarding import (
    GOAL_CATEGORIES, TIME_BUDGETS, ENERGY_LEVELS, DIFFICULTY_LEVELS,
    create_user,
)
from core.database import get_session


class CategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cat, value=cat)
            for cat in GOAL_CATEGORIES
        ]
        super().__init__(
            placeholder="가장 바꾸고 싶은 영역을 선택하세요",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.goal_category = self.values[0]
        await interaction.response.send_message(
            f"'{self.values[0]}' 선택! 이 영역에서 이루고 싶은 목표를 입력해주세요.",
            ephemeral=True,
        )
        self.view.stop()


class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.goal_category = None
        self.add_item(CategorySelect())


class TimeBudgetView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.time_budget = None

    @discord.ui.button(label="10분 이하", style=discord.ButtonStyle.secondary)
    async def short(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.time_budget = "short"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="10~30분", style=discord.ButtonStyle.primary)
    async def medium(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.time_budget = "medium"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="30분 이상", style=discord.ButtonStyle.success)
    async def long(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.time_budget = "long"
        await interaction.response.defer()
        self.stop()


class EnergyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.energy = None

    @discord.ui.button(label="낮음", style=discord.ButtonStyle.secondary)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.energy = "low"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="보통", style=discord.ButtonStyle.primary)
    async def normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.energy = "normal"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="높음", style=discord.ButtonStyle.success)
    async def high(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.energy = "high"
        await interaction.response.defer()
        self.stop()


class DifficultyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.difficulty = None

    @discord.ui.button(label="아주 가볍게", style=discord.ButtonStyle.secondary)
    async def light(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.difficulty = "light"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="적당히", style=discord.ButtonStyle.primary)
    async def moderate(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.difficulty = "moderate"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="조금 빡세게", style=discord.ButtonStyle.danger)
    async def hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.difficulty = "hard"
        await interaction.response.defer()
        self.stop()

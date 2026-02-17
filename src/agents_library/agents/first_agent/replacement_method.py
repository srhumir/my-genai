import datetime

from src.agents_library.base import BaseAgent


def variables_to_replace_in_prompt(self: BaseAgent) -> dict[str, str]:
    return {
        "bot_user_name": self.session_config.bot_user_name,
        "date_now": datetime.date.today().isoformat(),
    }

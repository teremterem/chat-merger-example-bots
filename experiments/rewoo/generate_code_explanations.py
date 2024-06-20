# pylint: disable=wrong-import-position
import asyncio
import shutil
import sys
from pathlib import Path

from botmerger import BotResponses
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parents[2]))

from experiments.rewoo.print_code_explanations import BOTMERGER_EXPLANATIONS_PATH
from experiments.rewoo.rewoo import explain_file_bot
from experiments.rewoo.rewoo_utils import list_botmerger_files


async def save_the_explanation(file: str, bot_responses: BotResponses) -> None:
    explanation = (await bot_responses.get_final_response()).content
    explanation = f"FILE: {file}\n\n{explanation}"
    explanation_file_path = BOTMERGER_EXPLANATIONS_PATH / f"{file}.txt"
    explanation_file_path.parent.mkdir(parents=True, exist_ok=True)
    explanation_file_path.write_text(explanation, encoding="utf-8")


async def main() -> None:
    shutil.rmtree(BOTMERGER_EXPLANATIONS_PATH, ignore_errors=True)

    tasks = []
    for file in list_botmerger_files():
        responses = await explain_file_bot.bot.trigger(file)
        tasks.append(asyncio.create_task(save_the_explanation(file, responses)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

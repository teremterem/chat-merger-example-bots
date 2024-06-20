# pylint: disable=wrong-import-position
import asyncio
import shutil
import sys
from pathlib import Path

from botmerger import BotResponses
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parents[2]))

from experiments.rewoo.print_code_explanations import BOTMERGER_EXPLANATION_CRITICISM_PATH
from experiments.rewoo.rewoo import criticize_explanation
from experiments.rewoo.rewoo_utils import list_botmerger_files


async def save_the_criticism(file: str, bot_responses: BotResponses) -> None:
    explanation = (await bot_responses.get_final_response()).content
    explanation = f"FILE: {file}\n\n{explanation}"
    explanation_file_path = BOTMERGER_EXPLANATION_CRITICISM_PATH / f"{file}.txt"
    explanation_file_path.parent.mkdir(parents=True, exist_ok=True)
    explanation_file_path.write_text(explanation, encoding="utf-8")


async def main() -> None:
    shutil.rmtree(BOTMERGER_EXPLANATION_CRITICISM_PATH, ignore_errors=True)

    tasks = []
    for file in list_botmerger_files():
        responses = await criticize_explanation.bot.trigger(file)
        tasks.append(asyncio.create_task(save_the_criticism(file, responses)))

    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())

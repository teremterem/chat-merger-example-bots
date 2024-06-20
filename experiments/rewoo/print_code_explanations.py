# pylint: disable=wrong-import-position
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parents[2]))

from experiments.rewoo.rewoo_utils import list_botmerger_files, BOTMERGER_REPO_PATH

BOTMERGER_EXPLANATIONS_PATH = Path(f"{BOTMERGER_REPO_PATH.as_posix()}.inspection") / "explanations"
BOTMERGER_EXPLANATIONS_ON_REPO_PATH = Path(f"{BOTMERGER_REPO_PATH.as_posix()}.inspection") / "explanations-on-repo"
BOTMERGER_EXPLANATION_CRITICISM_PATH = Path(f"{BOTMERGER_REPO_PATH.as_posix()}.inspection") / "explanation-criticism"


def get_botmerger_explanations() -> list[str]:
    result = [
        (BOTMERGER_EXPLANATIONS_PATH / f"{file}.txt").read_text(encoding="utf-8") for file in list_botmerger_files()
    ]
    return result


def get_botmerger_explanations_on_repo() -> list[str]:
    result = [
        (BOTMERGER_EXPLANATIONS_ON_REPO_PATH / f"{file}.txt").read_text(encoding="utf-8")
        for file in list_botmerger_files()
    ]
    return result


def get_botmerger_explanation_criticism() -> list[str]:
    result = [
        (BOTMERGER_EXPLANATION_CRITICISM_PATH / f"{file}.txt").read_text(encoding="utf-8")
        for file in list_botmerger_files()
    ]
    return result


def main() -> None:
    for explanation, exp_criticism in zip(get_botmerger_explanations(), get_botmerger_explanation_criticism()):
        print()
        print()
        print()
        print(explanation)
        print()
        print()
        print("[CRITICISM]", exp_criticism)
        # print()
        # print()
        # print("[BETTER?]", exp_over_repo)
    print()
    print()
    print()
    print("\n".join(list_botmerger_files()))
    print()
    print()
    print()


if __name__ == "__main__":
    main()

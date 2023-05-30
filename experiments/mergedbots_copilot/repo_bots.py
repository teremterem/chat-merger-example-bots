from pathlib import Path
from typing import AsyncGenerator

from langchain import LLMChain
from langchain.chat_models import PromptLayerChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from mergedbots import MergedBot, MergedMessage

from experiments.common.bot_manager import bot_manager, FAST_GPT_MODEL
from experiments.common.repo_access_utils import list_files_in_repo

REPO_DIR = Path(__file__).parents[3] / "mergedbots"

# `gpt-3.5-turbo` (unlike `gpt-4`) might pay more attention to `user` messages than `system` messages
EXTRACT_FILE_PATH_PROMPT = ChatPromptTemplate.from_messages(
    [
        HumanMessagePromptTemplate.from_template("{file_list}"),
        HumanMessagePromptTemplate.from_template(
            """\
HERE IS A REQUEST FROM A USER:

{request}"""
        ),
        HumanMessagePromptTemplate.from_template(
            """\
IF THE USER IS ASKING FOR A FILE FROM THE REPO ABOVE, PLEASE RESPOND WITH THE FOLLOWING JSON:
{{
    "file": "path/to/file"
}}

IF THE USER IS ASKING FOR A FILE THAT IS NOT LISTED ABOVE OR THERE IS NO MENTION OF A FILE IN THE USER'S REQUEST, \
PLEASE RESPOND WITH THE FOLLOWING JSON:
{{
    "file": ""  // empty string
}}

YOUR RESPONSE:
{{
    "file": "\
"""
        ),
    ]
)


@bot_manager.create_bot(handle="ListRepoTool")
async def list_repo_tool(bot: MergedBot, message: MergedMessage) -> AsyncGenerator[MergedMessage, None]:
    file_list = list_files_in_repo(REPO_DIR)
    file_list_strings = [file.as_posix() for file in file_list]
    file_list_string = "\n".join(file_list_strings)

    result = (
        f"Here is the complete list of files that can be found in `{REPO_DIR.name}` repo:\n"
        f"```\n"
        f"{file_list_string}\n"
        f"```"
    )
    yield await message.final_bot_response(
        bot,
        result,
        custom_fields={"file_list": file_list_strings},  # TODO are you sure you need this ?
    )


@bot_manager.create_bot(handle="ReadFileBot")
async def read_file_bot(bot: MergedBot, message: MergedMessage) -> AsyncGenerator[MergedMessage, None]:
    # TODO implement bot fulfillment caching
    # TODO implement a utility function that simply returns the final bot response
    file_list_msg = [resp async for resp in list_repo_tool.merged_bot.fulfill(message)][-1]
    # yield file_list_msg  # TODO here is where it would be cool to override `is_still_typing`
    file_set = set(file_list_msg.custom_fields["file_list"])

    chat_llm = PromptLayerChatOpenAI(
        model_name=FAST_GPT_MODEL,
        temperature=0.0,
        model_kwargs={
            "stop": ['"', "\n"],
            "user": str(message.originator.uuid),
        },
        pl_tags=["read_file_bot"],
    )
    llm_chain = LLMChain(
        llm=chat_llm,
        prompt=EXTRACT_FILE_PATH_PROMPT,
    )
    file_path = await llm_chain.arun(request=message.content, file_list=file_list_msg.content)

    if file_path and file_path in file_set:
        yield await message.interim_bot_response(bot, file_path)

        yield await message.final_bot_response(
            bot,
            Path(REPO_DIR, file_path).read_text(encoding="utf-8"),
            custom_fields={"success": True},
        )
    else:
        yield await message.final_bot_response(
            bot,
            "Please specify a file you want to read.",
            custom_fields={"success": False},
        )

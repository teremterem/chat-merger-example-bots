import json

from botmerger import SingleTurnContext, BotResponses
from langchain import LLMChain
from langchain.chat_models import PromptLayerChatOpenAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.schema import HumanMessage

from experiments.common.bot_merger import bot_merger, FAST_GPT_MODEL, SLOW_GPT_MODEL
from experiments.rewoo.print_code_explanations import BOTMERGER_EXPLANATIONS_PATH
from experiments.rewoo.print_code_outlines import get_botmerger_outlines
from experiments.rewoo.rewoo_utils import list_botmerger_files, BOTMERGER_REPO_PATH

GET_FILE_PATH_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            "Here is the complete list of files that can be found in `{repo_name}` repo:"
        ),
        HumanMessagePromptTemplate.from_template("{file_list}"),
        SystemMessagePromptTemplate.from_template("AND HERE IS A REQUEST FROM A USER:"),
        HumanMessagePromptTemplate.from_template("{request}"),
        SystemMessagePromptTemplate.from_template(
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
EXPLAIN_FILE_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template("Here is the content of `{file_path}`:"),
        HumanMessagePromptTemplate.from_template("{file_content}"),
        SystemMessagePromptTemplate.from_template("Please explain this content in plain English."),
    ]
)
EXPLAIN_FILE_OVER_WHOLE_REPO_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template("Here are contents of all the files in `{repo_name}` repo."),
        HumanMessagePromptTemplate.from_template("{other_file_contents}"),
        SystemMessagePromptTemplate.from_template(
            "And here is the content of `{file_path}`, the file that you need to explain."
        ),
        HumanMessagePromptTemplate.from_template("{file_content}"),
        SystemMessagePromptTemplate.from_template("Please explain the content of `{file_path}` in plain English."),
    ]
)
CRITICIZE_EXPLANATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template("Here are contents of all the files in `{repo_name}` repo."),
        HumanMessagePromptTemplate.from_template("{other_file_contents}"),
        SystemMessagePromptTemplate.from_template(
            "Here is the content of `{file_path}`, the explanation of which you will need to criticize."
        ),
        HumanMessagePromptTemplate.from_template("{file_content}"),
        SystemMessagePromptTemplate.from_template("And here is the EXPLANATION of the content of `{file_path}`."),
        HumanMessagePromptTemplate.from_template("{file_explanation}"),
        SystemMessagePromptTemplate.from_template(
            """\
Please find flaws in this explanation (potentially misleading information, incomplete information, imprecise \
information, not deep enough explanation etc.)\
"""
        ),
    ]
)
GENERATE_FILE_OUTLINE_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            """\
You are a chatbot that generates code outlines and lists dependencies for source code files of a repository in the \
following format:
```
Declared concepts:
- concept1 - a class
- concept2 - a function
- concept3 - a variable

Other files from this repo this file depends on:
- file1
- file2

Third-party libraries this file depends on:
- library1
- library2

Built-in libraries this file depends on:
- library1
- library2
```

The name of the repository name is `{repo_name}`. This repository contains the following files:\
"""
        ),
        HumanMessagePromptTemplate.from_template("{file_list}"),
        SystemMessagePromptTemplate.from_template("Here is the content of `{file_path}`:"),
        HumanMessagePromptTemplate.from_template("{file_content}"),
        SystemMessagePromptTemplate.from_template(
            "Please outline all the concepts that are DECLARED in this file and list this file's dependencies."
        ),
    ]
)
REWOO_PLANNER_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            """\
You are a chatbot that is good at analysing the code in the following repository and answering questions about the \
concepts that can be found in this repository.

Repository name: {repo_name}
List of files in the repository:\
"""
        ),
        HumanMessagePromptTemplate.from_template("{file_list}"),
        SystemMessagePromptTemplate.from_template(
            "And here are the outlines of the source code files in `{repo_name}` repo:"
        ),
        HumanMessagePromptTemplate.from_template("{file_outlines}"),
        SystemMessagePromptTemplate.from_template(
            """\
For the following tasks, make plans that can solve the problem step-by-step. For each plan, indicate which external \
tool together with tool input to retrieve evidence. You can store the evidence into a variable that can be called \
by later tools.

Here is the expected format of your response:\
"""
        ),
        SystemMessagePromptTemplate.from_template(
            """\
{{
    "evidence1": {{
        "plan": "explanation of a step of the plan",
        "tool": "Tool1",
        "tool_input": "free form text",
        "context": []
    }},
    "evidence2": {{
        "plan": "explanation of a step of the plan",
        "tool": "Tool2",
        "tool_input": "free form text",
        "context": []
    }},
    "evidence3": {{
        "plan": "explanation of a step of the plan",
        "tool": "Tool1",
        "tool_input": "free form text",
        "context": ["evidence2"]
    }},
    "evidence4": {{
        "plan": "explanation of a step of the plan",
        "tool": "Tool3",
        "tool_input": "free form text",
        "context": ["evidence1", "evidence3"]
    }}
}}\
"""
        ),
        #         SystemMessagePromptTemplate.from_template(
        #             """\
        # Tools can be one of the following:
        #
        # {tools}
        #
        # Begin! Describe your plans with rich details. RESPOND WITH VALID JSON ONLY AND NO OTHER TEXT.\
        # """
        #         ),
        SystemMessagePromptTemplate.from_template(
            "Begin! Describe your plans with rich details. RESPOND WITH VALID JSON ONLY AND NO OTHER TEXT."
        ),
        HumanMessagePromptTemplate.from_template("{request}"),
    ]
)


@bot_merger.create_bot("GetFilePathBot")
async def get_file_path_bot(context: SingleTurnContext) -> None:
    file_list = list_botmerger_files()
    file_list_str = "\n".join(file_list)
    file_set = set(file_list)

    async def yield_file_path(file_path: str) -> bool:
        if not file_path:
            return False

        file_path = file_path.strip()
        if file_path in file_set:
            await context.yield_final_response(file_path)
            return True

        return False

    if await yield_file_path(context.concluding_request.content):
        return

    async def figure_out_the_file_path(model_name: str) -> bool:
        chat_llm = PromptLayerChatOpenAI(
            model_name=model_name,
            temperature=0.0,
            model_kwargs={"stop": ['"', "\n"]},
            pl_tags=["get_file_path_bot"],
        )
        llm_chain = LLMChain(
            llm=chat_llm,
            prompt=GET_FILE_PATH_PROMPT,
        )
        file_path = await llm_chain.arun(
            repo_name=BOTMERGER_REPO_PATH.name,
            file_list=file_list_str,
            request=context.concluding_request.content,
        )
        return await yield_file_path(file_path)

    if not await figure_out_the_file_path(FAST_GPT_MODEL):
        if not await figure_out_the_file_path(SLOW_GPT_MODEL):
            raise ValueError(f"```\n{file_list_str}\n```\nPlease specify one of the files from the list above.")


@bot_merger.create_bot(
    "FileReaderBot",
    description=(
        "Displays the content of a file from the repository. Input should be a file path. Does not accept file "
        "paths that are not present in the list of files above. Useful when you need to look at the code directly."
    ),
)
async def read_file_bot(context: SingleTurnContext) -> None:
    file_path_msg = await get_file_path_bot.bot.get_final_response(context.concluding_request)
    file_path = BOTMERGER_REPO_PATH / file_path_msg.content

    await context.yield_final_response(file_path.read_text(encoding="utf-8"))


@bot_merger.create_bot(
    "CodeExplainerBot",
    description=(
        "Explains the code in a repository file. Input should be a file path. Does not accept "
        "file paths that are not present in the list of files above."
    ),
)
async def explain_file_bot(context: SingleTurnContext) -> None:
    file_path_msg = await get_file_path_bot.bot.get_final_response(context.concluding_request)

    # TODO use the future `InquiryBot` to report this interim result ? and move it to the `get_file_path_bot` ?
    await context.yield_interim_response(file_path_msg)

    file_content_msg = await read_file_bot.bot.get_final_response(file_path_msg.content)

    chat_llm = PromptLayerChatOpenAI(
        model_name=SLOW_GPT_MODEL,
        temperature=0.0,
        pl_tags=["explain_file_bot"],
    )
    llm_chain = LLMChain(
        llm=chat_llm,
        prompt=EXPLAIN_FILE_PROMPT,
    )
    file_explanation = await llm_chain.arun(file_path=file_path_msg.content, file_content=file_content_msg.content)
    await context.yield_final_response(file_explanation)


@bot_merger.create_bot("CodeExplainerOverWholeRepo")
async def explain_file_over_whole_repo(context: SingleTurnContext) -> None:
    file_path = (await get_file_path_bot.bot.get_final_response(context.concluding_request)).content

    # TODO use the future `InquiryBot` to report this interim result ? and move it to the `get_file_path_bot` ?
    await context.yield_interim_response(file_path)

    other_file_contents = []
    for another_file_path in list_botmerger_files():
        if another_file_path == file_path:
            continue
        another_file_content = (await read_file_bot.bot.get_final_response(another_file_path)).content
        other_file_contents.append(f"======= FILE: {another_file_path} =======\n\n{another_file_content}")
    other_file_contents_str = "\n\n\n".join(other_file_contents)

    file_content = (await read_file_bot.bot.get_final_response(file_path)).content

    chat_llm = PromptLayerChatOpenAI(
        model_name=SLOW_GPT_MODEL,
        temperature=0.0,
        pl_tags=["explain_file_over_repo"],
    )
    llm_chain = LLMChain(
        llm=chat_llm,
        prompt=EXPLAIN_FILE_OVER_WHOLE_REPO_PROMPT,
    )
    file_explanation = await llm_chain.arun(
        repo_name=BOTMERGER_REPO_PATH.name,
        other_file_contents=other_file_contents_str,
        file_path=file_path,
        file_content=file_content,
    )
    await context.yield_final_response(file_explanation)


@bot_merger.create_bot("CriticizeExplanationBot")
async def criticize_explanation(context: SingleTurnContext) -> None:
    file_path = (await get_file_path_bot.bot.get_final_response(context.concluding_request)).content

    # TODO use the future `InquiryBot` to report this interim result ? and move it to the `get_file_path_bot` ?
    await context.yield_interim_response(file_path)

    other_file_contents = []
    for another_file_path in list_botmerger_files():
        if another_file_path == file_path:
            continue
        another_file_content = (await read_file_bot.bot.get_final_response(another_file_path)).content
        other_file_contents.append(f"======= FILE: {another_file_path} =======\n\n{another_file_content}")
    other_file_contents_str = "\n\n\n".join(other_file_contents)

    file_content = (await read_file_bot.bot.get_final_response(file_path)).content

    chat_llm = PromptLayerChatOpenAI(
        model_name=SLOW_GPT_MODEL,
        temperature=0.0,
        pl_tags=["criticise_explanation"],
    )
    llm_chain = LLMChain(
        llm=chat_llm,
        prompt=CRITICIZE_EXPLANATION_PROMPT,
    )
    file_explanation = await llm_chain.arun(
        repo_name=BOTMERGER_REPO_PATH.name,
        other_file_contents=other_file_contents_str,
        file_path=file_path,
        file_content=file_content,
        file_explanation=(BOTMERGER_EXPLANATIONS_PATH / f"{file_path}.txt").read_text(encoding="utf-8"),
    )
    await context.yield_final_response(file_explanation)


@bot_merger.create_bot(
    "CodeOutlineGeneratorBot",
    description=(
        "Displays the outline of a source code file from the repository. Input should be a file path. Does not accept "
        "file paths that are not present in the list of files above."
    ),
)
async def generate_file_outline(context: SingleTurnContext) -> None:
    file_path_msg = await get_file_path_bot.bot.get_final_response(context.concluding_request)
    file_list = "\n".join(list_botmerger_files())

    # TODO use the future `InquiryBot` to report this interim result ? and move it to the `get_file_path_bot` ?
    await context.yield_interim_response(file_path_msg)

    file_content_msg = await read_file_bot.bot.get_final_response(file_path_msg.content)

    chat_llm = PromptLayerChatOpenAI(
        model_name=FAST_GPT_MODEL,
        temperature=0.0,
        pl_tags=["generate_outline_bot"],
    )
    llm_chain = LLMChain(
        llm=chat_llm,
        prompt=GENERATE_FILE_OUTLINE_PROMPT,
    )
    file_explanation = await llm_chain.arun(
        repo_name=BOTMERGER_REPO_PATH.name,
        file_list=file_list,
        file_path=file_path_msg.content,
        file_content=file_content_msg.content,
    )
    await context.yield_final_response(file_explanation)


@bot_merger.create_bot(
    "ConceptExplorerBot",
    description=(
        "A complex bot that is an exact copy of yourself. Capable of generating and carrying out elaborate plans "
        "just like you. Has access to all the same tools as you do. Input should be a question about a concept."
    ),
)
async def rewoo(context: SingleTurnContext) -> None:
    file_list = "\n".join(list_botmerger_files())

    chat_llm = PromptLayerChatOpenAI(
        model_name=SLOW_GPT_MODEL,
        temperature=0.5,
        pl_tags=["rewoo_planner"],
    )
    llm_chain = LLMChain(
        llm=chat_llm,
        prompt=REWOO_PLANNER_PROMPT,
    )
    # rewoo_tools = (
    #     explain_file_bot.bot,
    #     generate_file_outline.bot,
    #     read_file_bot.bot,
    #     rewoo.bot,
    #     simpler_llm.bot,
    # )
    generated_plan = json.loads(
        await llm_chain.arun(
            repo_name=BOTMERGER_REPO_PATH.name,
            file_list=file_list,
            file_outlines="\n\n\n".join(get_botmerger_outlines()),
            # tools="\n\n".join([f"{bot.alias}[input]: {bot.description}" for bot in rewoo_tools]),
            request=context.concluding_request.content,
        )
    )
    await context.yield_final_response(generated_plan)

    promises: dict[str, BotResponses] = {}
    for evidence_id, plan in generated_plan.items():
        bot = await bot_merger.find_bot(plan["tool"])
        plan_context = [promises[previous_evidence_id] for previous_evidence_id in plan["context"]]
        promises[evidence_id] = await bot.trigger(requests=[*plan_context, plan["tool_input"]])

    for idx, (evidence_id, responses) in enumerate(promises.items()):
        await context.yield_interim_response(f"```\n{evidence_id}\n```")
        await context.yield_from(responses, still_thinking=True if idx < len(promises) - 1 else None)


@bot_merger.create_bot(
    "SimplerLLM",
    description=(
        "Displays the outline of a code file from the repository. Input should be a file path. Does not accept "
        "file paths that are not present in the list of files above."
    ),
)
async def simpler_llm(context: SingleTurnContext) -> None:
    chat_llm = PromptLayerChatOpenAI(
        model_name=SLOW_GPT_MODEL,
        temperature=0.0,
        pl_tags=["simpler_llm"],
    )
    result = await chat_llm.agenerate([[HumanMessage(content=context.concluding_request.content)]])
    await context.yield_final_response(json.loads(result.generations[0][0].text))


main_bot = rewoo.bot

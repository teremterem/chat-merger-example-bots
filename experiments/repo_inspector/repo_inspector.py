"""A bot that can inspect a repo."""
import secrets
from pathlib import Path
from typing import AsyncGenerator, Optional

import faiss
from langchain.callbacks.manager import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain.chat_models import PromptLayerChatOpenAI
from langchain.docstore import InMemoryDocstore
from langchain.embeddings import OpenAIEmbeddings
from langchain.experimental import AutoGPT
from langchain.tools import BaseTool
from langchain.tools.file_management.read import ReadFileTool
from langchain.tools.file_management.utils import BaseFileToolMixin
from langchain.vectorstores import FAISS
from mergedbots import MergedMessage, MergedBot

from experiments.common import SLOW_GPT_MODEL
from experiments.repo_inspector.repo_access_utils import list_files_in_repo

repo_inspector = MergedBot(handle="RepoInspector")


class ListRepoTool(BaseFileToolMixin, BaseTool):
    """Tool that lists all the files in a repo."""

    name: str = "list_repo"
    description: str = "List all the files in `%s` repo"
    repo_name: str = None

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if not self.repo_name:
            self.repo_name = Path(self.root_dir).name
        self.description = self.description % self.repo_name

    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        file_list: list[Path] = list_files_in_repo(self.root_dir)

        file_list_str = "\n".join([file.as_posix() for file in file_list])
        result = f"Here is the complete list of files that can be found in `{self.repo_name}` repo:\n{file_list_str}"
        return result

    async def _arun(
        self,
        dir_path: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        return self._run()


@repo_inspector
async def repo_inspector_func(bot: MergedBot, message: MergedMessage) -> AsyncGenerator[MergedMessage, None]:
    """A bot that can inspect a repo."""
    conversation = message.get_full_conversion()
    if not conversation:
        yield message.service_followup_as_final_response(bot, "```\nCONVERSATION RESTARTED\n```")
        return

    root_dir = (Path(__file__).parents[3] / "mergedbots").as_posix()
    tools = [
        ListRepoTool(root_dir=root_dir),
        ReadFileTool(root_dir=root_dir),
    ]

    embeddings_model = OpenAIEmbeddings()
    embedding_size = 1536
    index = faiss.IndexFlatL2(embedding_size)
    vectorstore = FAISS(embeddings_model.embed_query, index, InMemoryDocstore({}), {})

    model_name = SLOW_GPT_MODEL
    yield message.service_followup_for_user(bot, f"`{model_name}`")

    chat_llm = PromptLayerChatOpenAI(
        model_name=model_name,
        model_kwargs={
            "user": str(message.originator.uuid),
        },
        pl_tags=["mb_auto_gpt", secrets.token_hex(4)],
    )
    agent = AutoGPT.from_llm_and_tools(
        ai_name="RepoInspector",
        ai_role="Source code researcher",
        tools=tools,
        llm=chat_llm,
        memory=vectorstore.as_retriever(),
    )
    # Set verbose to be true
    agent.chain.verbose = True

    yield message.final_bot_response(bot, agent.run([message.content]))
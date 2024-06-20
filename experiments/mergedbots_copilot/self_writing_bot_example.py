"""
Plan: Start by examining the structure of the botmerger repository by looking at the outline of the core file, which
should contain the main functions and classes of the bot.
#E1 = CodeOutlineGeneratorBot["botmerger/core.py"]

Plan: After understanding the structure of the core file, look at the actual code in the core file to understand how to
use the functions and classes there.
#E2 = FileReaderBot["botmerger/core.py"]

Plan: The 'inquiry_bot.py' file in the 'experimental' directory might contain an example of how to create a bot. Check
the outline of this file to confirm.
#E3 = CodeOutlineGeneratorBot["botmerger/experimental/inquiry_bot.py"]

Plan: If the 'inquiry_bot.py' file does contain an example of how to create a bot, read the actual code in this file to
understand how it works.
#E4 = FileReaderBot["botmerger/experimental/inquiry_bot.py"]

Plan: Lastly, if there are any concepts in the code that are unclear, use the ConceptExplorerBot to get a detailed
explanation of these concepts.
#E5 = ConceptExplorerBot["What is the purpose of the 'inquiry_bot.py' file?"]
"""
from botmerger import SingleTurnContext
from fakeimports import code_outline_generator, file_reader, concept_explorer, solver

from experiments.common.bot_merger import bot_merger


@bot_merger.create_bot("generated", description='Answers "How can I create a bot using botmerger?" question.')
async def generated(context: SingleTurnContext) -> None:
    # Plan: Start by examining the structure of the botmerger repository by looking at the outline of the core file,
    # which should contain the main functions and classes of the bot.
    evidence1 = await code_outline_generator.bot.trigger("botmerger/core.py")
    # Plan: After understanding the structure of the core file, look at the actual code in the core file to understand
    # how to use the functions and classes there.
    evidence2 = await file_reader.bot.trigger("botmerger/core.py")
    # Plan: The 'inquiry_bot.py' file in the 'experimental' directory might contain an example of how to create a bot.
    # Check the outline of this file to confirm.
    evidence3 = await code_outline_generator.bot.trigger("botmerger/experimental/inquiry_bot.py")

    # TODO TODO TODO conditional ?
    # Plan: If the 'inquiry_bot.py' file does contain an example of how to create a bot, read the actual code in this
    # file to understand how it works.
    # Plan: Lastly, if there are any concepts in the code that are unclear, use the ConceptExplorerBot to get a detailed
    # explanation of these concepts.
    evidence4 = await concept_explorer.bot.trigger(
        [
            evidence1,
            evidence2,
            evidence3,
            "TODO if this then do this otherwise do that",
        ]
    )

    # TODO TODO TODO solver ?
    await context.yield_from(
        await solver.bot.trigger(
            [
                evidence1,
                evidence2,
                evidence3,
                evidence4,
            ]
        )
    )

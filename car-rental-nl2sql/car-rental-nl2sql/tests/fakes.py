"""A scripted stand-in for the LLM, used only to test pipeline logic deterministically."""
from typing import List


class ScriptedLLM:
    name = "scripted:test"

    def __init__(self, replies: List[str]):
        self.replies = list(replies)
        self.calls = []

    def complete(self, system, messages):
        self.calls.append(list(messages))
        return self.replies.pop(0)

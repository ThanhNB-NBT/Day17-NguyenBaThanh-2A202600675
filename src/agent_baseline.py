from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Student TODO: implement Agent A.

    Requirements:
    - Within-session memory only
    - No persistent `User.md`
    - Should forget long-term facts across new threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}

        # TODO: optionally initialize a real LangChain/LangGraph agent when dependencies exist.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: return the agent response and token accounting.

        Pseudocode:
        - If a live agent exists, call the live path.
        - Otherwise use a deterministic offline path.
        """
        if not self.force_offline:
            self._maybe_build_langchain_agent()

        if self.langchain_agent is not None:
            try:
                config = {"configurable": {"thread_id": thread_id}}
                result = self.langchain_agent.invoke({"messages": [("user", message)]}, config=config)
                last_msg = result["messages"][-1]
                content = last_msg.content
                tokens = estimate_tokens(content)
                
                # Estimate prompt tokens processed
                all_prev_msg_content = "".join(m.content for m in result["messages"][:-1])
                prompt_tokens = estimate_tokens(all_prev_msg_content) + estimate_tokens(message)

                if thread_id not in self.sessions:
                    self.sessions[thread_id] = SessionState()
                session = self.sessions[thread_id]
                session.token_usage += tokens
                session.prompt_tokens_processed += prompt_tokens

                return {
                    "content": content,
                    "tokens": tokens,
                }
            except Exception:
                pass

        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        # return cumulative agent token count for one thread.
        if thread_id not in self.sessions:
            return 0
        return self.sessions[thread_id].token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        # estimate how much prompt context this baseline kept processing.
        if thread_id not in self.sessions:
            return 0
        return self.sessions[thread_id].prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        # Baseline has no compact memory.
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement a simple offline behavior.

        Suggested behavior:
        - Store the new user message in the session
        - Generate a short deterministic reply
        - Update token counts
        - Never remember facts across different thread ids
        """
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
        session = self.sessions[thread_id]

        prompt_tokens = sum(estimate_tokens(m["content"]) for m in session.messages) + estimate_tokens(message)
        session.prompt_tokens_processed += prompt_tokens

        session.messages.append({"role": "user", "content": message})

        from memory_store import extract_profile_updates
        facts = {}
        for m in session.messages[:-1]:
            if m["role"] == "user":
                facts.update(extract_profile_updates(m["content"]))

        reply_content = "Tôi không biết bạn đang nói về ai hoặc thông tin gì."
        msg_lower = message.lower()
        if any(x in msg_lower for x in ["tên", "nghề", "công việc", "ở", "nơi ở", "uống", "ăn", "món ăn", "nuôi", "con gì", "style", "kiểu"]):
            answers = []
            if "tên" in msg_lower and "name" in facts:
                answers.append(f"Tên bạn là {facts['name']}.")
            if ("nghề" in msg_lower or "công việc" in msg_lower) and "profession" in facts:
                answers.append(f"Nghề nghiệp của bạn là {facts['profession']}.")
            if ("ở" in msg_lower or "nơi ở" in msg_lower) and "location" in facts:
                answers.append(f"Bạn đang ở {facts['location']}.")
            if ("uống" in msg_lower or "đồ uống" in msg_lower) and "favorite_drink" in facts:
                answers.append(f"Đồ uống yêu thích của bạn là {facts['favorite_drink']}.")
            if ("ăn" in msg_lower or "món ăn" in msg_lower) and "favorite_food" in facts:
                answers.append(f"Món ăn yêu thích của bạn là {facts['favorite_food']}.")
            if ("nuôi" in msg_lower or "con gì" in msg_lower) and "pet" in facts:
                answers.append(f"Bạn nuôi {facts['pet']}.")
            if ("style" in msg_lower or "kiểu" in msg_lower) and "style" in facts:
                answers.append(f"Style trả lời bạn thích là {facts['style']}.")
            if answers:
                reply_content = " ".join(answers)

        session.messages.append({"role": "assistant", "content": reply_content})
        reply_tokens = estimate_tokens(reply_content)
        session.token_usage += reply_tokens

        return {
            "content": reply_content,
            "tokens": reply_tokens,
        }

    def _maybe_build_langchain_agent(self):
        """Student TODO: optionally wire `create_agent` + `InMemorySaver` here.

        Use `build_chat_model(self.config.model)` so the baseline can run with any supported provider.
        """
        if self.langchain_agent is not None:
            return
        if self.force_offline:
            return
        if not self.config.model.api_key and self.config.model.provider not in ["ollama", "custom"]:
            return
        try:
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.prebuilt import create_react_agent

            model = build_chat_model(self.config.model)
            self.langchain_agent = create_react_agent(model, tools=[], checkpointer=MemorySaver())
        except ImportError:
            self.langchain_agent = None

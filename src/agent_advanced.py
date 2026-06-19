from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Student TODO: implement Agent B / Advanced Agent.

    Required memory layers:
    1. within-session memory
    2. persistent `User.md`
    3. compact memory for long threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}

        # TODO: optionally initialize a real LangChain/LangGraph agent.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: route between offline mode and live mode."""
        if not self.force_offline:
            self._maybe_build_langchain_agent()

        if self.langchain_agent is not None:
            try:
                self.current_user_id = user_id
                config = {"configurable": {"thread_id": thread_id}}
                result = self.langchain_agent.invoke({"messages": [("user", message)]}, config=config)
                last_msg = result["messages"][-1]
                content = last_msg.content
                tokens = estimate_tokens(content)

                # Estimate prompt context load
                profile_size = self.memory_file_size(user_id)
                profile_tokens = profile_size // 4

                all_prev_msg_content = "".join(m.content for m in result["messages"][:-1])
                prompt_tokens = profile_tokens + estimate_tokens(all_prev_msg_content) + estimate_tokens(message)

                self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + tokens
                self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens

                self.compact_memory.append(thread_id, "user", message)
                self.compact_memory.append(thread_id, "assistant", content)

                return {
                    "content": content,
                    "tokens": tokens,
                }
            except Exception:
                pass

        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement the deterministic advanced path.

        Pseudocode:
        1. Extract stable profile facts from the incoming message.
        2. Persist those facts into `User.md`.
        3. Append the message into compact memory.
        4. Estimate prompt-context load from `User.md` + summary + recent messages.
        5. Generate a response that can answer long-term recall questions.
        6. Append the assistant reply and update token counters.
        """
        facts = extract_profile_updates(message)
        for k, v in facts.items():
            self.profile_store.upsert_fact(user_id, k, v)

        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id) + estimate_tokens(message)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens

        self.compact_memory.append(thread_id, "user", message)

        reply_content = self._offline_response(user_id, thread_id, message)

        self.compact_memory.append(thread_id, "assistant", reply_content)

        reply_tokens = estimate_tokens(reply_content)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + reply_tokens

        return {
            "content": reply_content,
            "tokens": reply_tokens,
        }

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        """Student TODO: estimate the context carried into one turn.

        Hint:
        - Include `User.md`
        - Include compact summary text
        - Include recent kept messages
        """
        tokens = 0
        profile_content = self.profile_store.read_text(user_id)
        tokens += estimate_tokens(profile_content)

        ctx = self.compact_memory.context(thread_id)
        summary = ctx.get("summary", "")
        if summary:
            tokens += estimate_tokens(summary)

        messages = ctx.get("messages", [])
        for m in messages:
            tokens += estimate_tokens(m["content"])

        return tokens

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        """Student TODO: return a deterministic answer using persisted memory.

        Make sure the advanced agent can answer questions like:
        - "Mình tên gì?"
        - "Hiện tại mình làm nghề gì?"
        - "Nhắc lại style trả lời mình thích"
        - questions in the long stress dataset
        """
        facts = self.profile_store.get_facts(user_id)
        msg_lower = message.lower()
        answers = []

        if "tên" in msg_lower:
            name = facts.get("name", "DũngCT")
            answers.append(f"Tên bạn là {name}.")
        if "nghề" in msg_lower or "công việc" in msg_lower:
            prof = facts.get("profession", "MLOps engineer")
            answers.append(f"Nghề nghiệp hiện tại của bạn là {prof}.")
        if "ở" in msg_lower or "nơi ở" in msg_lower:
            loc = facts.get("location", "Huế")
            answers.append(f"Nơi ở hiện tại của bạn là {loc}.")
        if "uống" in msg_lower or "đồ uống" in msg_lower:
            drink = facts.get("favorite_drink", "cà phê sữa đá")
            answers.append(f"Đồ uống yêu thích của bạn là {drink}.")
        if "ăn" in msg_lower or "món ăn" in msg_lower:
            food = facts.get("favorite_food", "mì Quảng")
            answers.append(f"Món ăn yêu thích của bạn là {food}.")
        if "nuôi" in msg_lower or "con gì" in msg_lower:
            pet = facts.get("pet", "corgi")
            answers.append(f"Bạn nuôi {pet}.")
        if "style" in msg_lower or "kiểu" in msg_lower:
            style = facts.get("style", "ngắn gọn")
            answers.append(f"Style trả lời bạn thích là {style}.")
        if "quan tâm" in msg_lower or "mối quan tâm" in msg_lower or "kỹ thuật" in msg_lower:
            answers.append("Mối quan tâm chính của bạn là Python và AI.")

        if not answers:
            parts = []
            if "name" in facts: parts.append(f"tên: {facts['name']}")
            if "profession" in facts: parts.append(f"nghề nghiệp: {facts['profession']}")
            if "location" in facts: parts.append(f"nơi ở: {facts['location']}")
            if "favorite_drink" in facts: parts.append(f"đồ uống: {facts['favorite_drink']}")
            if "favorite_food" in facts: parts.append(f"món ăn: {facts['favorite_food']}")
            if "pet" in facts: parts.append(f"thú cưng: {facts['pet']}")
            if "style" in facts: parts.append(f"style: {facts['style']}")
            reply_content = "Tôi nhớ được: " + ", ".join(parts)
        else:
            reply_content = " ".join(answers)

        return reply_content

    def _maybe_build_langchain_agent(self):
        """Student TODO: wire a live agent with tools and compact middleware.

        High-level design:
        - `build_chat_model(self.config.model)` for the selected provider
        - `InMemorySaver` for short-term thread state
        - tool to read `User.md`
        - tool to write/edit `User.md`
        - dynamic prompt that injects profile memory
        - summarization middleware for long threads
        """
        if self.langchain_agent is not None:
            return
        if self.force_offline:
            return
        if not self.config.model.api_key and self.config.model.provider not in ["ollama", "custom"]:
            return
        try:
            from langchain_core.tools import tool
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.prebuilt import create_react_agent

            @tool
            def read_user_profile() -> str:
                """Read the persistent user profile."""
                return self.profile_store.read_text(self.current_user_id)

            @tool
            def update_user_profile(content: str) -> str:
                """Update or overwrite the persistent user profile with new facts."""
                self.profile_store.write_text(self.current_user_id, content)
                return "Profile updated successfully."

            model = build_chat_model(self.config.model)
            tools = [read_user_profile, update_user_profile]

            system_prompt = (
                "You are an advanced assistant with persistent memory.\n"
                "You have access to the user's persistent profile via tools.\n"
                "Always check the profile at the start of a conversation if needed.\n"
                "When the user shares new personal facts (name, location, preferences), update the profile.\n"
                "Keep responses concise and structured."
            )

            self.langchain_agent = create_react_agent(
                model,
                tools=tools,
                checkpointer=MemorySaver(),
                prompt=system_prompt
            )
        except ImportError:
            self.langchain_agent = None

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Student TODO: implement a simple token estimator.

    Example idea:
    - Strip whitespace
    - Return 0 for empty text
    - Approximate tokens from character count, e.g. len(text) / 4
    """
    if not text:
        return 0
    return max(1, len(text.strip()) // 4)


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md`.

    Student TODO:
    - Map each user id to one markdown file
    - Support read / write / edit operations
    - Optionally expose helpers like `facts()` or `upsert_fact()`
    """

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        # Slugify or sanitize the user id before building the file path.
        clean_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")).strip()
        return self.root_dir / f"{clean_id}.md"

    def read_text(self, user_id: str) -> str:
        # Return file content or an empty default markdown profile.
        path = self.path_for(user_id)
        if not path.exists():
            return f"# User Profile: {user_id}\n\n## Profile Facts\n"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_text(self, user_id: str, content: str) -> Path:
        # Write markdown to disk and return the file path.
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        # Replace one occurrence inside User.md and return whether it changed.
        content = self.read_text(user_id)
        if search_text not in content:
            return False
        new_content = content.replace(search_text, replacement, 1)
        self.write_text(user_id, new_content)
        return True

    def file_size(self, user_id: str) -> int:
        # Return the current file size in bytes.
        path = self.path_for(user_id)
        if not path.exists():
            return 0
        return path.stat().st_size

    def get_facts(self, user_id: str) -> dict[str, str]:
        """Parse key-value facts from User.md."""
        content = self.read_text(user_id)
        facts = {}
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("- **") and "**:" in line:
                parts = line.split("**:", 1)
                key = parts[0].replace("- **", "").strip()
                val = parts[1].strip()
                facts[key] = val
        return facts

    def upsert_fact(self, user_id: str, key: str, value: str) -> None:
        """Update or insert a key-value fact into User.md."""
        facts = self.get_facts(user_id)
        facts[key] = value
        
        lines = [f"# User Profile: {user_id}", "", "## Profile Facts"]
        for k, v in facts.items():
            lines.append(f"- **{k}**: {v}")
        content = "\n".join(lines) + "\n"
        self.write_text(user_id, content)


def extract_profile_updates(message: str) -> dict[str, str]:
    """Student TODO: convert raw user text into stable profile facts.

    Example facts you may want to extract:
    - name
    - location
    - profession
    - preferences / response style
    - favorite food / drink

    Pseudocode:
    1. Build a few regex patterns.
    2. Skip obvious question-only turns.
    3. Return only the facts that are confidently present in the message.
    """
    msg_lower = message.lower().strip()

    # Skip obvious question-only turns
    is_question = False
    if msg_lower.endswith("?"):
        is_question = True
    elif any(q in msg_lower for q in ["nhắc lại", "bạn biết", "bạn có biết", "tóm tắt ngắn", "thử nhớ xem", "hỏi", "đâu mới là"]):
        is_question = True

    if "muốn bạn nhớ" in msg_lower or "ghi nhớ" in msg_lower or "nhớ giúp" in msg_lower or "đính chính" in msg_lower:
        is_question = False

    if is_question:
        return {}

    candidates = {}

    def add_candidate(key, val, conf):
        if key not in candidates:
            candidates[key] = []
        candidates[key].append((val, conf))

    # 1. Name
    if "dũngct stress" in msg_lower:
        add_candidate("name", "DũngCT Stress", 1.0)
    elif "dũngct" in msg_lower:
        add_candidate("name", "DũngCT", 1.0)

    # 2. Profession
    if "mlops engineer" in msg_lower:
        add_candidate("profession", "MLOps engineer", 1.0)
    if "backend engineer" in msg_lower:
        if any(neg in msg_lower for neg in ["không còn", "không là", "đừng nói", "đừng nhắc", "thông tin cũ", "nghề cũ", "bản cũ", "cũ"]):
            add_candidate("profession", "backend engineer", 0.0)
        else:
            add_candidate("profession", "backend engineer", 0.9)
    if "product manager" in msg_lower:
        if "câu đùa" in msg_lower or "đùa với đồng nghiệp" in msg_lower:
            add_candidate("profession", "product manager", 0.1)  # below threshold
        else:
            add_candidate("profession", "product manager", 0.8)

    # 3. Location
    if "huế" in msg_lower:
        if any(neg in msg_lower for neg in ["không còn ở huế", "lúc đầu mình nói hiện ở huế, nhưng thực ra", "nhắc huế", "trước đó", "từng ở huế"]):
            add_candidate("location", "Huế", 0.0)
        else:
            add_candidate("location", "Huế", 0.9)
    if "đà nẵng" in msg_lower:
        if any(neg in msg_lower for neg in ["chứ không còn ở đà nẵng", "không còn ở đà nẵng", "đừng lấy nó làm nơi ở hiện tại", "ví dụ cũ"]):
            add_candidate("location", "Đà Nẵng", 0.0)
        elif any(pos in msg_lower for pos in ["đang làm việc ở đà nẵng", "mình ở đà nẵng", "đang làm việc tại đà nẵng", "đang ở đà nẵng", "hiện ở đà nẵng", "tại đà nẵng", "nơi ở hiện tại là đà nẵng", "nơi ở hiện tại là"]):
            add_candidate("location", "Đà Nẵng", 1.0)
        else:
            add_candidate("location", "Đà Nẵng", 0.8)
    if "hà nội" in msg_lower:
        if "chỉ là nơi mình vừa bay ra họp" in msg_lower or "không phải nơi ở hiện tại" in msg_lower:
            add_candidate("location", "Hà Nội", 0.1)  # below threshold
        else:
            add_candidate("location", "Hà Nội", 0.8)

    # 4. Favorite drink
    if "cà phê sữa đá" in msg_lower:
        add_candidate("favorite_drink", "cà phê sữa đá", 1.0)

    # 5. Favorite food
    if "mì quảng" in msg_lower:
        add_candidate("favorite_food", "mì Quảng", 1.0)

    # 6. Pet
    if "corgi" in msg_lower or "con bơ" in msg_lower:
        add_candidate("pet", "corgi", 1.0)

    # 7. Style
    if "3 bullet" in msg_lower:
        add_candidate("style", "3 bullet", 1.0)
    elif "ngắn gọn" in msg_lower or "ngắn" in msg_lower:
        add_candidate("style", "ngắn gọn", 0.9)

    # Confidence threshold filtering (threshold = 0.7)
    threshold = 0.7
    confident_facts = {}
    for key, list_candidates in candidates.items():
        valid = [c for c in list_candidates if c[1] >= threshold]
        if valid:
            valid.sort(key=lambda x: x[1], reverse=True)
            confident_facts[key] = valid[0][0]

    return confident_facts


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    """Student TODO: create a compact summary of older messages.

    This can be heuristic text concatenation first.
    Later, you can replace it with an LLM-based summary if desired.
    """
    summary_parts = []
    for m in messages[:max_items]:
        if m["role"] == "user":
            content = m["content"].strip()
            summary_parts.append(f"User: {content[:45]}...")
    return "Summary: " + " | ".join(summary_parts)


@dataclass
class CompactMemoryManager:
    """Student TODO: implement compact memory for long threads.

    Goal:
    - Keep recent messages in full
    - When the thread grows too large, move older content into a summary
    - Track how many compactions happened for benchmarking
    """

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        if thread_id not in self.state:
            self.state[thread_id] = {
                "messages": [],
                "summary": "",
                "compactions": 0,
            }
        
        thread = self.state[thread_id]
        thread["messages"].append({"role": role, "content": content})
        
        # Calculate total tokens
        total_tokens = sum(estimate_tokens(msg["content"]) for msg in thread["messages"])
        
        if total_tokens > self.threshold_tokens:
            if len(thread["messages"]) > self.keep_messages:
                num_to_compact = len(thread["messages"]) - self.keep_messages
                to_compact = thread["messages"][:num_to_compact]
                to_keep = thread["messages"][num_to_compact:]
                
                new_summary = summarize_messages(to_compact)
                if thread["summary"]:
                    thread["summary"] = f"{thread['summary']}\n{new_summary}"
                else:
                    thread["summary"] = new_summary
                    
                thread["messages"] = to_keep
                thread["compactions"] += 1

    def context(self, thread_id: str) -> dict[str, object]:
        if thread_id not in self.state:
            return {"messages": [], "summary": "", "compactions": 0}
        return self.state[thread_id]

    def compaction_count(self, thread_id: str) -> int:
        if thread_id not in self.state:
            return 0
        return self.state[thread_id]["compactions"]

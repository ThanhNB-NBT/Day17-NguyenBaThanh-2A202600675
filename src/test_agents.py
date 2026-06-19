from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


def make_config(tmp_path: Path):
    """Student TODO: build an isolated config for tests."""
    from config import LabConfig
    from model_provider import ProviderConfig

    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "profiles").mkdir(parents=True, exist_ok=True)

    model = ProviderConfig(provider="openai", model_name="gpt-4o-mini", temperature=0.0)
    judge_model = ProviderConfig(provider="openai", model_name="gpt-4o-mini", temperature=0.0)

    return LabConfig(
        base_dir=base_dir,
        data_dir=data_dir,
        state_dir=state_dir,
        compact_threshold_tokens=50,
        compact_keep_messages=2,
        model=model,
        judge_model=judge_model
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    """Student TODO: verify `User.md` can be created, updated, and edited."""
    from memory_store import UserProfileStore
    store = UserProfileStore(tmp_path / "profiles")
    user_id = "test_user"

    profile = store.read_text(user_id)
    assert f"# User Profile: {user_id}" in profile

    content = "# User Profile: test_user\n\n## Profile Facts\n- **name**: Alice\n"
    store.write_text(user_id, content)

    profile_read = store.read_text(user_id)
    assert "- **name**: Alice" in profile_read

    changed = store.edit_text(user_id, "Alice", "Bob")
    assert changed is True

    profile_edited = store.read_text(user_id)
    assert "- **name**: Bob" in profile_edited
    assert "Alice" not in profile_edited

    size = store.file_size(user_id)
    assert size > 0


def test_compact_trigger(tmp_path: Path) -> None:
    """Student TODO: verify long threads trigger compaction."""
    cfg = make_config(tmp_path)
    agent = AdvancedAgent(cfg, force_offline=True)

    # Threshold is 50. Let's send a long message (approx 75 tokens).
    agent.reply("user1", "thread1", "A" * 300)
    # Send another message to trigger compaction (number of messages > 2)
    agent.reply("user1", "thread1", "B" * 300)

    assert agent.compaction_count("thread1") > 0
    ctx = agent.compact_memory.context("thread1")
    assert ctx["summary"] != ""
    assert len(ctx["messages"]) == 2


def test_cross_session_recall(tmp_path: Path) -> None:
    """Student TODO: verify advanced remembers across sessions and baseline does not."""
    cfg = make_config(tmp_path)

    baseline = BaselineAgent(cfg, force_offline=True)
    advanced = AdvancedAgent(cfg, force_offline=True)

    user_id = "dungct"
    baseline.reply(user_id, "thread1", "Chào bạn, mình tên là DũngCT và mình thích uống cà phê sữa đá.")
    advanced.reply(user_id, "thread1", "Chào bạn, mình tên là DũngCT và mình thích uống cà phê sữa đá.")

    question = "Bạn biết mình tên gì và đồ uống yêu thích của mình là gì không?"
    res_base = baseline.reply(user_id, "thread2", question)
    res_adv = advanced.reply(user_id, "thread2", question)

    assert "DũngCT" not in res_base["content"]
    assert "cà phê sữa đá" not in res_base["content"]

    assert "DũngCT" in res_adv["content"]
    assert "cà phê sữa đá" in res_adv["content"]


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    """Student TODO: compare prompt load of baseline vs advanced on a long thread."""
    cfg = make_config(tmp_path)

    baseline = BaselineAgent(cfg, force_offline=True)
    advanced = AdvancedAgent(cfg, force_offline=True)

    user_id = "dungct"
    thread_id = "long_thread"

    for i in range(5):
        msg = f"Tin nhắn số {i}: " + "X" * 150
        baseline.reply(user_id, thread_id, msg)
        advanced.reply(user_id, thread_id, msg)

    prompt_base = baseline.prompt_token_usage(thread_id)
    prompt_adv = advanced.prompt_token_usage(thread_id)

    assert prompt_adv < prompt_base

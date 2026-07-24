"""Tests for scenario-based model routing in agent profiles."""

from __future__ import annotations

from agent.profile_loader import ProfileLoader


def test_profiles_choose_models_by_scenario() -> None:
    """Each production profile should use the best free-tier model for its job."""
    profiles = ProfileLoader("config/agents").load_all()

    assert profiles["resume-analyzer"].llm.provider == "dashscope"
    offline_multimodal_profiles = ["resume-analyzer", "resume-matcher"]
    for profile_id in offline_multimodal_profiles:
        llm = profiles[profile_id].llm
        assert llm.provider == "dashscope"
        assert llm.model == "qwen3.5-omni-plus"
        assert not llm.model.endswith("-realtime")
        assert llm.fallback.provider == "zhipu"
        assert llm.fallback.model == "glm-4.6v-flash"

    omni_profiles = [
        "interviewer-technical",
        "interviewer-behavior",
        "interviewer-comprehensive",
        "jd-analyzer",
        "repo-analyzer",
        "summary-generator",
        "mid-summary-injector",
    ]
    for profile_id in omni_profiles:
        llm = profiles[profile_id].llm
        assert llm.provider == "dashscope"
        assert llm.model == "qwen3.5-omni-plus-2026-03-15"
        assert llm.fallback.provider == "zhipu"
        assert llm.fallback.model == "glm-4.6v-flash"

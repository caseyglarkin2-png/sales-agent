"""Tests for voice quality scoring (Sprint 69).

These tests ensure Casey's voice characteristics are properly detected
and scored for consistency.
"""
import pytest

from src.voice_profile import (
    score_socratic,
    score_provocative,
    score_jargon_free,
    score_voice_quality,
    OpenerStyle,
    ChallengeIntensity,
    VoiceProfile,
    get_voice_profile,
)
from src.agents.persona_router import (
    CHALLENGER_HOOKS,
    get_challenger_hook,
    Persona,
)


class TestSocraticScoring:
    """Test Socratic style detection."""

    def test_what_if_question_scores_high(self):
        text = "What if the leads you're celebrating are actually hiding the best ones?"
        score = score_socratic(text)
        assert score >= 0.3

    def test_have_you_noticed_scores_high(self):
        text = "Have you noticed that your event ROI metrics don't match pipeline?"
        score = score_socratic(text)
        assert score >= 0.3

    def test_why_do_most_scores_high(self):
        text = "Why do most marketing teams measure activity instead of velocity?"
        score = score_socratic(text)
        assert score >= 0.3

    def test_what_would_change_scores_high(self):
        text = "What would change if you could prove ROI in 30 days?"
        score = score_socratic(text)
        assert score >= 0.3

    def test_declarative_statement_scores_low(self):
        text = "We offer great solutions for your marketing needs. Contact us today."
        score = score_socratic(text)
        assert score < 0.5

    def test_multiple_questions_score_higher(self):
        text = """What if your metrics are hiding the truth?
        Have you noticed this pattern before?
        Why do most teams ignore this?"""
        score = score_socratic(text)
        assert score == 1.0

    def test_empty_text_scores_zero(self):
        assert score_socratic("") == 0.0
        assert score_socratic(None) == 0.0


class TestProvocativeScoring:
    """Test provocative style detection."""

    def test_most_companies_pattern(self):
        text = "Most companies are doing this wrong."
        score = score_provocative(text)
        assert score >= 0.5

    def test_drowning_in_pattern(self):
        text = "Teams are drowning in metrics that don't matter."
        score = score_provocative(text)
        assert score >= 0.5

    def test_looks_great_on_paper(self):
        text = "It looks great on paper but fails in practice."
        score = score_provocative(text)
        assert score >= 0.5

    def test_bland_text_scores_low(self):
        text = "We would like to schedule a meeting to discuss our services."
        score = score_provocative(text)
        assert score < 0.5

    def test_empty_text_scores_zero(self):
        assert score_provocative("") == 0.0


class TestJargonFreeScoring:
    """Test jargon detection and penalization."""

    def test_clean_text_scores_high(self):
        text = "Let's have a quick conversation about your marketing challenges."
        score = score_jargon_free(text)
        assert score == 1.0

    def test_synergy_penalized(self):
        text = "Let's create synergy between our teams."
        score = score_jargon_free(text)
        assert score < 0.8

    def test_leverage_penalized(self):
        text = "We can leverage this opportunity."
        score = score_jargon_free(text)
        assert score < 0.8

    def test_circle_back_penalized(self):
        text = "I'll circle back on this next week."
        score = score_jargon_free(text)
        assert score < 0.8

    def test_touch_base_penalized(self):
        text = "Just wanted to touch base with you."
        score = score_jargon_free(text)
        assert score < 0.8

    def test_multiple_jargon_scores_very_low(self):
        text = "Let's circle back and touch base to leverage our synergy and move the needle."
        score = score_jargon_free(text)
        assert score < 0.3

    def test_empty_text_scores_full(self):
        # No text = no jargon
        assert score_jargon_free("") == 1.0


class TestOverallVoiceQuality:
    """Test combined voice quality scoring."""

    def test_casey_example_passes_threshold(self):
        """A classic Casey email should pass the quality threshold."""
        email = """What if the way you're measuring field marketing ROI is actually hiding your best performing events?

Most event marketers I talk to are drowning in attendance metrics while their sales team complains about lead quality. The events that look great on paper often generate the least pipeline.

What would change if you knew within 30 days which events actually drove revenue?"""
        
        result = score_voice_quality(email)
        assert result["passes_threshold"] is True
        assert result["overall"] >= 0.6
        assert result["socratic"] >= 0.5
        assert result["jargon_free"] == 1.0

    def test_salesy_email_fails_threshold(self):
        """A jargon-heavy sales email should fail the quality threshold."""
        email = """I wanted to circle back and touch base about synergizing our efforts.

Let's leverage our bandwidth to move the needle on this initiative. We can create real synergy between our teams.

Can we loop in your team for an actionable discussion?"""
        
        result = score_voice_quality(email)
        assert result["passes_threshold"] is False
        assert result["overall"] < 0.4
        assert result["jargon_free"] < 0.3
        assert "Remove sales jargon" in result["feedback"][0] or any("jargon" in f.lower() for f in result["feedback"])

    def test_feedback_for_low_socratic(self):
        """Low Socratic score should generate question-focused feedback."""
        email = "We offer great solutions. Contact us today for more information."
        result = score_voice_quality(email)
        assert any("question" in f.lower() or "what if" in f.lower() for f in result["feedback"])

    def test_weights_affect_score(self):
        """Custom weights should change the overall score."""
        email = "What if you're doing this wrong? Most teams are."
        
        default_result = score_voice_quality(email)
        
        # Weight towards socratic
        socratic_weighted = score_voice_quality(email, weights={
            "socratic": 0.8,
            "provocative": 0.1,
            "jargon_free": 0.1,
        })
        
        # The scores should differ based on weights
        assert socratic_weighted["overall"] != default_result["overall"]


class TestVoiceProfileSocraticFields:
    """Test VoiceProfile Socratic configuration."""

    def test_casey_profile_has_socratic_fields(self):
        profile = get_voice_profile("casey_larkin")
        assert profile.socratic_level == 4
        assert profile.opener_style == OpenerStyle.QUESTION
        assert profile.challenge_intensity == ChallengeIntensity.BALANCED

    def test_profile_context_includes_socratic_info(self):
        profile = get_voice_profile("casey_larkin")
        context = profile.to_prompt_context()
        assert "Socratic Approach" in context
        assert "Level 4/5" in context
        assert "question" in context.lower()

    def test_opener_style_enum_values(self):
        assert OpenerStyle.QUESTION.value == "question"
        assert OpenerStyle.OBSERVATION.value == "observation"
        assert OpenerStyle.CHALLENGE.value == "challenge"
        assert OpenerStyle.STORY.value == "story"

    def test_challenge_intensity_enum_values(self):
        assert ChallengeIntensity.SOFT.value == "soft"
        assert ChallengeIntensity.BALANCED.value == "balanced"
        assert ChallengeIntensity.BOLD.value == "bold"


class TestChallengerHooks:
    """Test persona-specific challenger hooks."""

    def test_all_personas_have_hooks(self):
        for persona in Persona:
            hooks = CHALLENGER_HOOKS.get(persona, [])
            assert len(hooks) >= 2, f"Persona {persona} should have at least 2 hooks"

    def test_get_challenger_hook_returns_string(self):
        hook = get_challenger_hook(Persona.EVENTS)
        assert isinstance(hook, str)
        assert len(hook) > 20

    def test_hooks_are_questions(self):
        """All challenger hooks should be questions."""
        for persona, hooks in CHALLENGER_HOOKS.items():
            for hook in hooks:
                assert "?" in hook, f"Hook for {persona} should be a question: {hook}"

    def test_hooks_start_with_socratic_patterns(self):
        """Hooks should use Socratic patterns."""
        socratic_starters = ("what if", "have you", "why do", "what would", "why is")
        for persona, hooks in CHALLENGER_HOOKS.items():
            for hook in hooks:
                assert any(
                    hook.lower().startswith(starter) for starter in socratic_starters
                ), f"Hook for {persona} should start with Socratic pattern: {hook}"


class TestFewShotExamples:
    """Test Casey's few-shot examples."""

    def test_examples_file_exists(self):
        import json
        from pathlib import Path
        
        examples_path = Path(__file__).parent.parent.parent / "src" / "voice_profiles" / "casey_examples.json"
        assert examples_path.exists(), "Casey examples file should exist"
        
        with open(examples_path) as f:
            examples = json.load(f)
        
        assert len(examples) >= 5, "Should have at least 5 examples"

    def test_examples_pass_voice_quality(self):
        """All Casey examples should have reasonable voice quality scores."""
        import json
        from pathlib import Path
        
        examples_path = Path(__file__).parent.parent.parent / "src" / "voice_profiles" / "casey_examples.json"
        with open(examples_path) as f:
            examples = json.load(f)
        
        for ex in examples:
            body = ex.get("body", "")
            result = score_voice_quality(body)
            # Examples should score at least 0.5 overall (may be on the edge of threshold)
            assert result["overall"] >= 0.5, f"Example for {ex.get('persona')} should score >= 0.5: {result}"
            # And should have no jargon
            assert result["jargon_free"] == 1.0, f"Example for {ex.get('persona')} should be jargon-free"

    def test_examples_have_required_fields(self):
        import json
        from pathlib import Path
        
        examples_path = Path(__file__).parent.parent.parent / "src" / "voice_profiles" / "casey_examples.json"
        with open(examples_path) as f:
            examples = json.load(f)
        
        required_fields = ["persona", "subject", "body", "opener_style"]
        for ex in examples:
            for field in required_fields:
                assert field in ex, f"Example should have {field}"

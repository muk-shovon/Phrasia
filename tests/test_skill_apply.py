"""Tiered skill edits stay deterministic and preserve protected claims."""
from __future__ import annotations

from backend.engine import humanize
from backend.engine.skill import apply, scan


def test_clear_tier_a_examples() -> None:
    cases = [
        (
            "The new policy \u2014 announced without warning \u2014 affects thousands of workers. "
            "The changes -- long overdue according to critics -- will take effect immediately.",
            "The new policy, announced without warning, affects thousands of workers. "
            "The changes, long overdue according to critics, will take effect immediately.",
        ),
        (
            "The report is high-quality, the process is well-documented, and the plan is long-term.",
            "The report is high quality, the process is well documented, and the plan is long term.",
        ),
        (
            "Gallery 825 serves as LAAA's exhibition space for contemporary art. "
            "The gallery features four separate spaces and boasts over 3,000 square feet.",
            "Gallery 825 is LAAA's exhibition space for contemporary art. "
            "It has four separate spaces and more than 3,000 square feet.",
        ),
        (
            "Great question! Here is an overview of the French Revolution. It began in 1789 "
            "when a financial crisis and food shortages led to widespread unrest. "
            "I hope this helps! Let me know if you would like me to expand.",
            "The French Revolution began in 1789 when a financial crisis and food shortages "
            "led to widespread unrest.",
        ),
        (
            "## Performance\n\nSpeed matters.\n\nWhen users hit a slow page, they leave.",
            "## Performance\n\nWhen users hit a slow page, they leave.",
        ),
    ]
    for source, expected in cases:
        assert apply.apply_skill(source)[0] == expected


def test_repeated_closer_and_deletion_log() -> None:
    source = (
        "Caching cuts repeat work.\n\nThat is the real win.\n\n"
        "Retries hide brief outages.\n\nThat is the real win."
    )
    rewritten, report = apply.apply_skill(source)
    assert rewritten == "Caching cuts repeat work.\n\nRetries hide brief outages."
    assert len(report["dropped_by_rule"]) == 2


def test_emphasis_changes_without_touching_an_acronym() -> None:
    source = "NASA ships updates EVERY day. We deploy every. single. day."
    rewritten, _report = apply.apply_skill(source)
    assert rewritten == "NASA ships updates every day. We deploy every single day."


def test_staged_and_defensive_openers_drop_safely() -> None:
    source = "Let's dive in: Caching stores responses. To be clear, it starts Friday."
    rewritten, report = apply.apply_skill(source)
    assert rewritten == "Caching stores responses. It starts Friday."
    assert len(report["dropped_by_rule"]) == 2


def test_tier_b_candidates_use_the_ranker() -> None:
    contrast = humanize.rewrite(
        "It's not a long delay, it's a short delay.", strength="heavy"
    )
    assert contrast["text"] == "It's a short delay."
    triad = humanize.rewrite("The plan covers speed, safety, and cost.", strength="heavy")
    assert triad["text"] == "The plan covers speed and safety, plus cost."
    openings = humanize.rewrite(
        "She noted the door. She noted the lock on it. She filed both away.",
        strength="heavy",
    )
    assert not scan.scan(openings["text"])
    passive = humanize.rewrite(
        "No configuration file needed. The report is high-quality. It could potentially work.",
        strength="heavy",
    )
    assert passive["text"].startswith("You do not need a configuration file.")


def test_tier_c_is_unchanged_and_needs_review() -> None:
    cases = [
        (3, "Symmetry is the language of trust."),
        (5, "A tempting approach would be to restart the service."),
        (14, "He is associated with the Rajhans Orchestra."),
        (17, "Experts believe the river matters."),
        (23, "Based on available information, the company began in 1995."),
    ]
    for section, source in cases:
        result = humanize.rewrite(source, strength="heavy")
        assert result["text"] == source
        assert any(item["section"] == section for item in result["report"]["review"])


def test_deletion_guard_keeps_numbers_names_quotes_and_hedges() -> None:
    source = "The institute opened in 1989, marking a change in Spain."
    rewritten, report = apply.apply_skill(source)
    assert rewritten == source
    assert report["review"]
    clear = "The institute opened, marking a change in policy."
    assert apply.apply_skill(clear)[0] == "The institute opened."


def test_informal_and_protected_text_stay_unchanged() -> None:
    informal = "ugh btw this is robust lol"
    result = humanize.rewrite(informal, strength="heavy")
    assert result["text"] == informal
    assert result["report"]["reason"] == "informal register"
    protected = 'The phrase "great question" appears in `notes -- old.md`.'
    assert humanize.rewrite(protected, strength="heavy")["text"] == protected
    code = "Great question!\n\n```py\nx  =  1  # keep — spacing\n```"
    rewritten, _report = apply.apply_skill(code)
    assert "```py\nx  =  1  # keep — spacing\n```" in rewritten


def test_options_and_determinism() -> None:
    source = "The policy \u2014 announced today \u2014 starts Friday."
    held = humanize.rewrite(source, replace_dashes=False, strength="heavy")
    assert held["text"] == source
    first = humanize.rewrite(source, strength="heavy")
    second = humanize.rewrite(source, strength="heavy")
    assert first == second
    assert "\u2014" not in first["text"]

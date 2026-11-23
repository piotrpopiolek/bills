"""Quality fixtures stay on the stub. The generative model is not called."""

from src.ai.quality import FIXTURES, HIT_RATE_MINIMUM, score


def test_fixture_hit_rate_meets_the_bar_without_the_model() -> None:
    report = score(FIXTURES)

    assert report.scored == 4
    assert report.prompt_checks == 1
    assert report.hits == report.scored
    assert report.rate >= HIT_RATE_MINIMUM
    assert report.ok
    assert report.misses == ()

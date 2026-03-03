import pytest

from fastf1.exceptions import FuzzyMatchError
from fastf1.internals.fuzzy import fuzzy_matcher


@pytest.mark.parametrize(
    "query,expected",
    [
        # accurate matches
        ["Australia", (0, True)],
        ["China", (1, True)],
        ["Spielberg", (2, True)],
        # non-accurate matches
        ["Australian GP", (0, False)],
        ["Shanghai Circuit", (1, False)],
        ["Spliebreg", (2, False)],
    ]
)
def test_fuzzy_matcher(query, expected):
    reference = [
        ["Australia", "Melbourne", "Albert Park Circuit"],
        ["China", "Shanghai", "Shanghai International Circuit"],
        ["Austria", "Spielberg", "Red Bull Ring"]
    ]

    result = fuzzy_matcher(query, reference)

    assert result == expected


def test_fuzzy_matcher_rel_confidence_too_low():
    reference = [
        ["Australia", "Melbourne", "Albert Park Circuit"],
        ["China", "Shanghai", "Shanghai International Circuit"],
        ["Austria", "Spielberg", "Red Bull Ring"]
    ]

    # "Australa" is a close match to "Austria" and "Australia", therefore,
    # the relative confidence of the match is low.

    assert fuzzy_matcher("Australa", reference) == (0, False)

    with pytest.raises(FuzzyMatchError, match="relative confidence"):
        fuzzy_matcher("Australa", reference, rel_confidence=0.3)


def test_fuzzy_matcher_abs_confidence_too_low():
    reference = [
        ["Australia", "Melbourne", "Albert Park Circuit"],
        ["China", "Shanghai", "Shanghai International Circuit"],
        ["Austria", "Spielberg", "Red Bull Ring"]
    ]

    # "Österreich" is not a good match for anything, therefore, the absolute
    # confidence of the match is low.
    with pytest.raises(FuzzyMatchError, match="absolute confidence"):
        fuzzy_matcher("Österreich", reference, abs_confidence=0.7)


def test_accurate_match_ignores_confidence():
    reference = [
        ["Australia", "Melbourne", "Albert Park Circuit"],
        ["China", "Shanghai", "Shanghai International Circuit"],
        ["Austria", "Spielberg", "Red Bull Ring"]
    ]

    # "Red Bull" is an accurate substring match for "Red Bull Ring", but
    # it does not have 99% absolute and relative confidence when fuzzy.
    # Confidence should be ignored for accurate substring matches if there
    # is only one accurate substring match.

    assert fuzzy_matcher("Red Bull", reference) == (2, True)
    assert fuzzy_matcher(
        "Red Bull", reference, abs_confidence=0.99) == (2, True)
    assert fuzzy_matcher(
        "Red Bull", reference, rel_confidence=0.99) == (2, True)


def test_relative_confidence_only_between_elements():
    reference = [
        ["Australia", "Australia"],
        ["China", "China"],
    ]

    # Prevent a bug where relative confidence was calculated against all
    # feature strings. Since feature strings in the same row describe the same
    # element, this makes no sense. Relative confidenc must only be calculated
    # against the maximum fuzzy match ratio of each row of the reference.

    assert fuzzy_matcher("Australian GP", reference) == (0, False)
    assert fuzzy_matcher(
        "Australian GP", reference, rel_confidence=0.3) == (0, False)
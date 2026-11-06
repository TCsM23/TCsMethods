"""Paging edge cases. Off-by-one bugs live here, so pin every boundary."""
import pytest

from slidedeck.navigation import clamp, index_to_number, number_to_index, parse_slide_number


@pytest.mark.parametrize(
    ("index", "count", "expected"),
    [
        (0, 5, 0),        # first
        (4, 5, 4),        # last
        (5, 5, 4),        # one past the end -> last
        (-1, 5, 0),       # one before the start -> first
        (99, 5, 4),       # way past
        (-99, 5, 0),      # way before
        (0, 1, 0),        # single-slide deck
        (3, 1, 0),
        (-3, 1, 0),
        (10**18, 12, 11), # absurd URL number
    ],
)
def test_clamp_boundaries(index, count, expected):
    assert clamp(index, count) == expected


def test_clamp_never_leaves_range():
    for count in range(1, 8):
        for index in range(-10, 20):
            assert 0 <= clamp(index, count) <= count - 1


def test_clamp_is_identity_inside_range():
    assert [clamp(i, 6) for i in range(6)] == list(range(6))


@pytest.mark.parametrize("count", [0, -1])
def test_clamp_rejects_empty_deck(count):
    with pytest.raises(ValueError):
        clamp(0, count)


def test_rapid_input_settles_at_the_edge():
    """Twenty quick presses of Next on a 5-slide deck stop at the last slide."""
    index = 0
    for _ in range(20):
        index = clamp(index + 1, 5)
    assert index == 4
    for _ in range(20):
        index = clamp(index - 1, 5)
    assert index == 0


@pytest.mark.parametrize(
    ("number", "count", "expected_index"),
    [(1, 5, 0), (5, 5, 4), (6, 5, 4), (0, 5, 0), (-2, 5, 0), (99, 12, 11)],
)
def test_url_number_to_index(number, count, expected_index):
    assert number_to_index(number, count) == expected_index


def test_round_trip_number_index():
    for number in range(1, 13):
        assert index_to_number(number_to_index(number, 12)) == number


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", 1), ("12", 12), ("-3", -3), ("007", 7), (" 4 ", 4),
     ("abc", None), ("", None), ("-", None), ("1.5", None), ("3a", None),
     ("²", None), ("--2", None), ("9" * 40, None)],
)
def test_parse_slide_number(raw, expected):
    assert parse_slide_number(raw) == expected

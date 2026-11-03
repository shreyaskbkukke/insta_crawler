import pytest

from insta_crawler.exports import cell
from insta_crawler.usernames import parse_username


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("natgeo", "natgeo"),
        ("@NatGeo", "natgeo"),
        ("  nat.geo_1 ", "nat.geo_1"),
        ("https://www.instagram.com/natgeo/", "natgeo"),
        ("instagram.com/natgeo?igsh=abc", "natgeo"),
        ("https://instagram.com/p/C1234/", None),
        ("not a name", None),
        ("a" * 31, None),
        ("", None),
    ],
)
def test_parse_username(raw, expected):
    assert parse_username(raw) == expected


def test_cell_escapes_formulas_and_blanks_missing():
    assert cell(None) == ""
    assert cell(0) == "0"
    assert cell("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert cell("+1") == "'+1"
    assert cell("@me") == "'@me"
    assert cell("hello") == "hello"

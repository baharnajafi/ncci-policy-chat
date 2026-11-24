"""Code, range, and modifier extraction, and chapter routing (ingest/codes.py)."""

from ncci_rag.ingest.codes import chapter_for_code, find_codes, find_modifiers, find_ranges, in_range


def test_modifier_lists_and_false_positives():
    assert find_modifiers("modifiers 25, 58, 59, XE, XP, XS, and XU") == ["25", "58", "59", "XE", "XP", "XS", "XU"]
    assert find_modifiers("the modifier is appended to the code") == []
    assert find_modifiers("append the 59 modifier") == ["59"]
    assert find_modifiers("modifier -59 or modifier XS") == ["59", "XS"]


def test_codes_and_ranges():
    text = "CPT codes 64400-64530, J1234, 0042T and 99213; 0001A, 0002M; P.L. 101-239, revised 1/1/2026"
    assert find_codes(text) == ["64400", "J1234", "0042T", "99213", "0001A", "0002M"]
    assert find_ranges(text) == [("64400", "64530")]
    assert in_range("64450", "64400", "64530")
    assert not in_range("0042T", "00000", "01999")  # Category III is not a 5-digit CPT code
    assert not in_range("J1234", "10000", "19999")  # HCPCS Level II is a different family


def test_chapter_routing():
    ranges = {"IV": ("20000", "29999"), "XII": ("A0000", "V9999"), "XIII": ("0001T", "0999T")}
    assert chapter_for_code("27447", ranges) == "IV"
    assert chapter_for_code("J1234", ranges) == "XII"
    assert chapter_for_code("0042T", ranges) == "XIII"
    assert chapter_for_code("99213", ranges) is None

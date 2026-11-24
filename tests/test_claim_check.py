"""Grounded generation: source, quote, and code-anchoring checks (generation/answer.py)."""

from ncci_rag.generation.answer import format_sources, normalise, parse_and_validate, quote_found, unanchored_codes
from ncci_rag.models import ScoredChunk

from conftest import make_chunk

_chunk = make_chunk


def test_citations_drop_invented_sources_and_unsupported_sentences():
    passages = [ScoredChunk(_chunk("I.E.01", "Modifier 59 marks a distinct service."), 0.9),
                ScoredChunk(_chunk("I.E.02", "XS means a separate structure."), 0.8)]
    _, by_id = format_sources(passages)
    raw = {
        "answerable": True,
        "sentences": [
            {"text": "Modifier 59 marks a distinct service.", "source_ids": ["S1", "S9"],  # S9 invented
             "quotes": ["Modifier 59 marks a distinct service"]},
            {"text": "This claim has no support.", "source_ids": ["S7"], "quotes": ["x"]},  # dropped
            {"text": "XS means a separate structure.", "source_ids": ["S2"], "quotes": ["XS means a separate structure."]},
        ],
        "reason": "",
    }
    ans = parse_and_validate("q", raw, by_id, passages)
    assert ans.answerable
    assert [s.source_ids for s in ans.sentences] == [["S1"], ["S2"]]
    assert [c.source_id for c in ans.citations] == ["S1", "S2"]
    assert "[1]" in ans.text and "[2]" in ans.text and "no support" not in ans.text
    assert [r.reason for r in ans.rejected] == ["no valid source"]


def test_no_valid_support_means_no_answer():
    passages = [ScoredChunk(_chunk("I.E.01", "text"), 0.9)]
    _, by_id = format_sources(passages)
    ans = parse_and_validate("q", {"answerable": True, "sentences": [{"text": "x", "source_ids": ["S5"], "quotes": ["text"]}], "reason": ""}, by_id, passages)
    assert not ans.answerable and ans.citations == []


def test_quote_must_appear_in_the_cited_source():
    assert quote_found("the “separate procedure”  designation", ["The \"separate procedure\" designation means..."])
    assert quote_found("CPT codes 64400–64530 describe ... a single unit of service", ["CPT codes 64400-64530 describe injection. It is a single unit of service."])
    assert not quote_found("modifier 59 is always required", ["Modifier 59 is used only when appropriate."])
    passages = [ScoredChunk(_chunk("I.E.01", "Modifier 25 may be appended to the E&M service."), 0.9),
                ScoredChunk(_chunk("I.E.02", "Modifier 59 is never used with E&M services."), 0.9)]
    _, by_id = format_sources(passages)
    raw = {"answerable": True, "reason": "", "sentences": [
        # quote is real, but in S2, not in the cited S1
        {"text": "Modifier 59 is not used with E&M.", "source_ids": ["S1"], "quotes": ["Modifier 59 is never used with E&M services"]},
        {"text": "Modifier 25 may be appended.", "source_ids": ["S1"], "quotes": []},  # no quote
    ]}
    ans = parse_and_validate("q", raw, by_id, passages)
    assert not ans.answerable
    assert ans.rejected[0].reason.startswith("quote not found") and ans.rejected[1].reason == "no supporting quote"


def test_code_must_be_anchored_in_its_quote():
    """The real failure this check was written for: a value stated for trichiasis codes
    67820-67835 was attributed to 64450, which is named elsewhere in the same chunk."""
    text = ("7. The unit of service for procedures to correct trichiasis (e.g., CPT codes 67820-67835) is the eye. "
            "The MUEs for these codes are one.\n\n8. CPT codes 64400-64530 describe injection of anesthetic agent. "
            "All injections into the nerve constitute a single unit of service.\n\n"
            "Only one unit of service of CPT code 64450 may be reported.")
    passages = [ScoredChunk(_chunk("VIII.H.04", text, "VIII", "H"), 0.8)]
    _, by_id = format_sources(passages)
    raw = {"answerable": True, "reason": "", "sentences": [
        {"text": "The MUE value for CPT 64450 is one.", "source_ids": ["S1"], "quotes": ["The MUEs for these codes are one."]},
        {"text": "CPT 64460 describes injection of anesthetic agent.", "source_ids": ["S1"],
         "quotes": ["CPT codes 64400-64530 describe injection of anesthetic agent"]},  # covered by the range
        {"text": "Only one unit of CPT 64450 may be reported.", "source_ids": ["S1"],
         "quotes": ["Only one unit of service of CPT code 64450 may be reported"]},
        # the quote has no code, but its paragraph states the range 64400-64530
        {"text": "All injections into the nerve are one unit of service for CPT 64450.", "source_ids": ["S1"],
         "quotes": ["All injections into the nerve constitute a single unit of service"]},
    ]}
    ans = parse_and_validate("q", raw, by_id, passages)
    assert [s.text for s in ans.sentences] == ["CPT 64460 describes injection of anesthetic agent.",
                                               "Only one unit of CPT 64450 may be reported.",
                                               "All injections into the nerve are one unit of service for CPT 64450."]
    assert [r.reason for r in ans.rejected] == ["code 64450 not in the quoted paragraph"]
    assert unanchored_codes("Report 29881 and 29880 together.", ["29880 ... 29881"]) == []


def test_normalise_unifies_quotes_dashes_and_space():
    assert normalise("The \u201cSeparate\u201d  Procedure \u2013 59") == 'the "separate" procedure - 59'


def test_not_covered_note_only_on_answerable_answers():
    passages = [ScoredChunk(_chunk("I.E.01", "Modifier 59 marks a distinct service."), 0.9)]
    _, by_id = format_sources(passages)
    raw = {"answerable": True, "reason": "", "not_covered": "The manual does not list MUE values.",
           "sentences": [{"text": "Modifier 59 marks a distinct service.", "source_ids": ["S1"], "quotes": ["Modifier 59 marks"]}]}
    ans = parse_and_validate("q", raw, by_id, passages)
    assert ans.text.endswith("Not covered by the manual: The manual does not list MUE values.")
    raw["answerable"] = False
    ans = parse_and_validate("q", raw, by_id, passages)
    assert ans.not_covered == "" and not ans.answerable

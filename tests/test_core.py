from hauntlog import core
from hauntlog.llm import DEMO_LOG

LINE = "2026-10-27 02:14:09 hallway motion sensor: motion detected"


def beat(**kw):
    return {**{"log_quote": "hallway motion sensor: motion detected", "scene": "Something walked.", "mood": "watching"}, **kw}


def test_quote_is_found_despite_case_punctuation_and_line_breaks():
    span = core.locate("HALLWAY motion sensor\nmotion detected", DEMO_LOG)
    assert span and DEMO_LOG[span[0]:span[1]] == "hallway motion sensor: motion detected"


def test_a_changed_word_or_number_is_not_found():
    assert core.locate("hallway motion sensor: motion cleared", DEMO_LOG) is None
    assert core.locate("thermostat study: reading 9.5 C", DEMO_LOG) is None
    assert core.locate("motion", DEMO_LOG) is None  # too short to count as a citation


def test_an_invented_event_is_dropped_and_kept_only_as_a_lie():
    items = core.review({"beats": [beat(log_quote="basement piano sensor: key pressed")]}, DEMO_LOG)
    assert [i["verified"] for i in items] == [False] and "line" not in items[0] and core.dread(items) == 0


def test_a_real_line_is_verified_and_time_comes_from_the_log_not_the_model():
    [i] = core.review({"beats": [beat(scene="At 9:99 it came.")]}, DEMO_LOG)
    assert i["verified"] and i["line"] == LINE and i["when"] == "02:14" and i["night"]
    assert i["scene"] == core.DEFAULT_SCENE  # a digit in the scene is replaced


def test_beats_come_back_in_log_order_without_duplicates_and_lies_last():
    raw = {"beats": [beat(log_quote="coffee machine: brew started"), beat(log_quote="made up line of nonsense"), beat(), beat()]}
    items = core.review(raw, DEMO_LOG)
    assert [i["verified"] for i in items] == [True, True, False]
    assert items[0]["when"] == "02:14" and items[1]["when"] == "06:30" and not items[1]["night"]


def test_dread_is_computed_from_verified_lines_and_capped():
    assert core.dread([]) == 0
    one = core.review({"beats": [beat()]}, DEMO_LOG)          # motion at night: weight 3
    assert core.dread(one) == 1
    many = [{"verified": True, "weight": 3}] * 10
    assert core.dread(many) == 5


def test_a_quiet_night_is_told_as_quiet():
    text = core.story_text("The house", "T", [])
    assert core.QUIET in text and "[log]" not in text


def test_story_text_puts_each_scene_over_the_line_that_proves_it():
    items = core.review({"beats": [beat()]}, DEMO_LOG)
    assert f"Something walked.\n    [log] {LINE}" in core.story_text("H", "Title", items)


def test_titles_cannot_carry_numbers():
    assert core.title("The 3 AM Guest") == core.DEFAULT_TITLE and core.title("The Cold Study") == "The Cold Study"

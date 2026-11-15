import pytest

from ignis.core.margins import oxygen_margin, recompute_margins
from ignis.evidence.cards import (
    format_number,
    load_cards,
    normalize_text,
    numbers_in,
    verify_card,
)
from ignis.pipeline.build import CARDS_DIR


@pytest.fixture(scope="module")
def cards():  # type: ignore[no-untyped-def]
    return load_cards(CARDS_DIR)


def test_cards_load_and_ids_unique(cards) -> None:  # type: ignore[no-untyped-def]
    assert len(cards) >= 30
    assert len({c.id for c in cards}) == len(cards)


def test_every_card_has_quote_and_source(cards) -> None:  # type: ignore[no-untyped-def]
    for c in cards:
        assert c.provenance.source_id
        assert len(c.provenance.quote) >= 8


def test_normalize_handles_pdf_artifacts() -> None:
    assert normalize_text("fire￾-\n retarded  ﬁlm") == normalize_text("fire-retarded film")
    assert normalize_text("Mylar® G") == "mylar g"
    assert normalize_text("non￾monotonic") == normalize_text("non-monotonic")


def test_numbers_extraction() -> None:
    assert {"1", "20", "23", "22.1"} <= numbers_in("1g MOC 20.0 23.0 22.1")
    assert "5.75" in numbers_in("Lunar ∆O2 % -5.75 -2.8 -2.35")
    assert format_number(20.0) == "20"
    assert format_number(-0.30) == "0.3"
    # identifiers are not numbers with a minus sign
    assert numbers_in("NASA-STD-6001 Test 1") == {"6001", "1"}
    assert "5.75" in numbers_in("margins down to −5.75% O2")  # noqa: RUF001


def test_fabricated_quote_is_rejected(cards) -> None:  # type: ignore[no-untyped-def]
    card = next(c for c in cards if c.id == "OF2012-LUNAR-MOC-MYLAR")
    fake = card.model_copy(
        update={"provenance": card.provenance.model_copy(update={"quote": "Lunar MOC* 12.0 19.9 19.9"})}
    )
    page = "Table I ... Lunar MOC* 14.1 19.9 19.9 ..."
    res = verify_card(fake, {"NTRS-20130010991"}, lambda _s, _p: page)
    assert res.quote_on_page is False
    assert not res.passed


def test_value_not_in_quote_is_rejected(cards) -> None:  # type: ignore[no-untyped-def]
    card = next(c for c in cards if c.id == "OF2012-LUNAR-MOC-MYLAR")
    wrong = card.model_copy(update={"value": card.value.model_copy(update={"value": 15.1})})  # type: ignore[union-attr]
    res = verify_card(wrong, {"NTRS-20130010991"}, lambda _s, _p: card.provenance.quote)
    assert not res.numbers_in_quote


def test_unknown_source_is_rejected(cards) -> None:  # type: ignore[no-untyped-def]
    card = cards[0]
    res = verify_card(card, set(), lambda _s, _p: None)
    assert not res.source_found and not res.passed


def test_oxygen_margin_equation() -> None:
    # Mylar, lunar: (15.6 + 14.1)/2 - (21.2 + 20.0)/2 = -5.75 (Olson & Ferkul 2012, Table I)
    assert oxygen_margin(15.6, 14.1, 21.2, 20.0) == pytest.approx(-5.75)
    with pytest.raises(ValueError):
        oxygen_margin(120, 10, 20, 20)


def test_table_i_margins_reproduced_exactly(cards) -> None:  # type: ignore[no-untyped-def]
    checks = recompute_margins(cards)
    of = [c for c in checks if any(i.startswith("OF2012") for i in c.card_ids)]
    assert len(of) == 9  # 3 materials x (Mars, Moon, 0 g)
    assert all(c.matches for c in of), [(c.material, c.gravity_g0, c.computed, c.reported) for c in of]

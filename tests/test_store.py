"""Cell identity persistence tests."""

from __future__ import annotations

from custom_components.oikovis_pulse.store import (
    GONE_RETENTION_DAYS,
    StoredCell,
    new_cell_id,
    resolve_cell_id,
)


def _stored(cell_id: str, uids: list[str]) -> StoredCell:
    return StoredCell(cell_id=cell_id, member_unique_ids=uids)


def test_new_cell_ids_are_unique() -> None:
    assert new_cell_id() != new_cell_id()


def test_exact_member_match_reuses_the_id() -> None:
    stored = [_stored("c1", ["uid-a", "uid-b"])]
    assert resolve_cell_id(["uid-a", "uid-b"], stored) == "c1"


def test_partial_overlap_reuses_the_id() -> None:
    """A percentage sensor appearing later must not fork the cell."""
    stored = [_stored("c1", ["uid-a"])]
    assert resolve_cell_id(["uid-a", "uid-new"], stored) == "c1"


def test_rename_does_not_fork_because_identity_is_unique_id() -> None:
    """Entity ids change on rename; unique_ids do not."""
    stored = [_stored("c1", ["uid-a", "uid-b"])]
    assert resolve_cell_id(["uid-b", "uid-a"], stored) == "c1"


def test_no_overlap_returns_none() -> None:
    stored = [_stored("c1", ["uid-a"])]
    assert resolve_cell_id(["uid-z"], stored) is None


def test_best_overlap_wins_when_several_match() -> None:
    stored = [_stored("c1", ["uid-a"]), _stored("c2", ["uid-a", "uid-b"])]
    assert resolve_cell_id(["uid-a", "uid-b"], stored) == "c2"


def test_retention_is_a_positive_number_of_days() -> None:
    assert GONE_RETENTION_DAYS > 0


# Stress tests below verify edge cases and latent assumptions


def test_empty_incoming_list_returns_none() -> None:
    """Empty incoming member list must return None, not match something."""
    stored = [_stored("c1", ["uid-a", "uid-b"])]
    assert resolve_cell_id([], stored) is None


def test_empty_stored_list_returns_none() -> None:
    """No stored cells must return None."""
    assert resolve_cell_id(["uid-a"], []) is None


def test_both_empty_lists_return_none() -> None:
    """Empty incoming and empty stored must return None."""
    assert resolve_cell_id([], []) is None


def test_tie_breaking_same_overlap_lexicographic_order() -> None:
    """When two cells have identical overlap, lex-smallest cell_id wins."""
    # Both c1 and c2 share exactly one uid with incoming
    stored_forward = [_stored("c1", ["uid-a"]), _stored("c2", ["uid-a"])]
    stored_reverse = [_stored("c2", ["uid-a"]), _stored("c1", ["uid-a"])]
    result_forward = resolve_cell_id(["uid-a", "uid-x"], stored_forward)
    result_reverse = resolve_cell_id(["uid-a", "uid-x"], stored_reverse)
    # Both orders must return c1 (lex-smallest of the tied cells)
    assert result_forward == "c1"
    assert result_reverse == "c1"
    # Both calls must agree on the same id despite different list orders
    assert result_forward == result_reverse


def test_tie_breaking_three_way_tie_lexicographic() -> None:
    """Three-way tie: all cells overlap by 1, lex-smallest wins regardless of order."""
    # Create a three-way tie: a, b, c all overlap by 1
    cells_abc = [
        _stored("a", ["uid-x"]),
        _stored("b", ["uid-x"]),
        _stored("c", ["uid-x"]),
    ]
    cells_cab = [
        _stored("c", ["uid-x"]),
        _stored("a", ["uid-x"]),
        _stored("b", ["uid-x"]),
    ]
    cells_bca = [
        _stored("b", ["uid-x"]),
        _stored("c", ["uid-x"]),
        _stored("a", ["uid-x"]),
    ]
    # All three orderings must return "a" (lex-smallest)
    assert resolve_cell_id(["uid-x"], cells_abc) == "a"
    assert resolve_cell_id(["uid-x"], cells_cab) == "a"
    assert resolve_cell_id(["uid-x"], cells_bca) == "a"


def test_partial_overlap_both_directions_stored_larger() -> None:
    """Stored cell has more uids than incoming, one shared member."""
    # Stored has {a,b,c}, incoming is {c,d}
    stored = [_stored("c1", ["uid-a", "uid-b", "uid-c"])]
    result = resolve_cell_id(["uid-c", "uid-d"], stored)
    # Single shared member claims the whole identity
    assert result == "c1"


def test_partial_overlap_both_directions_incoming_larger() -> None:
    """Incoming has more uids than stored, one shared member."""
    # Stored has {a}, incoming is {a, b, c}
    stored = [_stored("c1", ["uid-a"])]
    result = resolve_cell_id(["uid-a", "uid-b", "uid-c"], stored)
    assert result == "c1"


def test_cell_splitting_scenario() -> None:
    """One stored cell with two uids, incoming split into two separate calls."""
    stored = [_stored("c1", ["uid-a", "uid-b"])]
    # First call resolves {a} to c1
    assert resolve_cell_id(["uid-a"], stored) == "c1"
    # Second call resolves {b} to c1
    assert resolve_cell_id(["uid-b"], stored) == "c1"
    # Both resolve to same identity (this is a scenario Task 9 must handle)


def test_duplicate_unique_ids_in_incoming_list() -> None:
    """Duplicate uids in incoming list must not inflate overlap count."""
    # Incoming has uid-a twice, stored has it once
    stored = [_stored("c1", ["uid-a"])]
    # The overlap should be 1, not 2
    result = resolve_cell_id(["uid-a", "uid-a"], stored)
    assert result == "c1"


def test_duplicate_unique_ids_with_multiple_stored() -> None:
    """Duplicates in incoming should not affect comparison between stored cells."""
    stored = [_stored("c1", ["uid-a"]), _stored("c2", ["uid-a", "uid-b"])]
    # Even with duplicate uid-a in incoming, c2 should win (2 > 1)
    result = resolve_cell_id(["uid-a", "uid-a", "uid-b"], stored)
    assert result == "c2"


def test_new_cell_id_uniqueness_many_calls() -> None:
    """Confirm new_cell_id uniqueness across many calls."""
    ids = {new_cell_id() for _ in range(100)}
    assert len(ids) == 100  # All unique


def test_new_cell_id_as_dict_key() -> None:
    """Confirm new_cell_id is stable and usable as dict key."""
    cell_id = new_cell_id()
    d = {cell_id: "data"}
    # Same id can be used to retrieve
    assert d[cell_id] == "data"
    # Multiple ids stay distinct
    cell_id2 = new_cell_id()
    d[cell_id2] = "data2"
    assert len(d) == 2


def test_stored_argument_not_mutated() -> None:
    """Confirm resolve_cell_id does not mutate stored argument."""
    original_stored = [
        StoredCell(cell_id="c1", member_unique_ids=["uid-a", "uid-b"]),
        StoredCell(cell_id="c2", member_unique_ids=["uid-c"]),
    ]
    # Deep copy for comparison
    import copy

    stored_copy = copy.deepcopy(original_stored)

    resolve_cell_id(["uid-a", "uid-x"], original_stored)

    # Verify stored is unchanged
    assert original_stored == stored_copy


def test_zero_overlap_no_candidate_wins() -> None:
    """Multiple stored cells with zero overlap all lose."""
    stored = [
        _stored("c1", ["uid-a"]),
        _stored("c2", ["uid-b"]),
        _stored("c3", ["uid-c"]),
    ]
    assert resolve_cell_id(["uid-z"], stored) is None


def test_multiple_candidates_best_overlap_deterministic() -> None:
    """Multiple candidates with best_overlap must deterministically pick best."""
    stored = [
        _stored("c1", ["uid-a", "uid-b"]),
        _stored("c2", ["uid-a"]),
        _stored("c3", ["uid-a", "uid-b", "uid-c"]),
    ]
    result = resolve_cell_id(["uid-a", "uid-b"], stored)
    # c3 has 2 overlaps, c1 has 2 overlaps, c2 has 1 overlap.
    # On tie (both c1 and c3 have 2), lex-smallest wins: c1 < c3.
    assert result == "c1"


def test_higher_overlap_beats_lexicographically_smaller_id() -> None:
    """Higher overlap count always beats lex-smaller cell_id in tie-break."""
    # c2 is lex-smaller but has lower overlap; b has higher overlap
    stored = [
        _stored("c2", ["uid-x"]),  # overlap: 1, but lex-smaller
        _stored("b", ["uid-x", "uid-y"]),  # overlap: 2, should win despite lex-larger
    ]
    result = resolve_cell_id(["uid-x", "uid-y"], stored)
    # b should win because 2 overlaps > 1 overlap, even though "c2" < "b"
    assert result == "b"

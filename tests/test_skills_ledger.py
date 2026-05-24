"""Tests for guild.skills.ledger — ledger parse + idempotent consumer register.

Fixture ledger is defined inline; tests do NOT touch the live docs/skill-sources.md.
"""

from __future__ import annotations

import pytest

from guild.skills.ledger import parse_consumers, register_consumer

# ---------------------------------------------------------------------------
# Fixture ledger
# ---------------------------------------------------------------------------

FIXTURE_LEDGER = """\
# Skill sources

Some prose before the table.

| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | `tipalti`, `daria` |
| `communicate` | `steward` | — |
| `run-tests`, `version-bump` | `steward` |  |
"""

# A ledger that uses a hyphen instead of em-dash for "no consumers"
HYPHEN_LEDGER = """\
| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | - |
| `communicate` | `steward` | `alpha` |
"""

# A ledger with an agent already present (idempotency base)
ALREADY_REGISTERED_LEDGER = """\
| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | `newsib` |
| `communicate` | `steward` | `newsib`, `daria` |
| `run-tests`, `version-bump` | `steward` | `newsib` |
"""


# ===========================================================================
# parse_consumers tests
# ===========================================================================


class TestParseConsumers:
    def test_comma_split_and_first_backtick_token(self) -> None:
        """cicd row has two consumers; both are returned."""
        result = parse_consumers(FIXTURE_LEDGER, "cicd")
        assert result == ["tipalti", "daria"]

    def test_em_dash_yields_empty(self) -> None:
        """communicate row has em-dash in Downstream → no consumers."""
        result = parse_consumers(FIXTURE_LEDGER, "communicate")
        assert result == []

    def test_empty_cell_yields_empty(self) -> None:
        """run-tests row has empty Downstream cell → no consumers."""
        result = parse_consumers(FIXTURE_LEDGER, "run-tests")
        assert result == []

    def test_skill_membership_combined_row(self) -> None:
        """version-bump is listed together with run-tests; it should resolve to the same row."""
        result_run = parse_consumers(FIXTURE_LEDGER, "run-tests")
        result_vb = parse_consumers(FIXTURE_LEDGER, "version-bump")
        assert result_run == result_vb  # same row → same (empty) list

    def test_skill_not_in_ledger_returns_empty(self) -> None:
        """Unknown skill name → empty list, no exception."""
        result = parse_consumers(FIXTURE_LEDGER, "nonexistent-skill")
        assert result == []

    def test_hyphen_yields_empty(self) -> None:
        """A plain hyphen in the Downstream cell counts as 'no consumers'."""
        result = parse_consumers(HYPHEN_LEDGER, "cicd")
        assert result == []

    def test_deduplication(self) -> None:
        """Duplicate consumer names in the downstream cell are de-duplicated."""
        ledger = """\
| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | `alpha`, `alpha`, `beta` |
"""
        result = parse_consumers(ledger, "cicd")
        assert result == ["alpha", "beta"]

    def test_order_preserved(self) -> None:
        """Order of first appearance is preserved in the de-duplicated result."""
        ledger = """\
| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | `beta`, `alpha`, `gamma` |
"""
        result = parse_consumers(ledger, "cicd")
        assert result == ["beta", "alpha", "gamma"]

    def test_chunk_with_no_backtick_is_skipped(self) -> None:
        """A chunk that has no backtick-quoted token is skipped (not a bare name)."""
        ledger = """\
| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | plain-text, `alpha` |
"""
        result = parse_consumers(ledger, "cicd")
        assert result == ["alpha"]

    def test_table_without_downstream_column_ignored(self) -> None:
        """A table whose header does not include 'Downstream' is not a supplier table."""
        ledger = """\
| Name | Notes |
|------|-------|
| `cicd` | something |
"""
        result = parse_consumers(ledger, "cicd")
        assert result == []


# ===========================================================================
# register_consumer tests
# ===========================================================================


class TestRegisterConsumer:
    def test_adds_agent_to_all_rows_when_no_skills_filter(self) -> None:
        """register_consumer with skills=None adds agent to every canonical skill row."""
        result = register_consumer(FIXTURE_LEDGER, "newsib")
        # All three rows should now contain `newsib`
        consumers_cicd = parse_consumers(result, "cicd")
        consumers_comm = parse_consumers(result, "communicate")
        consumers_run = parse_consumers(result, "run-tests")
        assert "newsib" in consumers_cicd
        assert "newsib" in consumers_comm
        assert "newsib" in consumers_run

    def test_existing_consumers_preserved(self) -> None:
        """Pre-existing consumers in the Downstream cell are not removed."""
        result = register_consumer(FIXTURE_LEDGER, "newsib")
        consumers_cicd = parse_consumers(result, "cicd")
        assert "tipalti" in consumers_cicd
        assert "daria" in consumers_cicd

    def test_idempotent_no_duplicates(self) -> None:
        """Calling register_consumer twice produces byte-identical output."""
        once = register_consumer(FIXTURE_LEDGER, "newsib")
        twice = register_consumer(once, "newsib")
        assert once == twice

    def test_idempotent_on_already_registered(self) -> None:
        """Applying to a ledger where agent already appears returns identical text."""
        result = register_consumer(ALREADY_REGISTERED_LEDGER, "newsib")
        assert result == ALREADY_REGISTERED_LEDGER

    def test_skills_filter_limits_rows(self) -> None:
        """When skills=[...] is given, only matching rows are updated."""
        result = register_consumer(FIXTURE_LEDGER, "newsib", skills=["cicd"])
        assert "newsib" in parse_consumers(result, "cicd")
        assert "newsib" not in parse_consumers(result, "communicate")
        assert "newsib" not in parse_consumers(result, "run-tests")

    def test_em_dash_replaced_with_agent(self) -> None:
        """An em-dash Downstream cell (no consumers) becomes just the new agent."""
        result = register_consumer(FIXTURE_LEDGER, "newsib")
        consumers_comm = parse_consumers(result, "communicate")
        assert consumers_comm == ["newsib"]

    def test_empty_cell_replaced_with_agent(self) -> None:
        """An empty Downstream cell becomes just the new agent."""
        result = register_consumer(FIXTURE_LEDGER, "newsib")
        consumers_run = parse_consumers(result, "run-tests")
        assert consumers_run == ["newsib"]

    def test_non_supplier_table_untouched(self) -> None:
        """A table without a Downstream column is left byte-for-byte identical."""
        non_supplier = """\
| Name | Notes |
|------|-------|
| `cicd` | something |
"""
        # Embed in a larger ledger
        full = FIXTURE_LEDGER + "\n" + non_supplier
        result = register_consumer(full, "newsib")
        # The non-supplier portion must appear verbatim in the result
        assert non_supplier in result

    def test_prose_and_headers_unchanged(self) -> None:
        """Lines that are not table data rows are preserved exactly."""
        result = register_consumer(FIXTURE_LEDGER, "newsib")
        # Opening prose line must still be present
        assert "# Skill sources" in result
        assert "Some prose before the table." in result

    def test_combined_row_both_skills_matched(self) -> None:
        """A row listing multiple skills (run-tests, version-bump) matches either name."""
        result_via_run = register_consumer(FIXTURE_LEDGER, "newsib", skills=["run-tests"])
        result_via_vb = register_consumer(FIXTURE_LEDGER, "newsib", skills=["version-bump"])
        # Both should update the same row identically
        assert result_via_run == result_via_vb

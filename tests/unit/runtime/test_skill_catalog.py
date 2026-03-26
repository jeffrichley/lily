"""Unit tests for SKILL.md parsing and skill metadata contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lily.runtime.skill_catalog import (
    ParsedSkillMarkdown,
    load_skill_md,
    parse_skill_markdown,
)
from lily.runtime.skill_types import (
    SkillValidationError,
    is_recommended_kebab_case_skill_name,
    normalize_skill_name,
    reserved_provider_name_prefix,
)

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "skills"


def test_parse_minimal_fixture_skill_md() -> None:
    """Loads valid minimal SKILL.md fixture."""
    # Arrange - path to checked-in valid minimal skill package
    path = _FIXTURES / "valid" / "minimal" / "SKILL.md"
    # Act - load and parse SKILL.md
    result = load_skill_md(path)
    # Assert - metadata and body match expected contract
    assert isinstance(result, ParsedSkillMarkdown)
    assert result.metadata.name == "minimal-skill"
    assert "Minimal" in result.body
    assert result.source_path == path


def test_parse_full_optional_fixture_includes_nested_metadata() -> None:
    """Optional frontmatter keys, standard type, and nested metadata are accepted."""
    # Arrange - path to fixture with optional keys and nested metadata
    path = _FIXTURES / "valid" / "full_optional" / "SKILL.md"
    # Act - load skill package
    result = load_skill_md(path)
    # Assert - optional fields and nested version are present
    assert result.metadata.skill_type == "standard"
    assert result.metadata.license == "MIT"
    assert result.metadata.metadata is not None
    assert result.metadata.metadata["version"] == "0.1.0"


def test_missing_description_field_fails() -> None:
    """Missing required description yields field-specific error."""
    # Arrange - fixture missing required description
    path = _FIXTURES / "invalid" / "missing_description" / "SKILL.md"
    # Act - load invalid skill file
    with pytest.raises(SkillValidationError) as err:
        load_skill_md(path)
    # Assert - error references description
    assert err.value.field is not None
    assert "description" in str(err.value).lower()


def test_unknown_field_rejected() -> None:
    """Unknown top-level keys are rejected (fail fast)."""
    # Arrange - markdown with disallowed extra top-level key
    raw = """---
name: x
description: "d"
extra_key: not-allowed
---
body
"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - error mentions forbidden extra input
    assert "extra_key" in str(err.value) or "extra" in str(err.value).lower()


def test_description_max_length_enforced() -> None:
    """Description over 1024 chars is rejected."""
    # Arrange - JSON-escaped description longer than 1024 characters
    long_desc = "a" * 1025
    raw = f"---\nname: x\ndescription: {json.dumps(long_desc)}\n---\n"
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - validation ties to description
    assert "description" in str(err.value).lower()


def test_angle_bracket_in_name_rejected() -> None:
    """Angle brackets in values are forbidden."""
    # Arrange - forbidden angle brackets in name field
    raw = """---
name: <bad>
description: "ok"
---
"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - policy error mentions angle brackets
    assert "angle bracket" in str(err.value).lower()


def test_angle_bracket_in_nested_metadata_rejected() -> None:
    """Angle brackets in nested metadata strings are rejected."""
    # Arrange - angle brackets inside nested metadata string
    raw = """---
name: ok
description: "ok"
metadata:
  note: "bad <x> value"
---
"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - nested value is rejected
    assert "angle bracket" in str(err.value).lower()


def test_reserved_name_prefix_claude_rejected() -> None:
    """Names starting with claude are blocked."""
    # Arrange - reserved claude-prefixed name
    raw = """---
name: claude-helper
description: "nope"
---
"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - field and message identify name policy
    assert err.value.field == "name"
    assert "reserved" in str(err.value).lower()


def test_reserved_name_prefix_anthropic_rejected() -> None:
    """Names starting with anthropic are blocked."""
    # Arrange - reserved anthropic-prefixed name
    raw = """---
name: anthropic-brand
description: "nope"
---
"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - error targets name field
    assert err.value.field == "name"


def test_non_reserved_substring_allowed() -> None:
    """Names containing 'claude' not at prefix are allowed."""
    # Arrange - name containing claude but not as a blocked prefix
    raw = """---
name: my-claude-adjacent
description: "ok"
---
"""
    # Act - parse markdown
    result = parse_skill_markdown(raw)
    # Assert - parse succeeds with original name preserved
    assert result.metadata.name == "my-claude-adjacent"


def test_malformed_yaml_frontmatter_rejected() -> None:
    """Unclosed YAML structure raises deterministic error."""
    # Arrange - invalid YAML in frontmatter block
    raw = """---
name: [
---
body"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - failure is attributed to frontmatter parse
    assert err.value.field == "frontmatter"


def test_playbook_type_still_valid_for_forward_compat() -> None:
    """Legacy playbook type enum remains accepted."""
    # Arrange - valid optional type for post-MVP adapter hint
    raw = """---
name: x
description: "d"
type: playbook
---
"""
    # Act - parse markdown
    result = parse_skill_markdown(raw)
    # Assert - enum value is preserved
    assert result.metadata.skill_type == "playbook"


def test_invalid_type_field_rejected() -> None:
    """Invalid optional type enum is rejected."""
    # Arrange - invalid type enum value
    raw = """---
name: x
description: "d"
type: not-a-mode
---
"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - error references type
    assert "type" in str(err.value).lower()


def test_metadata_version_invalid_semver_rejected() -> None:
    """metadata.version must be semver when present."""
    # Arrange - non-semver version string under metadata
    raw = """---
name: x
description: "d"
metadata:
  version: "not-a-semver"
---
"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - semver validation error path
    assert "metadata.version" in str(err.value)


def test_metadata_version_non_string_rejected() -> None:
    """metadata.version must be a string."""
    # Arrange - numeric version (invalid type for semver string rule)
    raw = """---
name: x
description: "d"
metadata:
  version: 1
---
"""
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - field-specific rejection
    assert err.value.field == "metadata.version"


def test_load_skill_md_rejects_wrong_filename(tmp_path: Path) -> None:
    """Only SKILL.md is accepted as the package path."""
    # Arrange - write valid frontmatter to a non-SKILL filename
    wrong = tmp_path / "README.md"
    wrong.write_text(
        '---\nname: x\ndescription: "d"\n---\n',
        encoding="utf-8",
    )
    # Act - load via wrong filename
    with pytest.raises(SkillValidationError) as err:
        load_skill_md(wrong)
    # Assert - contract requires SKILL.md filename
    assert err.value.field == "path"


def test_normalize_skill_name_maps_spaces_and_underscores() -> None:
    """Normalization produces stable kebab-like keys."""
    # Arrange - sample author-facing names with mixed spacing and underscores
    samples = (
        ("My Skill", "my-skill"),
        ("Brand_Guidelines", "brand-guidelines"),
        ("  Foo   Bar  ", "foo-bar"),
    )
    # Act - normalize each sample name
    got = [normalize_skill_name(raw_name) for raw_name, _ in samples]
    # Assert - each maps to the expected canonical key
    expected = [pair[1] for pair in samples]
    assert got == expected


def test_is_recommended_kebab_case_skill_name() -> None:
    """Kebab-case recommendation helper matches spec pattern."""
    # Arrange - names with different authoring styles
    good = "brand-guidelines"
    bad_mixed = "Brand_Guidelines"
    bad_spaces = "not a kebab"
    # Act - evaluate recommendation helper for each name
    results = (
        is_recommended_kebab_case_skill_name(good),
        is_recommended_kebab_case_skill_name(bad_mixed),
        is_recommended_kebab_case_skill_name(bad_spaces),
    )
    # Assert - helper matches recommended pattern only for kebab-case
    assert results == (True, False, False)


def test_reserved_provider_name_prefix_helper() -> None:
    """Prefix helper matches policy."""
    # Arrange - names covering prefix and substring cases
    blocked_prefix = "claude-x"
    blocked_anthropic = "Anthropic"
    allowed_substring = "my-claude"
    # Act - evaluate prefix helper for each name
    results = (
        reserved_provider_name_prefix(blocked_prefix),
        reserved_provider_name_prefix(blocked_anthropic),
        reserved_provider_name_prefix(allowed_substring),
    )
    # Assert - only leading reserved prefixes are blocked
    assert results == (True, True, False)


def test_to_summary_preserves_name_and_canonical_key() -> None:
    """SkillMetadata.to_summary maps canonical key for retrieval."""
    # Arrange - mixed-case name requiring normalization for index key
    raw = """---
name: Mixed_Case Name
description: "d"
---
"""
    # Act - parse then build summary
    result = parse_skill_markdown(raw)
    summary = result.metadata.to_summary()
    # Assert - original name preserved; canonical key normalized
    assert summary.name == "Mixed_Case Name"
    assert summary.canonical_key == "mixed-case-name"


def test_no_frontmatter_yields_missing_required_fields() -> None:
    """Plain markdown without YAML fails required fields."""
    # Arrange - content with no YAML frontmatter block
    raw = "no frontmatter here"
    # Act - parse markdown
    with pytest.raises(SkillValidationError) as err:
        parse_skill_markdown(raw)
    # Assert - validation fails before successful model construction
    assert err.value.field is not None or str(err.value)

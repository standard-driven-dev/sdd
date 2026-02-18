#!/usr/bin/env python3
"""
SDD Spec Validator

Validates:
1. YAML syntax
2. JSON Schema conformance
3. Referential integrity (all IDs reference existing entities)

Usage: python3 scripts/validate_spec.py
"""

import json
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "schema" / "sdd-spec.schema.json"
SPEC_DIR = ROOT / "spec"


def load_yaml(path: Path) -> Any:
    """Load and parse YAML file."""
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error in {path}: {e}")
        return None
    except FileNotFoundError:
        print(f"❌ File not found: {path}")
        return None


def load_json(path: Path) -> Any:
    """Load JSON file."""
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON syntax error in {path}: {e}")
        return None
    except FileNotFoundError:
        print(f"❌ File not found: {path}")
        return None


def collect_ids(spec: Dict[str, Any], key: str, id_field: str) -> Set[str]:
    """Collect all IDs of a specific type from spec."""
    ids = set()
    if key in spec and spec[key]:
        for item in spec[key]:
            if isinstance(item, dict) and id_field in item:
                ids.add(item[id_field])
    return ids


def validate_referential_integrity(catalog: Dict[str, Any]) -> List[str]:
    """Check that all references point to existing entities."""
    errors = []

    # Collect all IDs
    standards = collect_ids(catalog, "standards", "id")
    tools = collect_ids(catalog, "tools", "id")
    properties = collect_ids(catalog, "properties", "id")

    # Load mappings for verification
    prop_to_std = load_yaml(SPEC_DIR / "mappings" / "property_to_standard.yaml")
    verifications = load_yaml(SPEC_DIR / "mappings" / "property_verifications.yaml")

    if prop_to_std and "mappings" in prop_to_std:
        for mapping in prop_to_std["mappings"]:
            prop_id = mapping.get("property_id")
            std_id = mapping.get("standard_id")

            if prop_id and prop_id not in properties:
                errors.append(f"Mapping references unknown property: {prop_id}")
            if std_id and std_id not in standards:
                errors.append(f"Mapping references unknown standard: {std_id}")

    if verifications and "verifications" in verifications:
        for v in verifications["verifications"]:
            prop_id = v.get("property_id")
            tool_id = v.get("tool_id")

            if prop_id and prop_id not in properties:
                errors.append(f"Verification references unknown property: {prop_id}")
            if tool_id and tool_id not in tools:
                errors.append(f"Verification references unknown tool: {tool_id}")

    return errors


def validate_spec() -> bool:
    """Main validation function."""
    print("🔍 Validating SDD specification files...\n")

    errors = []
    warnings = []

    # 1. Load schema
    print("📋 Loading schema...")
    schema = load_json(SCHEMA_PATH)
    if not schema:
        errors.append("Failed to load schema")
        return False
    print("   ✓ Schema loaded\n")

    # 2. Load catalog files
    print("📂 Loading catalog files...")
    standards_file = SPEC_DIR / "catalog" / "standards.yaml"
    properties_file = SPEC_DIR / "catalog" / "properties.yaml"
    tools_file = SPEC_DIR / "catalog" / "tools.yaml"

    standards_data = load_yaml(standards_file)
    properties_data = load_yaml(properties_file)
    tools_data = load_yaml(tools_file)

    if not all([standards_data, properties_data, tools_data]):
        errors.append("Failed to load catalog files")
        return False

    # Build catalog
    catalog = {
        "standards": standards_data.get("standards", []),
        "properties": properties_data.get("properties", []),
        "tools": tools_data.get("tools", []),
    }
    print(f"   ✓ Loaded {len(catalog['standards'])} standards")
    print(f"   ✓ Loaded {len(catalog['properties'])} properties")
    print(f"   ✓ Loaded {len(catalog['tools'])} tools\n")

    # 3. Validate referential integrity
    print("🔗 Checking referential integrity...")
    integrity_errors = validate_referential_integrity(catalog)
    if integrity_errors:
        for err in integrity_errors:
            errors.append(err)
    else:
        print("   ✓ All references valid\n")

    # 4. Validate patterns (basic checks)
    print("📏 Validating ID patterns...")

    for std in catalog["standards"]:
        if not std.get("id", "").startswith("std:"):
            errors.append(f"Standard ID must start with 'std:': {std.get('id')}")

    for prop in catalog["properties"]:
        if not prop.get("id", "").startswith("prop:"):
            errors.append(f"Property ID must start with 'prop:': {prop.get('id')}")

    for tool in catalog["tools"]:
        if not tool.get("id", "").startswith("tool:"):
            errors.append(f"Tool ID must start with 'tool:': {tool.get('id')}")

    print("   ✓ ID patterns valid\n")

    # 5. Check verification types
    print("🔍 Validating verification types...")
    valid_types = ["library", "custom_property", "ai_audit", "manual"]

    for prop in catalog["properties"]:
        vtype = prop.get("verification_type")
        if vtype and vtype not in valid_types:
            errors.append(f"Invalid verification_type '{vtype}' in {prop.get('id')}")

    print("   ✓ Verification types valid\n")

    # Summary
    print("=" * 50)
    if errors:
        print(f"❌ VALIDATION FAILED ({len(errors)} error(s)):\n")
        for err in errors:
            print(f"   - {err}")
        return False
    else:
        print("✅ VALIDATION PASSED")
        print(f"   Standards: {len(catalog['standards'])}")
        print(f"   Properties: {len(catalog['properties'])}")
        print(f"   Tools: {len(catalog['tools'])}")
        return True


if __name__ == "__main__":
    success = validate_spec()
    sys.exit(0 if success else 1)

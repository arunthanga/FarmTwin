"""Tests for FTS survey schema validation (engine/FarmTwin/schemas/).

Covers:
  - JSON schema structure validation (all required fields)
  - Domain-specific validation rules V01–V18 (from survey-schema.md §9)
  - Import/export round-trip fidelity
  - Mobile survey app data → FTS JSON conversion

White-paper references:
  [FTS]  survey-schema.md v1.0.0 (FarmTwin Survey Schema)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

try:
    from FarmTwin.preprocess import (
        load_fts_json,
        validate_fts_json,
    )

    _PREPROCESS_AVAILABLE = True
except ImportError:
    _PREPROCESS_AVAILABLE = False

# Path to the example FTS document used throughout
EXAMPLE_FTS_PATH = Path(__file__).parent.parent.parent / "docs/examples/eruthempathy_pilot.fts.json"

# Load the example document once (fixture will deep-copy it per test)
_EXAMPLE_DOC: dict = {}
if EXAMPLE_FTS_PATH.exists():
    with EXAMPLE_FTS_PATH.open() as _f:
        _EXAMPLE_DOC = json.load(_f)


@pytest.fixture
def valid_fts() -> dict:
    """Return a deep copy of the example FTS document (always valid)."""
    if not _EXAMPLE_DOC:
        pytest.skip("Example FTS document not found at docs/examples/eruthempathy_pilot.fts.json")
    return copy.deepcopy(_EXAMPLE_DOC)


# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — Schema Version & Top-Level Structure (unit)
# ══════════════════════════════════════════════════════════════════════


class TestFTSTopLevel:
    """Unit tests for top-level FTS document structure."""

    @pytest.mark.unit
    def test_valid_example_passes_validation(self, valid_fts: dict) -> None:
        """The pilot example FTS document must pass all validation rules V01–V18."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        errors = validate_fts_json(valid_fts)
        assert errors == [], f"Unexpected validation errors: {errors}"

    @pytest.mark.unit
    def test_wrong_schema_version_fails_v01(self, valid_fts: dict) -> None:
        """V01: schema_version != '1.0' must fail with V01 error."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["schema_version"] = "2.0"
        errors = validate_fts_json(valid_fts)
        assert any("V01" in e or "schema_version" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_invalid_survey_id_fails_v02(self, valid_fts: dict) -> None:
        """V02: survey_id must be a valid UUID v4."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["survey_id"] = "not-a-uuid"
        errors = validate_fts_json(valid_fts)
        assert any("V02" in e or "survey_id" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_missing_required_fields_reported(self) -> None:
        """Missing top-level required fields must all be reported, not just the first."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        minimal_invalid = {"schema_version": "1.0"}
        errors = validate_fts_json(minimal_invalid)
        # Must report multiple missing fields
        assert len(errors) > 1


# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — Farm Block Validation (unit)
# ══════════════════════════════════════════════════════════════════════


class TestFTSFarmBlock:
    """Unit tests for farm block validation rules."""

    @pytest.mark.unit
    def test_area_out_of_range_fails_v03(self, valid_fts: dict) -> None:
        """V03: farm.area_ha must be 0.01–500 ha."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["farm"]["area_ha"] = 0.001
        errors = validate_fts_json(valid_fts)
        assert any("V03" in e or "area" in e.lower() for e in errors)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "soil_type",
        [
            "sandy",
            "loam",
            "clay_loam",
            "red_laterite",
            "black_cotton",
        ],
    )
    def test_known_soil_types_accepted(self, valid_fts: dict, soil_type: str) -> None:
        """All documented soil types in §4.1 must pass validation."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["farm"]["soil_type_primary"] = soil_type
        errors = validate_fts_json(valid_fts)
        soil_errors = [e for e in errors if "soil" in e.lower()]
        assert soil_errors == []

    @pytest.mark.unit
    def test_unknown_soil_type_fails(self, valid_fts: dict) -> None:
        """An undocumented soil type must fail validation."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["farm"]["soil_type_primary"] = "moon_dust"
        errors = validate_fts_json(valid_fts)
        assert any("soil" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_invalid_phone_fails_v18(self, valid_fts: dict) -> None:
        """V18: surveyed_by.phone must match E.164 format (+countrycode digits)."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["surveyed_by"]["phone"] = "9876543210"  # missing + prefix
        errors = validate_fts_json(valid_fts)
        assert any("V18" in e or "phone" in e.lower() for e in errors)


# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — Network Topology Validation (unit)
# ══════════════════════════════════════════════════════════════════════


class TestFTSNetworkTopology:
    """Unit tests for node/link topology validation rules V04–V09."""

    @pytest.mark.unit
    def test_elevation_out_of_range_fails_v04(self, valid_fts: dict) -> None:
        """V04: node elevation must be in –10 to 3000 m range."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["nodes"][0]["location"]["elevation_m"] = 5000.0
        errors = validate_fts_json(valid_fts)
        assert any("V04" in e or "elevation" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_no_water_source_fails_v05(self, valid_fts: dict) -> None:
        """V05: at least one reservoir or pump node must be present."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        # Remove all reservoir/pump nodes
        valid_fts["nodes"] = [
            n for n in valid_fts["nodes"] if n["type"] not in ("reservoir", "pump")
        ]
        errors = validate_fts_json(valid_fts)
        assert any("V05" in e or "source" in e.lower() or "pump" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_dangling_link_fails_v06(self, valid_fts: dict) -> None:
        """V06: link.from_node or to_node referencing non-existent node must fail."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["links"][0]["to_node"] = "GHOST_NODE_999"
        errors = validate_fts_json(valid_fts)
        assert any("V06" in e or "dangling" in e.lower() or "GHOST_NODE_999" in e for e in errors)

    @pytest.mark.unit
    def test_disconnected_network_fails_v07(self, valid_fts: dict) -> None:
        """V07: an isolated node not reachable from the source must fail."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        # Add an orphan junction with no links
        valid_fts["nodes"].append(
            {
                "id": "ORPHAN",
                "type": "junction",
                "location": {"lat": 10.65, "lon": 76.64, "elevation_m": 140.0},
                "elevation_source": "manual",
                "attributes": {},
            }
        )
        errors = validate_fts_json(valid_fts)
        assert any("V07" in e or "disconnected" in e.lower() or "ORPHAN" in e for e in errors)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "diameter_m,should_pass",
        [
            (0.005, True),  # 5mm — lower bound (drip lateral)
            (0.5, True),  # 500mm — upper bound (large main)
            (0.004, False),  # below lower bound
            (0.51, False),  # above upper bound
        ],
    )
    def test_pipe_diameter_bounds_v08(
        self,
        valid_fts: dict,
        diameter_m: float,
        should_pass: bool,
    ) -> None:
        """V08: pipe internal diameter must be in 0.005–0.5 m range."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["links"][0]["internal_diameter_m"] = diameter_m
        errors = validate_fts_json(valid_fts)
        diameter_errors = [e for e in errors if "V08" in e or "diameter" in e.lower()]
        if should_pass:
            assert diameter_errors == []
        else:
            assert diameter_errors != []


# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — Zone & Crop Validation (unit)
# ══════════════════════════════════════════════════════════════════════


class TestFTSZoneValidation:
    """Unit tests for zone and crop validation rules V10–V16."""

    @pytest.mark.unit
    def test_known_crop_types_accepted(self, valid_fts: dict) -> None:
        """V16: all documented crop types in §4.5 must pass validation."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        for crop in ["coconut", "paddy", "banana_nendran", "tomato", "okra"]:
            fts_copy = copy.deepcopy(valid_fts)
            fts_copy["zones"][0]["crop"]["type"] = crop
            errors = validate_fts_json(fts_copy)
            crop_errors = [e for e in errors if "V16" in e or "crop" in e.lower()]
            assert crop_errors == [], f"Crop '{crop}' should be valid but got: {crop_errors}"

    @pytest.mark.unit
    def test_unknown_crop_fails_v16(self, valid_fts: dict) -> None:
        """V16: an undocumented crop type must fail validation."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["zones"][0]["crop"]["type"] = "durian"
        errors = validate_fts_json(valid_fts)
        assert any("V16" in e or "crop" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_emitter_flow_out_of_range_fails_v10(self, valid_fts: dict) -> None:
        """V10: emitter flow rate must be 0.5–200 L/h."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["zones"][0]["emitter_layout"]["flow_rate_lh"] = 0.1
        errors = validate_fts_json(valid_fts)
        assert any("V10" in e or "flow_rate" in e.lower() or "emitter" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_no_zones_fails_v12(self, valid_fts: dict) -> None:
        """V12: at least one zone must be defined."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        valid_fts["zones"] = []
        errors = validate_fts_json(valid_fts)
        assert any("V12" in e or "zone" in e.lower() for e in errors)


# ══════════════════════════════════════════════════════════════════════
# SECTION 5 — Round-Trip Import/Export (unit)
# ══════════════════════════════════════════════════════════════════════


class TestFTSRoundTrip:
    """Unit tests for FTS JSON round-trip fidelity (load → serialize → reload)."""

    @pytest.mark.unit
    def test_load_produces_valid_network(self, valid_fts: dict) -> None:
        """load_fts_json must produce a network dict solvable by GGASolver."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        network = load_fts_json(valid_fts)
        # Must have nodes and links
        assert "nodes" in network
        assert "links" in network
        assert len(network["nodes"]) >= 2  # noqa: PLR2004
        assert len(network["links"]) >= 1

    @pytest.mark.unit
    def test_all_node_ids_preserved(self, valid_fts: dict) -> None:
        """All node IDs from the FTS document must appear in the loaded network."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        network = load_fts_json(valid_fts)
        fts_node_ids = {n["id"] for n in valid_fts["nodes"]}
        network_node_ids = {n["id"] for n in network["nodes"]}
        assert fts_node_ids == network_node_ids

    @pytest.mark.unit
    def test_all_link_ids_preserved(self, valid_fts: dict) -> None:
        """All link IDs from the FTS document must appear in the loaded network."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        network = load_fts_json(valid_fts)
        fts_link_ids = {ln["id"] for ln in valid_fts["links"]}
        network_link_ids = {ln["id"] for ln in network["links"]}
        assert fts_link_ids.issubset(network_link_ids)  # net may add virtual emitter links

    @pytest.mark.unit
    def test_pipe_lengths_preserved_within_tolerance(self, valid_fts: dict) -> None:
        """Pipe lengths must be preserved exactly through the load/convert cycle."""
        if not _PREPROCESS_AVAILABLE:
            pytest.skip("preprocess module not available")
        network = load_fts_json(valid_fts)
        for fts_link in valid_fts["links"]:
            net_link = next(
                (ln for ln in network["links"] if ln["id"] == fts_link["id"]),
                None,
            )
            if net_link is not None:
                assert net_link["length_m"] == pytest.approx(fts_link["length_m"], rel=1e-6)


# ══════════════════════════════════════════════════════════════════════
# SECTION 6 — TDD Stubs
# ══════════════════════════════════════════════════════════════════════


class TestFTSSchemaTDD:
    """TDD stubs for schema features not yet implemented."""

    @pytest.mark.tdd
    def test_epanet_inp_import_roundtrip(self, tmp_path: pytest.TempPathFactory) -> None:
        """EPANET .inp → FTS JSON → GGA network must produce the same heads.

        Not yet implemented: EPANET .inp → FTS converter in preprocess.py.
        """
        from FarmTwin.preprocess import load_epanet_inp  # type: ignore[import]

        inp_file = tmp_path / "test_network.inp"  # type: ignore[operator]
        inp_file.write_text("""\
[TITLE]
Round-trip test

[JUNCTIONS]
J1    0    0

[RESERVOIRS]
R1    100
R2    80

[PIPES]
P1    R1    J1    1000    200    100
P2    J1    R2    800     150    100

[END]
""")
        network = load_epanet_inp(str(inp_file))
        assert network["nodes"] is not None
        assert len(network["links"]) == 2  # noqa: PLR2004

    @pytest.mark.tdd
    def test_kobo_webhook_ingest_converts_to_fts(self) -> None:
        """KoboToolbox webhook payload must be convertible to valid FTS JSON.

        Not yet implemented: POST /api/v1/surveys/kobo-ingest endpoint.
        """
        from FarmTwin.preprocess import convert_kobo_to_fts  # type: ignore[import]

        kobo_payload = {
            "_id": 12345,
            "farm_name": "Test Farm",
            "farm_area_ha": 5.0,
            "village": "Eruthempathy",
            "source_type": "borewell",
            "_geolocation": [10.6521, 76.6401],
        }
        fts = convert_kobo_to_fts(kobo_payload)
        assert fts["schema_version"] == "1.0"
        assert fts["farm"]["area_ha"] == pytest.approx(5.0)

    @pytest.mark.tdd
    def test_qr_devEUI_scan_registers_sensor(self) -> None:
        """Scanning a LoRaWAN DevEUI QR code must auto-register the sensor in the FTS doc.

        Not yet implemented: commissioning_app/qr_scanner.py → FTS sensor registration.
        """
        from FarmTwin.commissioning import register_sensor_from_deveui  # type: ignore[import]

        fts = copy.deepcopy(_EXAMPLE_DOC)
        updated_fts = register_sensor_from_deveui(
            fts=fts,
            dev_eui="70B3D57ED0049AFF",
            sensor_type="soil_moisture",
            zone_id="Z01",
            location={"lat": 10.6520, "lon": 76.6420, "elevation_m": 140.5},
        )
        sensor_ids = [s["lora_dev_eui"] for s in updated_fts["sensors"]]
        assert "70B3D57ED0049AFF" in sensor_ids

    @pytest.mark.tdd
    def test_bom_generation_includes_all_pipe_types(self, valid_fts: dict) -> None:
        """BoM generated from an FTS doc must include entries for every pipe material used.

        Not yet implemented: BoM generator in postprocess.py.
        """
        from FarmTwin.postprocess import generate_bom  # type: ignore[import]

        bom = generate_bom(valid_fts)
        materials_in_fts = {ln["material"] for ln in valid_fts["links"]}
        materials_in_bom = {item["material"] for item in bom["pipes"]}
        assert materials_in_fts == materials_in_bom

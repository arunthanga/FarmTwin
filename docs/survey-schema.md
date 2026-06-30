# FarmTwin — Input Formats & Survey Schema

**Version:** 1.0.0  
**Date:** 2026-06-29  
**Related:** `requirements.md §4`, `engine/krishiflow/preprocess.py`

---

## Table of Contents

1. [Can the Survey Be Done on a Mobile Phone?](#1-can-the-survey-be-done-on-a-mobile-phone)
2. [Survey Data Entry Modes](#2-survey-data-entry-modes)
3. [Master Schema: FarmTwin Survey Export/Import (FTS format)](#3-master-schema-farmtwin-survey-export--import-fts-format)
4. [Sub-schemas](#4-sub-schemas)
5. [Mobile Survey App — Field by Field UX Flow](#5-mobile-survey-app--field-by-field-ux-flow)
6. [Import/Export Rules](#6-importexport-rules)
7. [Offline-First Sync Protocol](#7-offline-first-sync-protocol)
8. [Integration with KoboToolbox / ODK (Third-Party Survey Tools)](#8-integration-with-kobotoolbox--odk)
9. [Validation Rules](#9-validation-rules)
10. [Example: Eruthempathy Pilot Farm](#10-example-eruthempathy-pilot-farm)

---

## 1. Can the Survey Be Done on a Mobile Phone?

**Yes — a mobile phone is the primary and recommended survey instrument.** The FarmTwin Studio survey app is designed from the ground up for a field technician walking a farm with a tablet or large-screen Android/iOS phone. No desktop or laptop required.

### What the phone handles natively

| Survey task | Phone capability | Tool used |
|---|---|---|
| Node placement (pump, junction, valve zone) | GPS tap on satellite basemap | Mapbox GL offline tiles |
| Pipe routing between nodes | Tap-and-drag on the map | Same |
| Node elevation | Automatic from phone GPS altitude + SRTM correction | Google Elevation API (online) / bundled SRTM tiles (offline) |
| Emitter zone boundary drawing | Polygon draw on map | Mapbox draw plugin |
| Photo of pump nameplate / motor label | Camera | React Native camera |
| Soil texture photo (for AI texture estimation) | Camera | ML model on-device |
| Component scan (emitter, valve, filter) | QR/barcode scan | React Native camera + component catalogue lookup |
| Voice note for field observations | Microphone | React Native audio |
| GPS track of pipe trench | Walk the route while recording | GPS track logging |
| Data sync to cloud | Wi-Fi or 4G when available | Background sync |
| Full offline operation | Yes — survey, save, sync later | Local SQLite + offline tiles |

### What still needs manual input

| Data item | Why manual | How collected |
|---|---|---|
| Pipe diameter per segment | Not detectable from GPS | Dropdown from catalogue |
| Pump model / HP | Nameplate photo + manual confirm | Photo + OCR assist |
| Crop per zone | Farmer knowledge | Dropdown from crop catalogue |
| Soil lab report (optional) | Lab result | CSV/PDF upload via phone Files app |
| Water source: borewell depth, static/dynamic water level | Requires measurement | Manual number entry |
| Electricity tariff (for cost calc) | Local knowledge | Manual entry |

**Bottom line:** a complete farm survey for a 15-acre drip system (≈ 20–50 nodes, 3–5 zones) can be completed in **45–90 minutes on-site** by a trained installation person using only a phone.

---

## 2. Survey Data Entry Modes

### Mode A — Native FarmTwin Studio App (recommended)

React Native app running on Android 11+ or iOS 15+. Data saved to on-device SQLite in the FTS JSON format (§3) and synced to cloud.

### Mode B — KoboToolbox / ODK Collect (NGO/FPO deployments)

For FPOs with existing KoboToolbox or ODK workflows, a KoboToolbox XLSForm template is provided (see §8). The submission is automatically converted to FTS JSON by the FarmTwin cloud API on receipt.

### Mode C — CSV Bulk Upload (installer desktop)

For installers who prefer spreadsheets. A template CSV (`templates/farm_survey_template.csv`) with one row per node and one sheet per link type. Uploaded and converted to FTS JSON by the cloud importer.

### Mode D — Direct JSON (API / developer)

POST to `POST /api/v1/surveys` with `Content-Type: application/json` and a valid FTS JSON body. Used by integrators and automated pipelines.

---

## 3. Master Schema: FarmTwin Survey Export/Import (FTS format)

**File extension:** `.fts.json`  
**MIME type:** `application/vnd.farmtwin.survey+json`  
**Version field:** `"schema_version": "1.0"`  
**Character encoding:** UTF-8  
**Coordinate system:** WGS84 decimal degrees (EPSG:4326)  
**All lengths:** metres. All flows: m³/s internally; L/h in the human-readable display layer.

```json
{
  "schema_version": "1.0",
  "survey_id": "<uuid-v4>",
  "farm_id": "<uuid-v4>",
  "created_at": "2026-06-29T08:15:00+05:30",
  "updated_at": "2026-06-29T14:32:00+05:30",
  "surveyed_by": {
    "name": "Rajan K.",
    "phone": "+919876543210",
    "role": "installer"
  },
  "sync_status": "synced",

  "farm": { /* §4.1 */ },
  "water_source": { /* §4.2 */ },
  "nodes": [ /* §4.3 — array of Node objects */ ],
  "links": [ /* §4.4 — array of Link objects */ ],
  "zones": [ /* §4.5 — array of Zone objects */ ],
  "sensors": [ /* §4.6 — array of Sensor objects */ ],
  "weather": { /* §4.7 */ },
  "design_constraints": { /* §4.8 */ },
  "attachments": [ /* §4.9 — photos, voice notes, lab reports */ ]
}
```

---

## 4. Sub-schemas

### 4.1 Farm (`farm`)

```json
{
  "name": "Arun Eruthempathy Farm",
  "owner_name": "Arun T.",
  "owner_phone": "+919876543210",
  "village": "Eruthempathy",
  "taluk": "Chittur",
  "district": "Palakkad",
  "state": "Kerala",
  "country": "IN",
  "survey_number": "300",
  "block": "30",
  "area_ha": 6.07,
  "boundary_polygon": {
    "type": "Polygon",
    "coordinates": [
      [[76.6401, 10.6521], [76.6445, 10.6521],
       [76.6445, 10.6498], [76.6401, 10.6498], [76.6401, 10.6521]]
    ]
  },
  "terrain": "undulating",
  "slope_pct_approx": 2.5,
  "soil_type_primary": "red_laterite",
  "groundwater_ec_us_cm": 850,
  "power_availability": "3phase_11kv",
  "electricity_tariff_inr_kwh": 5.80
}
```

**Allowed values:**

| Field | Allowed values |
|---|---|
| `terrain` | `flat`, `undulating`, `hilly`, `terraced` |
| `soil_type_primary` | `sandy`, `sandy_loam`, `loam`, `clay_loam`, `clay`, `red_laterite`, `black_cotton`, `alluvial` |
| `power_availability` | `single_phase_230v`, `3phase_415v`, `3phase_11kv`, `solar_only`, `none` |

### 4.2 Water Source (`water_source`)

```json
{
  "type": "borewell",
  "location": { "lat": 10.6521, "lon": 76.6401, "elevation_m": 142.5 },
  "borewell_depth_m": 120,
  "static_water_level_m": 35,
  "dynamic_water_level_m": 55,
  "yield_lpm": 800,
  "ec_us_cm": 820,
  "ph": 7.1,
  "tds_ppm": 540,
  "sump_volume_litre": 25000,
  "sump_elevation_m": 141.2,
  "pump_installed": false
}
```

**`type` allowed values:** `borewell`, `open_well`, `canal`, `river`, `pond`, `reservoir`, `municipal`, `rainwater_harvesting`

### 4.3 Nodes (`nodes` — array)

Each node is either a fixed-head node (source/reservoir), a junction, a pump, or a control element.

```json
{
  "id": "N01",
  "type": "pump",
  "label": "Main pump",
  "location": { "lat": 10.6521, "lon": 76.6401, "elevation_m": 141.5 },
  "elevation_source": "gps_corrected",
  "attributes": {
    "motor_hp": 5,
    "motor_phase": 3,
    "pump_make": "Kirloskar",
    "pump_model": "STAR-1 5HP",
    "curve_shutoff_m": 38.0,
    "curve_design_q_m3s": 0.00111,
    "curve_design_h_m": 28.0,
    "curve_maxflow_m3s": 0.00194,
    "motor_efficiency_pct": 88,
    "nameplate_photo_ref": "att_001"
  }
}
```

**`type` allowed values for nodes:**

| Type | Description |
|---|---|
| `reservoir` | Fixed-head source (tank, sump, canal) |
| `pump` | Pump/motor unit |
| `junction` | Pipe junction / tee |
| `prv` | Pressure-reducing valve |
| `psv` | Pressure-sustaining valve |
| `fcv` | Flow-control valve |
| `zone_valve` | On/off zone valve (solenoid or manual) |
| `filter` | Screen / disc / media filter |
| `venturi` | Fertigation venturi injector |
| `air_valve` | Air release / vacuum break valve |
| `flush_valve` | End-cap flush valve |

**`elevation_source` allowed values:** `gps_raw`, `gps_corrected`, `srtm`, `manual`, `surveyor_level`

### 4.4 Links (`links` — array)

Each link is a pipe, lateral, or fitting run between two nodes.

```json
{
  "id": "L01",
  "type": "mainline",
  "from_node": "N01",
  "to_node": "N02",
  "material": "hdpe_pe100",
  "nominal_diameter_mm": 63,
  "internal_diameter_m": 0.0545,
  "length_m": 87.4,
  "length_source": "gps_track",
  "pressure_class": "PN6",
  "hazen_williams_c": 140,
  "minor_losses": [
    { "fitting": "elbow_90", "count": 2, "k": 0.9 },
    { "fitting": "tee_branch", "count": 1, "k": 1.0 }
  ]
}
```

**`type` allowed values:**

| Type | Description |
|---|---|
| `mainline` | Main supply pipe |
| `submain` | Zone header pipe |
| `lateral` | Drip / sprinkler lateral |
| `riser` | Vertical pipe (bund crossing, standpipe) |
| `bypass` | Bypass around pump or PRV |

**`material` allowed values:** `pvc_upvc`, `hdpe_pe80`, `hdpe_pe100`, `gi`, `ms`, `cpvc`, `ldpe`

**`length_source` allowed values:** `gps_track`, `gps_straight`, `manual_tape`, `plan_measurement`

### 4.5 Zones (`zones` — array)

Each zone is an irrigated area served by one valve and one emitter type.

```json
{
  "id": "Z01",
  "label": "Coconut block north",
  "valve_node": "NV01",
  "boundary_polygon": {
    "type": "Polygon",
    "coordinates": [[[76.6410, 10.6518], [76.6430, 10.6518],
                     [76.6430, 10.6508], [76.6410, 10.6508], [76.6410, 10.6518]]]
  },
  "area_m2": 2000,
  "crop": {
    "type": "coconut",
    "variety": "local_tall",
    "planting_date": "2018-06-01",
    "age_years": 8,
    "row_spacing_m": 7.5,
    "plant_spacing_m": 7.5,
    "plant_count": 35
  },
  "emitter_layout": {
    "type": "drip",
    "emitter_model": "Netafim UniRam 4L",
    "flow_rate_lh": 4.0,
    "operating_pressure_kpa": 100,
    "emitters_per_plant": 2,
    "lateral_spacing_m": 7.5,
    "emitter_spacing_m": 0.5,
    "lateral_length_m": 25
  },
  "soil": {
    "texture": "red_laterite",
    "van_genuchten_alpha": 0.059,
    "van_genuchten_n": 1.48,
    "theta_r": 0.065,
    "theta_s": 0.41,
    "ks_mday": 0.62,
    "data_source": "default_palakkad_laterite",
    "lab_report_ref": null
  },
  "agronomy": {
    "kcb_ini": 0.60,
    "kcb_mid": 0.95,
    "kcb_end": 0.75,
    "mad_fraction": 0.50,
    "root_depth_max_m": 1.2,
    "ky_overall": 0.85,
    "ec_threshold_ds_m": 1.5,
    "ec_slope_pct_per_ds_m": 7.1
  },
  "fertigation": {
    "enabled": true,
    "n_kg_ha_season": 180,
    "p_kg_ha_season": 80,
    "k_kg_ha_season": 200,
    "target_ec_ds_m": 1.8,
    "target_ph": 6.0
  }
}
```

**`crop.type` allowed values:** `coconut`, `paddy`, `banana_nendran`, `banana_robusta`, `tomato`, `okra`, `capsicum`, `tapioca`, `areca`, `pepper`, `mango`, `other`

**`emitter_layout.type` allowed values:** `drip`, `sprinkler`, `micro_sprinkler`, `fogger`, `surface_furrow`, `surface_basin`, `surface_border`

### 4.6 Sensors (`sensors` — array)

```json
{
  "id": "S01",
  "type": "soil_moisture",
  "zone_id": "Z01",
  "location": { "lat": 10.6415, "lon": 76.6420, "elevation_m": 140.8 },
  "depths_cm": [15, 30, 60],
  "make": "Decagon 5TM",
  "lora_dev_eui": "70B3D57ED0049A2C",
  "installation_date": null,
  "notes": "Place 30 cm from coconut base, upslope side"
}
```

**`type` allowed values:** `soil_moisture`, `tensiometer`, `pressure_transducer`, `flow_meter`, `water_level`, `ec_ph_probe`, `aws_station`, `rain_gauge`

### 4.7 Weather (`weather`)

```json
{
  "nearest_imd_station_id": "43066",
  "nearest_imd_station_name": "Palakkad",
  "distance_km": 12.3,
  "nasa_power_lat": 10.6521,
  "nasa_power_lon": 76.6401,
  "design_rainfall_mm_year": 850,
  "design_eto_mm_day_peak": 5.8,
  "design_eto_mm_day_annual_avg": 4.1,
  "preferred_source": "open_meteo_era5"
}
```

### 4.8 Design Constraints (`design_constraints`)

```json
{
  "max_velocity_ms": 1.8,
  "min_emitter_pressure_kpa": 70,
  "max_emitter_pressure_kpa": 350,
  "min_eu_pct": 85,
  "max_system_flow_m3h": 5.0,
  "irrigation_window_start": "04:00",
  "irrigation_window_end": "07:00",
  "max_simultaneous_zones": 2,
  "budget_inr": 350000,
  "optimisation_priority": "balanced"
}
```

**`optimisation_priority` allowed values:** `cost`, `uniformity`, `yield`, `energy`, `balanced`

### 4.9 Attachments (`attachments` — array)

```json
{
  "id": "att_001",
  "type": "photo",
  "subject": "pump_nameplate",
  "node_ref": "N01",
  "filename": "pump_nameplate_N01.jpg",
  "captured_at": "2026-06-29T09:12:45+05:30",
  "gps": { "lat": 10.6521, "lon": 76.6401 },
  "storage_url": null,
  "local_path": "attachments/att_001.jpg"
}
```

**`type` allowed values:** `photo`, `video`, `voice_note`, `lab_report_pdf`, `existing_plan_pdf`, `gps_track_gpx`

**`subject` allowed values:** `pump_nameplate`, `motor_label`, `filter_nameplate`, `emitter_label`, `soil_profile`, `field_overview`, `existing_pipe`, `borewell`, `sump`, `general`

---

## 5. Mobile Survey App — Field by Field UX Flow

The installer follows a guided wizard. Each screen collects exactly the data needed for the next solver step. No screen shows more than 5 input fields.

```
Screen 1 — Farm identity
  • Farm name (text)
  • Owner name + phone (text + phone)
  • Survey number, block, village (text; auto-fill from GPS reverse geocode)
  • Area (ha) — draw polygon on map OR enter manually
  → GPS polygon area auto-calculated

Screen 2 — Water source
  • Source type (dropdown)
  • Tap location on map → GPS captured
  • Borewell depth / sump volume (conditional fields)
  • Water EC / pH (optional; can be added later)

Screen 3 — Pump & motor
  • Photo of nameplate → OCR extracts HP, make, model
  • Confirm / correct OCR result
  • Pump curve: enter 3 points (shutoff, design, runout) OR scan QR on pump
  • Motor phase (radio: single / 3-phase)

Screen 4 — Pipe network (map interaction)
  • Tap to place nodes (type picker appears on tap)
  • Drag between nodes to draw pipe link
  • Tap a link → assign diameter + material from dropdown
  • GPS track mode: walk the pipe route → link length auto-measured

Screen 5 — Zones (repeat per zone)
  • Draw zone polygon on map
  • Crop type + variety (searchable dropdown)
  • Emitter type + model (scan emitter barcode OR dropdown)
  • Soil texture (photo → AI estimate OR dropdown)

Screen 6 — Sensors (repeat per sensor)
  • Sensor type (dropdown)
  • Tap location on map
  • Scan LoRaWAN DevEUI from node sticker (QR scan)
  • Installation depth(s) (for soil moisture)

Screen 7 — Design constraints
  • Budget (₹ — number pad)
  • Irrigation window (time picker)
  • Priority slider: Cost ←→ Yield

Screen 8 — Review & submit
  • Summary: X nodes, Y links, Z zones, N sensors
  • Completeness indicator: missing required fields highlighted
  • "Save offline" or "Submit to cloud" (auto-chooses based on connectivity)
  • Download BoM preview (instant, from quick GGA run)
```

### Auto-fill from GPS

When a node is placed on the map:
- `elevation_m` → SRTM DEM lookup (bundled 30 m resolution tiles for Palakkad district; fallback to Google Elevation API)
- `elevation_source` → set to `srtm` or `gps_raw` automatically

When a pipe is drawn:
- `length_m` → computed from GPS distance along route; `length_source` = `gps_straight`
- If GPS track recorded while walking the route: `length_source` = `gps_track`

---

## 6. Import/Export Rules

### Export from Studio → Runtime (at install)

At commissioning time, the approved design (selected from NSGA-II top-3) is exported as an **As-Built FTS JSON**. This is the FTS survey JSON with additional fields populated:

```json
{
  "design_selected": true,
  "design_id": "<uuid>",
  "design_timestamp": "2026-06-29T16:00:00+05:30",
  "runtime_config": {
    "sensor_addresses": { "S01": "70B3D57ED0049A2C" },
    "valve_addresses": { "NV01": "70B3D57ED0049A2F" },
    "initial_setpoints": {
      "Z01": { "target_theta_m3m3": 0.28, "ec_target_ds_m": 1.8, "ph_target": 6.0 }
    },
    "schedule_window_start": "04:00",
    "schedule_window_end": "07:00"
  }
}
```

This JSON file is transferred to the edge controller via:
1. QR code (for small networks < 4 KB — edge controller scans during commissioning)
2. Bluetooth LE file transfer (React Native BLE to edge gateway)
3. Cloud push over MQTT (for remote re-configuration)

### EPANET .inp Import

The pre-processor supports reading EPANET 2.2 `.inp` files and converting them to FTS JSON. This allows importing existing designs from IRRICAD, IrriPro, or any EPANET-compatible tool. Unsupported EPANET sections (water quality, time patterns) are ignored with a warning.

### EPANET .inp Export

The post-processor can write the solved network as an EPANET `.inp` for verification in EPANET 2.2 GUI or for sharing with hydraulic engineers who use conventional tools.

---

## 7. Offline-First Sync Protocol

All survey data is saved locally first. Sync to cloud happens opportunistically.

```
Local storage:  SQLite on device  (FTS JSON rows + attachments as BLOBs)
Sync trigger:   Wi-Fi connect / 4G signal / manual "Sync now"
Conflict resolution:  "last-write-wins" per field; timestamps in ISO 8601 with TZ
Attachment sync: Progressive upload; large files (PDFs, videos) upload in background
Sync status field:  "draft" | "synced" | "conflict" | "pending_review"
```

Partial surveys (incomplete screens) are saved with `sync_status: "draft"` and can be resumed on the same or a different device (by signing in to the same account).

---

## 8. Integration with KoboToolbox / ODK

For FPO deployments where surveyors already use KoboToolbox or ODK Collect, FarmTwin provides:

- **XLSForm template** (`templates/farmtwin_survey.xls`) — a complete KoboToolbox form covering all required fields in the FTS schema
- **Webhook endpoint** — `POST /api/v1/surveys/kobo-ingest` — receives KoboToolbox webhook submissions and converts them to FTS JSON
- **ODK Central** — the same webhook endpoint accepts ODK Central submission JSON

**Limitations of KoboToolbox mode:**
- No map-based node placement (KoboToolbox GPS captures single point only)
- No barcode scan for LoRaWAN DevEUI (text entry instead)
- Polygon zone boundary must be pre-measured and entered as WKT
- Photo attachment size limited to 3 MB per KoboToolbox plan limits

The KoboToolbox path is recommended for large-scale FPO enrolment where surveyors are already trained; the native Studio app is recommended for new deployments where the installation person places sensors and devices.

---

## 9. Validation Rules

All FTS JSON inputs are validated on ingest (both local save and cloud upload) against these rules. Invalid documents are rejected with a structured error response listing every failed field.

| Rule ID | Field / condition | Error message |
|---|---|---|
| V01 | `schema_version` must be `"1.0"` | Unsupported schema version |
| V02 | `survey_id` must be valid UUID v4 | Invalid survey ID format |
| V03 | `farm.area_ha` must be 0.01–500 | Farm area out of range (0.01–500 ha) |
| V04 | Every node `location.elevation_m` must be –10 to 3000 | Elevation out of plausible range |
| V05 | At least one node of type `reservoir` or `pump` | No water source node found |
| V06 | Every `link.from_node` and `to_node` must reference an existing node ID | Dangling link reference |
| V07 | Network must be connected (all nodes reachable from source) | Disconnected network |
| V08 | `link.internal_diameter_m` must be 0.005–0.5 | Pipe diameter out of catalogue range |
| V09 | `link.length_m` must be 0.1–5000 | Pipe length out of range |
| V10 | `zone.emitter_layout.flow_rate_lh` must be 0.5–200 | Emitter flow out of range |
| V11 | `zone.emitter_layout.operating_pressure_kpa` must be 30–600 | Emitter pressure out of range |
| V12 | At least one `zone` must be defined | No irrigation zones defined |
| V13 | `design_constraints.min_eu_pct` must be 70–100 | EU target out of range |
| V14 | `weather.preferred_source` must be a known value | Unknown weather source |
| V15 | All GPS coordinates: lat –90 to 90, lon –180 to 180 | GPS coordinate out of range |
| V16 | `zone.crop.type` must be from the allowed crop list | Unknown crop type |
| V17 | Attachment `id` references must exist in `attachments` array | Broken attachment reference |
| V18 | `surveyed_by.phone` must match E.164 format | Invalid phone number format |

---

## 10. Example: Eruthempathy Pilot Farm

A minimal valid FTS JSON for the 15-acre pilot farm (6.07 ha net cultivated), coconut monocrop, single borewell, 5 HP pump, 2 zones.

```json
{
  "schema_version": "1.0",
  "survey_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "farm_id": "f0e1d2c3-b4a5-6789-0123-456789abcdef",
  "created_at": "2026-06-29T08:30:00+05:30",
  "updated_at": "2026-06-29T11:45:00+05:30",
  "surveyed_by": { "name": "Rajan K.", "phone": "+919876543210", "role": "installer" },
  "sync_status": "synced",

  "farm": {
    "name": "Eruthempathy Pilot Farm",
    "owner_name": "Arun T.",
    "owner_phone": "+919876543210",
    "village": "Eruthempathy", "taluk": "Chittur", "district": "Palakkad",
    "state": "Kerala", "country": "IN",
    "survey_number": "300", "block": "30",
    "area_ha": 6.07,
    "boundary_polygon": {
      "type": "Polygon",
      "coordinates": [[[76.6401,10.6521],[76.6445,10.6521],[76.6445,10.6498],[76.6401,10.6498],[76.6401,10.6521]]]
    },
    "terrain": "undulating", "slope_pct_approx": 2.5,
    "soil_type_primary": "red_laterite",
    "groundwater_ec_us_cm": 820,
    "power_availability": "3phase_415v",
    "electricity_tariff_inr_kwh": 5.80
  },

  "water_source": {
    "type": "borewell",
    "location": { "lat": 10.6521, "lon": 76.6401, "elevation_m": 142.5 },
    "borewell_depth_m": 120, "static_water_level_m": 35, "dynamic_water_level_m": 55,
    "yield_lpm": 800, "ec_us_cm": 820, "ph": 7.1,
    "sump_volume_litre": 25000, "sump_elevation_m": 141.2, "pump_installed": false
  },

  "nodes": [
    {
      "id": "N_SUMP", "type": "reservoir", "label": "Sump",
      "location": { "lat": 10.6521, "lon": 76.6401, "elevation_m": 141.2 },
      "elevation_source": "manual",
      "attributes": { "head_m": 141.2 }
    },
    {
      "id": "N_PUMP", "type": "pump", "label": "5HP main pump",
      "location": { "lat": 10.6521, "lon": 76.6402, "elevation_m": 141.3 },
      "elevation_source": "gps_corrected",
      "attributes": {
        "motor_hp": 5, "motor_phase": 3, "pump_make": "Kirloskar",
        "curve_shutoff_m": 38.0, "curve_design_q_m3s": 0.00111,
        "curve_design_h_m": 28.0, "curve_maxflow_m3s": 0.00194
      }
    },
    {
      "id": "N_FILTER", "type": "filter", "label": "120 mesh disc filter",
      "location": { "lat": 10.6522, "lon": 76.6403, "elevation_m": 141.4 },
      "elevation_source": "gps_corrected",
      "attributes": { "type": "disc", "mesh_size": 120, "clean_dp_kpa": 15 }
    },
    {
      "id": "N_J1", "type": "junction", "label": "Main junction",
      "location": { "lat": 10.6525, "lon": 76.6410, "elevation_m": 141.0 },
      "elevation_source": "srtm", "attributes": {}
    },
    {
      "id": "N_V1", "type": "zone_valve", "label": "Zone 1 valve — coconut north",
      "location": { "lat": 10.6528, "lon": 76.6415, "elevation_m": 140.8 },
      "elevation_source": "srtm", "attributes": { "type": "solenoid_latching", "dn_mm": 40 }
    },
    {
      "id": "N_V2", "type": "zone_valve", "label": "Zone 2 valve — coconut south",
      "location": { "lat": 10.6522, "lon": 76.6415, "elevation_m": 140.5 },
      "elevation_source": "srtm", "attributes": { "type": "solenoid_latching", "dn_mm": 40 }
    }
  ],

  "links": [
    {
      "id": "L_SUMP_PUMP", "type": "mainline",
      "from_node": "N_SUMP", "to_node": "N_PUMP",
      "material": "hdpe_pe100", "nominal_diameter_mm": 63,
      "internal_diameter_m": 0.0545, "length_m": 2.0,
      "length_source": "manual", "pressure_class": "PN6",
      "hazen_williams_c": 140, "minor_losses": []
    },
    {
      "id": "L_PUMP_FILTER", "type": "mainline",
      "from_node": "N_PUMP", "to_node": "N_FILTER",
      "material": "hdpe_pe100", "nominal_diameter_mm": 63,
      "internal_diameter_m": 0.0545, "length_m": 5.0,
      "length_source": "manual", "pressure_class": "PN6",
      "hazen_williams_c": 140, "minor_losses": [{"fitting": "elbow_90", "count": 1, "k": 0.9}]
    },
    {
      "id": "L_FILTER_J1", "type": "mainline",
      "from_node": "N_FILTER", "to_node": "N_J1",
      "material": "hdpe_pe100", "nominal_diameter_mm": 63,
      "internal_diameter_m": 0.0545, "length_m": 42.0,
      "length_source": "gps_straight", "pressure_class": "PN6",
      "hazen_williams_c": 140, "minor_losses": []
    },
    {
      "id": "L_J1_V1", "type": "submain",
      "from_node": "N_J1", "to_node": "N_V1",
      "material": "pvc_upvc", "nominal_diameter_mm": 50,
      "internal_diameter_m": 0.0446, "length_m": 35.0,
      "length_source": "gps_straight", "pressure_class": "PN4",
      "hazen_williams_c": 145, "minor_losses": []
    },
    {
      "id": "L_J1_V2", "type": "submain",
      "from_node": "N_J1", "to_node": "N_V2",
      "material": "pvc_upvc", "nominal_diameter_mm": 50,
      "internal_diameter_m": 0.0446, "length_m": 28.0,
      "length_source": "gps_straight", "pressure_class": "PN4",
      "hazen_williams_c": 145, "minor_losses": []
    }
  ],

  "zones": [
    {
      "id": "Z01", "label": "Coconut north", "valve_node": "N_V1",
      "area_m2": 17500,
      "boundary_polygon": {"type": "Polygon", "coordinates": [[[76.641,10.6528],[76.644,10.6528],[76.644,10.652],[76.641,10.652],[76.641,10.6528]]]},
      "crop": { "type": "coconut", "variety": "local_tall", "age_years": 8,
                "row_spacing_m": 7.5, "plant_spacing_m": 7.5, "plant_count": 311 },
      "emitter_layout": { "type": "drip", "emitter_model": "Netafim UniRam 4L",
                          "flow_rate_lh": 4.0, "operating_pressure_kpa": 100,
                          "emitters_per_plant": 2, "lateral_spacing_m": 7.5,
                          "emitter_spacing_m": 0.5, "lateral_length_m": 30 },
      "soil": { "texture": "red_laterite", "van_genuchten_alpha": 0.059,
                "van_genuchten_n": 1.48, "theta_r": 0.065, "theta_s": 0.41,
                "ks_mday": 0.62, "data_source": "default_palakkad_laterite", "lab_report_ref": null },
      "agronomy": { "kcb_mid": 0.95, "mad_fraction": 0.50, "root_depth_max_m": 1.2,
                    "ky_overall": 0.85, "ec_threshold_ds_m": 1.5, "ec_slope_pct_per_ds_m": 7.1 },
      "fertigation": { "enabled": true, "n_kg_ha_season": 180, "p_kg_ha_season": 80,
                       "k_kg_ha_season": 200, "target_ec_ds_m": 1.8, "target_ph": 6.0 }
    },
    {
      "id": "Z02", "label": "Coconut south", "valve_node": "N_V2",
      "area_m2": 13000,
      "boundary_polygon": {"type": "Polygon", "coordinates": [[[76.641,10.652],[76.644,10.652],[76.644,10.6512],[76.641,10.6512],[76.641,10.652]]]},
      "crop": { "type": "coconut", "variety": "local_tall", "age_years": 8,
                "row_spacing_m": 7.5, "plant_spacing_m": 7.5, "plant_count": 231 },
      "emitter_layout": { "type": "drip", "emitter_model": "Netafim UniRam 4L",
                          "flow_rate_lh": 4.0, "operating_pressure_kpa": 100,
                          "emitters_per_plant": 2, "lateral_spacing_m": 7.5,
                          "emitter_spacing_m": 0.5, "lateral_length_m": 28 },
      "soil": { "texture": "red_laterite", "van_genuchten_alpha": 0.059,
                "van_genuchten_n": 1.48, "theta_r": 0.065, "theta_s": 0.41,
                "ks_mday": 0.62, "data_source": "default_palakkad_laterite", "lab_report_ref": null },
      "agronomy": { "kcb_mid": 0.95, "mad_fraction": 0.50, "root_depth_max_m": 1.2,
                    "ky_overall": 0.85, "ec_threshold_ds_m": 1.5, "ec_slope_pct_per_ds_m": 7.1 },
      "fertigation": { "enabled": true, "n_kg_ha_season": 180, "p_kg_ha_season": 80,
                       "k_kg_ha_season": 200, "target_ec_ds_m": 1.8, "target_ph": 6.0 }
    }
  ],

  "sensors": [
    { "id": "S01", "type": "soil_moisture", "zone_id": "Z01",
      "location": { "lat": 10.6525, "lon": 76.6418, "elevation_m": 140.7 },
      "depths_cm": [15, 30, 60], "make": "Decagon 5TM",
      "lora_dev_eui": "70B3D57ED0049A2C", "installation_date": null,
      "notes": "30 cm from coconut base, upslope" },
    { "id": "S02", "type": "flow_meter", "zone_id": null,
      "location": { "lat": 10.6522, "lon": 76.6404, "elevation_m": 141.4 },
      "depths_cm": null, "make": "Arad Minol M-Pro",
      "lora_dev_eui": "70B3D57ED0049A2D", "installation_date": null,
      "notes": "On mainline after filter" }
  ],

  "weather": {
    "nearest_imd_station_id": "43066", "nearest_imd_station_name": "Palakkad",
    "distance_km": 12.3, "nasa_power_lat": 10.6521, "nasa_power_lon": 76.6401,
    "design_rainfall_mm_year": 850, "design_eto_mm_day_peak": 5.8,
    "design_eto_mm_day_annual_avg": 4.1, "preferred_source": "open_meteo_era5"
  },

  "design_constraints": {
    "max_velocity_ms": 1.8, "min_emitter_pressure_kpa": 70, "max_emitter_pressure_kpa": 350,
    "min_eu_pct": 85, "max_system_flow_m3h": 5.0,
    "irrigation_window_start": "04:00", "irrigation_window_end": "07:00",
    "max_simultaneous_zones": 1, "budget_inr": 350000, "optimisation_priority": "balanced"
  },

  "attachments": []
}
```

---

*End of survey-schema.md — version 1.0.0*

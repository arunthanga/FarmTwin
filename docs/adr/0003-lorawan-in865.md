# ADR-0003: LoRaWAN IN865 for Farm Wireless

**Date:** 2026-06-29  
**Status:** Accepted  

## Context
Farm sensor/valve nodes need > 300 m range, penetrate coconut/banana canopy, run on solar.
Options evaluated: LoRaWAN IN865, Wi-Fi mesh, NB-IoT, Zigbee.

## Decision
LoRaWAN IN865 (865–867 MHz India ISM band, license-free per WPC/TEC).
Self-hosted ChirpStack network server on the farm gateway (Raspberry Pi CM4 + SX1302 concentrator).

## Consequences
- **Good:** 500 m range, solar-compatible (µA sleep current), no recurring spectrum fees.
- **Good:** Self-hosted NS means offline operation during cellular outage.
- **Bad:** 250 bytes max payload per uplink; no real-time streaming.
- **Mitigation:** 15-min sample cycle with store-and-forward fits payload limit; critical alarms use confirmed uplinks.

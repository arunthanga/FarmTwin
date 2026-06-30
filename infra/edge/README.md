# FarmTwin Edge Decision Engine

C++17 runtime for Raspberry Pi 4 / CM4. Links against `libkrishiflow.so`.

## Responsibilities
- FAO-56 daily balance + irrigation trigger decision
- Zone sequencing (pump↔valve interlock)
- MQTT publish/subscribe (ChirpStack → sensors → cloud)
- Offline operation (30-day weather + parameter cache)
- OTA firmware update receive and verify (ED25519 signature)

## Build
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
```

See `docs/requirements.md §7` for full spec.

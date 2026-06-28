# 17 — Weather Data Integration (free & paid)

Public weather feeds complement the on-farm AWS
([13-...](13-sensors-and-instrumentation.md) §B4): they (a) gap-fill any missing AWS
variable, (b) cover farms without a full AWS, and (c) supply forecasts for predictive
scheduling. A **source-precedence layer** picks the best available source per variable
and tags provenance + quality.

## 1. FAO-56 input -> instrument -> public fallback

Every Penman-Monteith input ([12-...](12-solver-mathematics.md) §A5) is sourced from a
physical instrument first, then a public feed:

| PM variable | Primary instrument | Public-data fallback |
| --- | --- | --- |
| T_mean, T_min, T_max | AWS thermometer | NASA POWER `T2M*`, Open-Meteo, IMD |
| RH / e_a | hygrometer | NASA POWER `RH2M`, Open-Meteo |
| u2 (wind @ 2 m) | anemometer + wind vane | NASA POWER `WS2M`, Open-Meteo |
| Rn / Rs (radiation) | pyranometer | NASA POWER `ALLSKY_SFC_SW_DWN` (key gap-fill) |
| rainfall (effective P) | rain gauge | NASA POWER, IMD GKMS, Open-Meteo |
| theta (soil water) | soil-moisture sensor | OpenWeather AgroMonitoring soil layer |

**Radiation is the variable farmers least often measure**, yet it dominates ET — so
NASA POWER `ALLSKY_SFC_SW_DWN` is the default Rs source when no pyranometer is present.

## 2. Providers

| Provider | Cost | Strengths | Latency / use |
| --- | --- | --- | --- |
| **NASA POWER** | Free | Satellite/reanalysis daily, AG community (T2M, RH2M, WS2M, ALLSKY_SFC_SW_DWN, precip); best free **solar** source | 2-7 day latency -> historical + gap-fill, not real-time control |
| **Open-Meteo** | Free, no key (CC BY 4.0) | Forecast to 16 days + ERA5 archive from 1940; hourly T, RH, wind, radiation, soil; self-hostable (AGPL) | **default forecast feed**; offline-capable |
| **OpenWeather + AgroMonitoring** | Free tier + paid | Current/forecast weather; satellite NDVI + soil moisture/temp by field polygon (paid) | where ground soil sensors are sparse |
| **IMD GKMS / Agromet-DSS / Meghdoot** | Free (official India) | Block/district agromet advisories + observations | local authoritative source; credibility/partnership |
| **ECMWF/Copernicus ERA5, NOAA GEFS** | Free | Reanalysis / ensemble forecast | bias-corrected ET forecasting (ties to Mitra's GEFS work, [15-...](15-iitpkd-collaboration-brief.md)) |
| Visual Crossing, Tomorrow.io, WeatherAPI | Paid | Higher resolution / SLAs | drop-in providers behind the same interface |

### NASA POWER access (reference)

```
GET https://power.larc.nasa.gov/api/temporal/daily/point
    ?parameters=T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR
    &community=AG&latitude=<lat>&longitude=<lon>
    &start=YYYYMMDD&end=YYYYMMDD&format=JSON
```

## 3. Source-precedence layer

```
for each variable, each timestep:
    pick first available, QC-passing source in priority order:
        on-farm sensor (B6 pass)  >  configured public source  >  last-known-good  >  model estimate
    record { value, source, quality_flag, fetched_at }
```

Forecasts (Open-Meteo / GEFS) drive look-ahead scheduling (e.g., skip irrigation before
forecast rain — [18-...](18-iot-control-architecture.md) §E2). All public values pass the
same B6 QC checks ([13-...](13-sensors-and-instrumentation.md)) and cross-checks (e.g.,
gauge rain vs forecast) before use.

## 4. Module

A planned `weather/` provider layer: one adapter per source mapping to a **common
schema** (variable names, units), with a cache + offline mode for connectivity gaps.
Adapters: `nasapower`, `openmeteo`, `openweather_agro`, `imd_gkms`, `era5_gefs`. The
layer feeds [`fao56.py`](../krishiflow/fao56.py) and the twin
([14-...](14-digital-twin-data-assimilation.md)).

## 5. References

- NASA POWER API docs (power.larc.nasa.gov); daily ETo from POWER, *Agronomy* 2021,
  11(10), 2077.
- Open-Meteo API (open-meteo.com) — CC BY 4.0, ERA5 + forecast.
- OpenWeather AgroMonitoring — satellite NDVI/soil API.
- IMD Gramin Krishi Mausam Seva (GKMS) / Agromet-DSS / Meghdoot.
- Copernicus ERA5; NOAA GEFS.

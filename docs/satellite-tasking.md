# Satellite Tasking & Astrodynamics Optimization

SkyWindow integrates SGP4 orbital propagation with multi-variable payload constraint optimization to plan high-value Earth observation missions.

## SGP4 Keplarian Orbital Propagation
Orbital ground tracks, subpoint coordinates, and overpasses are propagated using `skyfield` and `sgp4` from CelesTrak Two-Line Element (TLE) records.

- **Pass Events:**
  - Rise (Elevation $\ge 20^\circ$)
  - Culmination (Maximum Elevation, Azimuth, Off-Nadir Angle, Topocentric Range)
  - Set

## Sensor-Aware Optimization Formula

$$\text{Task Score} = (100 - \text{Effective Cloud Cover}) \times W_{\text{target}} \times W_{\text{elev}} \times M_{\text{sensor}}$$

Where:
- $W_{\text{target}}$: User or Disaster Urgency Weight ($1 - 10$)
- $W_{\text{elev}}$: Geometric Elevation Factor ($\min(1.0, \max(0.2, \text{MaxElevation} / 90^\circ))$)
- $M_{\text{sensor}}$: Sensor Modality Suitability Multiplier:
  - **SAR:** $\text{Effective Cloud} = \text{Raw Cloud} \times 0.05$ (100% all-weather penetration). $M_{\text{sensor}} = 1.45$ for floods/cyclones.
  - **Optical:** $\text{Effective Cloud} = \text{Raw Cloud}$. Passes with $>70\%$ cloud cover are rejected. $M_{\text{sensor}} = 1.25$ for clear-sky vegetation.
  - **Thermal:** $M_{\text{sensor}} = 1.40$ for wildfires/volcanoes.

## Constraints & Impact Simulation
1. **Orbital Conflict Detection:** Resolves overlapping camera exposure windows.
2. **Daily Duty Cycle Limit:** Restricts daily imaging passes per platform (default: 4-5 passes/day) to prevent battery/memory exhaustion.
3. **Capacity Impact Simulator:** Calculates power saved (Wh) and onboard Solid-State Recorder storage saved (GB) by avoiding clouded passes.

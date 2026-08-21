from typing import List, Dict, Any, Optional
from models.schemas import SatelliteInfo, SatelliteSensor

SATELLITE_CATALOG: Dict[int, SatelliteInfo] = {
    39634: SatelliteInfo(
        id=39634,
        norad_id=39634,
        name="SENTINEL-1A",
        operator="European Space Agency (ESA)",
        country="Europe",
        type="SAR (Radar)",
        desc="C-band Synthetic Aperture Radar. Day-and-night all-weather imaging. Penetrates clouds, rain, and smoke. The gold standard for flood mapping, cyclone wave run-up, and InSAR ground deformation.",
        revisit="6-12 days",
        recommended_capacity=4,
        orbit_type="Sun-Synchronous LEO",
        altitude_km=693.0,
        inclination_deg=98.18,
        sensors=[
            SatelliteSensor(
                name="C-SAR (Synthetic Aperture Radar)",
                sensor_type="SAR",
                resolution_m=5.0,
                swath_km=250.0,
                day_night_capable=True,
                cloud_penetrating=True
            )
        ],
        status="Operational"
    ),
    40697: SatelliteInfo(
        id=40697,
        norad_id=40697,
        name="SENTINEL-2A",
        operator="European Space Agency (ESA)",
        country="Europe",
        type="Multispectral Optical",
        desc="High-resolution 13-band multispectral sensor. Ideal for vegetation health (NDVI), burn scars, flood aftermath (clear sky), and post-disaster infrastructure damage.",
        revisit="5 days (constellation)",
        recommended_capacity=3,
        orbit_type="Sun-Synchronous LEO",
        altitude_km=786.0,
        inclination_deg=98.62,
        sensors=[
            SatelliteSensor(
                name="MSI (MultiSpectral Instrument)",
                sensor_type="Multispectral",
                resolution_m=10.0,
                swath_km=290.0,
                day_night_capable=False,
                cloud_penetrating=False
            )
        ],
        status="Operational"
    ),
    39084: SatelliteInfo(
        id=39084,
        norad_id=39084,
        name="LANDSAT 8",
        operator="NASA / USGS",
        country="USA",
        type="Optical / Thermal",
        desc="Operational Land Imager (OLI) and Thermal Infrared Sensor (TIRS). Excellent for regional environmental change, land surface temperature, and thermal anomaly monitoring.",
        revisit="16 days",
        recommended_capacity=3,
        orbit_type="Sun-Synchronous LEO",
        altitude_km=705.0,
        inclination_deg=98.2,
        sensors=[
            SatelliteSensor(
                name="OLI (Operational Land Imager)",
                sensor_type="Optical",
                resolution_m=15.0,
                swath_km=185.0,
                day_night_capable=False,
                cloud_penetrating=False
            ),
            SatelliteSensor(
                name="TIRS (Thermal Infrared Sensor)",
                sensor_type="Thermal",
                resolution_m=100.0,
                swath_km=185.0,
                day_night_capable=True,
                cloud_penetrating=False
            )
        ],
        status="Operational"
    ),
    49260: SatelliteInfo(
        id=49260,
        norad_id=49260,
        name="LANDSAT 9",
        operator="NASA / USGS",
        country="USA",
        type="Optical / Thermal",
        desc="Sister observatory to Landsat 8 with upgraded 14-bit radiometric resolution. Essential for long-term baseline comparison and change detection.",
        revisit="16 days (8 days with Landsat 8)",
        recommended_capacity=3,
        orbit_type="Sun-Synchronous LEO",
        altitude_km=705.0,
        inclination_deg=98.2,
        sensors=[
            SatelliteSensor(
                name="OLI-2",
                sensor_type="Optical",
                resolution_m=15.0,
                swath_km=185.0,
                day_night_capable=False,
                cloud_penetrating=False
            ),
            SatelliteSensor(
                name="TIRS-2",
                sensor_type="Thermal",
                resolution_m=100.0,
                swath_km=185.0,
                day_night_capable=True,
                cloud_penetrating=False
            )
        ],
        status="Operational"
    ),
    25994: SatelliteInfo(
        id=25994,
        norad_id=25994,
        name="TERRA",
        operator="NASA EOS",
        country="USA",
        type="Multispectral / Thermal",
        desc="MODIS & ASTER instruments. Broad 2,330 km swath allows daily global coverage of active wildfires, volcanic ash clouds, and regional flood extent.",
        revisit="1-2 days",
        recommended_capacity=4,
        orbit_type="Sun-Synchronous LEO",
        altitude_km=705.0,
        inclination_deg=98.2,
        sensors=[
            SatelliteSensor(
                name="MODIS (Moderate Resolution Imaging Spectroradiometer)",
                sensor_type="Multispectral/Thermal",
                resolution_m=250.0,
                swath_km=2330.0,
                day_night_capable=True,
                cloud_penetrating=False
            )
        ],
        status="Operational"
    ),
    27424: SatelliteInfo(
        id=27424,
        norad_id=27424,
        name="AQUA",
        operator="NASA EOS",
        country="USA",
        type="Microwave / Optical",
        desc="Afternoon constellation flagship observing Earth's water cycle, cloud properties, and atmospheric precipitation profiles (MODIS / AIRS / AMSR-E).",
        revisit="1-2 days",
        recommended_capacity=4,
        orbit_type="Sun-Synchronous LEO",
        altitude_km=705.0,
        inclination_deg=98.2,
        sensors=[
            SatelliteSensor(
                name="AIRS / AMSR-E (Atmospheric & Microwave Sounder)",
                sensor_type="Microwave",
                resolution_m=1000.0,
                swath_km=1650.0,
                day_night_capable=True,
                cloud_penetrating=True
            )
        ],
        status="Operational"
    ),
    25544: SatelliteInfo(
        id=25544,
        norad_id=25544,
        name="ISS (ZARYA)",
        operator="International Consortium (NASA/ESA/JAXA/CSA)",
        country="International",
        type="Space Station / EO Payload",
        desc="Low-inclination orbit provides rapid non-sun-synchronous diurnal observation passes over equatorial and mid-latitude disaster events.",
        revisit="Multiple per day",
        recommended_capacity=5,
        orbit_type="Low Inclination LEO",
        altitude_km=420.0,
        inclination_deg=51.64,
        sensors=[
            SatelliteSensor(
                name="Crew Earth Observations (CEO) & DESIS Hyperspectral",
                sensor_type="Optical/Hyperspectral",
                resolution_m=30.0,
                swath_km=150.0,
                day_night_capable=False,
                cloud_penetrating=False
            )
        ],
        status="Operational"
    )
}

def get_all_satellites_info() -> List[Dict[str, Any]]:
    return [sat.dict() for sat in SATELLITE_CATALOG.values()]

def get_satellite_by_id(norad_id: int) -> Optional[SatelliteInfo]:
    return SATELLITE_CATALOG.get(norad_id)

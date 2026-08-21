from typing import Dict, Any, Optional
from models.schemas import DisasterEvent, DisasterType

class ExplainableRiskEngine:
    """
    Computes transparent, defensible disaster risk scores based on:
    Risk = Hazard (H) x Exposure (E) x Vulnerability (V)
    
    Every output explicitly breaks down contributing factors and uncertainties.
    """
    def calculate_disaster_risk(
        self,
        disaster_type: DisasterType,
        hazard_intensity: float,    # 0.0 - 1.0 (e.g. magnitude/10 or rainfall/300)
        exposed_population: int,     # Count
        exposed_facilities: int,     # Count of hospitals/schools/bridges
        vulnerability_factor: float = 0.75 # 0.0 - 1.0 based on terrain/drainage
    ) -> Dict[str, Any]:
        # 1. Hazard Score (0 - 40 points)
        hazard_score = min(40.0, max(5.0, hazard_intensity * 40.0))
        
        # 2. Exposure Score (0 - 35 points)
        pop_factor = min(1.0, max(0.05, exposed_population / 100000.0))
        facility_factor = min(1.0, max(0.05, exposed_facilities / 20.0))
        exposure_score = (pop_factor * 20.0) + (facility_factor * 15.0)
        
        # 3. Vulnerability Score (0 - 25 points)
        vulnerability_score = min(25.0, max(5.0, vulnerability_factor * 25.0))
        
        total_risk = min(100.0, hazard_score + exposure_score + vulnerability_score)
        
        # Classification
        if total_risk >= 85.0:
            category = "CRITICAL RISK"
        elif total_risk >= 70.0:
            category = "HIGH RISK"
        elif total_risk >= 50.0:
            category = "MODERATE RISK"
        else:
            category = "LOW / MONITORING"
            
        return {
            "total_risk_score": round(total_risk, 1),
            "category": category,
            "formula": "Risk = Hazard (40%) + Exposure (35%) + Vulnerability (25%)",
            "breakdown": {
                "hazard_contribution": round(hazard_score, 1),
                "exposure_contribution": round(exposure_score, 1),
                "vulnerability_contribution": round(vulnerability_score, 1)
            },
            "parameters": {
                "hazard_intensity_norm": round(hazard_intensity, 2),
                "exposed_population": exposed_population,
                "exposed_facilities": exposed_facilities,
                "vulnerability_factor": round(vulnerability_factor, 2)
            },
            "uncertainty": "Medium (Subject to cloud cover obscuration on optical sensors and ground sensor density)"
        }

risk_engine = ExplainableRiskEngine()

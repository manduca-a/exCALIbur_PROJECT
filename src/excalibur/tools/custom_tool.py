from crewai.tools import BaseTool
from typing import Type, Union
from pydantic import BaseModel, Field, field_validator
import os
import json
import requests
import ast
import re
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

from datetime import datetime, timedelta

class AmbulanceStateManager:
    """Manager class to handle ambulance states in the ambulances.json file"""
    
    @staticmethod
    def assign_ambulance(ambulance_id: int, duration_minutes: int):
        """
        Assigns an ambulance by marking it as 'occupied' and setting the expected free time based on the mission duration.
        """
        with open('ambulances.json', 'r') as f:
            data = json.load(f)
        
        for amb in data['ambulances']:
            if amb['id'] == ambulance_id:
                now = datetime.now()
                amb['state'] = 'occupied'
                amb['occupied_until'] = (now + timedelta(minutes=duration_minutes)).isoformat()
                break
        
        with open('ambulances.json', 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def release_ambulance(ambulance_id: int):
        """Releases an ambulance, marking it as 'available'"""
        with open('ambulances.json', 'r') as f:
            data = json.load(f)
        
        for amb in data['ambulances']:
            if amb['id'] == ambulance_id:
                amb['state'] = 'available'
                amb['occupied_until'] = None
                break
        
        with open('ambulances.json', 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def check_and_free_ambulances():
        """Periodically checks if occupied ambulances can become available"""
        with open('ambulances.json', 'r') as f:
            data = json.load(f)
        
        now = datetime.now()
        updated = False
        
        for amb in data['ambulances']:
            if amb['state'] == 'occupied' and amb['occupied_until']:
                occupied_until = datetime.fromisoformat(amb['occupied_until'])
                if now >= occupied_until:
                    amb['state'] = 'available'
                    amb['occupied_until'] = None
                    updated = True
        
        if updated:
            with open('ambulances.json', 'w') as f:
                json.dump(data, f, indent=2)

def _parse_int_field(v, field_name: str) -> int:
    """
        Converts to int a value that can come as:
        - pure int → returns directly
        - numeric string "2" → int("2") = 2
        - arithmetic expression "21+5+8+2" → ast.literal_eval = 36
        - fallback → sums all numbers found in the string
        """
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        v_stripped = v.strip()
        # Most common case: pure numeric string
        if v_stripped.isdigit():
            return int(v_stripped)
        # Simple arithmetic expression (only numbers and operators +−*/)
        if re.fullmatch(r'[\d\s\+\-\*\/\.]+', v_stripped):
            try:
                result = ast.literal_eval(v_stripped)
                return int(result)
            except Exception:
                pass
        # Fallback: sum all numbers found in the string
        numbers = re.findall(r'\d+', v_stripped)
        if numbers:
            return sum(int(n) for n in numbers)
    raise ValueError(f"Cannot parse '{field_name}' as integer: received {v!r}")


class AssignAmbulanceInput(BaseModel):
    ambulance_id: Union[int, str] = Field(
        ...,
        description="The numeric ID of the ambulance to assign (must be an integer)"
    )
    duration_minutes: Union[int, str] = Field(
        ...,
        description="Total mission duration in minutes (must be a computed integer, not an expression)"
    )

    # mode='before' → the validator runs BEFORE Pydantic attempts to cast the type,
    # thus intercepting the string before it is rejected by the schema.
    @field_validator('ambulance_id', mode='before')
    @classmethod
    def parse_ambulance_id(cls, v):
        return _parse_int_field(v, 'ambulance_id')

    @field_validator('duration_minutes', mode='before')
    @classmethod
    def parse_duration_minutes(cls, v):
        return _parse_int_field(v, 'duration_minutes')

class AmbulanceEtaInput(BaseModel):
    ambulances_addresses: str = Field(
        ...,
        description=(
            'A JSON-formatted string mapping ambulance names to their current coordinates. '
            'Example: \'{"Ambulance 1": "39.3505,16.2466", "Ambulance 2": "39.3585,16.2373"}\''
        )
    )
    patient_address: str = Field(
        ...,
        description="The exact address or location of the patient."
    )

class AssignAmbulanceTool(BaseTool):
    name: str = "assign_ambulance"
    description: str = (
        "Marks an ambulance as occupied for the total duration of the mission. "
        "Requires the ambulance numeric ID and the total mission time in minutes "
        "(travel + on-site + hospital). Always pass pre-computed integers, never expressions."
    )
    args_schema: Type[BaseModel] = AssignAmbulanceInput

    def _run(self, ambulance_id: int, duration_minutes: int) -> str:
        # At this point the values are already clean thanks to the field_validator
        AmbulanceStateManager.assign_ambulance(ambulance_id, duration_minutes)
        return (
            f"✓ Ambulance {ambulance_id} successfully assigned and marked as "
            f"occupied for {duration_minutes} minutes."
        )
    

class AmbulanceEtaTool(BaseTool):
    name: str = "Google Maps Traffic ETA Calculator"
    description: str = (
        "Crucial tool to calculate the Estimated Time of Arrival (ETA) in minutes considering real-time traffic conditions. "
        "Use this tool whenever you need to find the fastest ambulance to dispatch to a patient's location. "
        "It returns a detailed report comparing travel times for all provided ambulances."
    )
    args_schema: Type[BaseModel] = AmbulanceEtaInput

    def _run(self, ambulances_addresses: str, patient_address: str) -> str:
        try:
            
            amb_dict = json.loads(ambulances_addresses)

            # TODO: Alter coordinates in order to have something like: {"waypoint": {"location": {"latLng": {"latitude": 39.3505, "longitude": 16.2466}}}}
            # instead of {"waypoint": {"address": "39.435, 16.3465645"}}. This would decrease tokes consumption
            
            fastest: float = float('inf')
            chosen_ambulance: str = ""
            chosen_time: str = ""
            
            report = f"Traffic analysis for destination: {patient_address}\n"

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_API_KEY,
                "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status"
            }

            origins = []
            for lat_lng_str in amb_dict.values():
                lat_str, lng_str = lat_lng_str.split(',')
                origins.append({
                    "waypoint": {
                        "location": {
                            "latLng": {
                                "latitude": float(lat_str.strip()),
                                "longitude": float(lng_str.strip())
                            }
                        }
                    }
                })
            request_body = {
                "origins": origins,
                "destinations": [ # Notare che ora è una LISTA (destinations)
                    {"waypoint": {"address": patient_address}}
                ],
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE"
            }
            
            ROUTES_API_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
            
            response = requests.post(ROUTES_API_URL, json=request_body, headers=headers)
            
            if response.status_code == 200:
                matrix_data = response.json()
                
                amb_keys = list(amb_dict.keys())
                
                for element in matrix_data:
                    idx = element.get('originIndex', 0)
                    amb_id = amb_keys[idx]
                    
                    if 'duration' in element and 'distanceMeters' in element:
                        duration_seconds = int(element['duration'].rstrip('s'))
                        distance_meters = int(element['distanceMeters'])
                        
                        minutes = duration_seconds // 60
                        hours = minutes // 60
                        remaining_minutes = minutes % 60
                        
                        distance_km = distance_meters / 1000
                        
                        if hours > 0:
                            time_str = f"{hours}h {remaining_minutes}m"
                        else:
                            time_str = f"{minutes}m"
                        
                        distance_str = f"{distance_km:.1f} km"

                        report += f"- {amb_id}: ETA {time_str} ({distance_str})\n"

                        if duration_seconds < fastest:
                            fastest = duration_seconds
                            chosen_ambulance = amb_id
                            chosen_time = time_str
                    else:
                        report += f"- {amb_id}: ROUTE ERROR (Nessun percorso trovato)\n"
            else:
                return f"Error: API returned status {response.status_code} - {response.text}"

            if chosen_ambulance:
                report += f"\nCONCLUSION: The fastest unit is {chosen_ambulance} with an ETA of {chosen_time}."
            else:
                report += f"\nCONCLUSION: Could not determine fastest ambulance."
            
            return report
            
        except Exception as e:
            return f"Error during route calculation: {str(e)}. Make sure the input is a valid JSON string."
        

class HospitalLocatorInput(BaseModel):
    """Input schema for the Hospital Locator Tool"""

    hospitals_data: str = Field(
        ...,
        description=(
            'JSON-formatted string with hospital data including name, address, '
            'capacity, current_patients, and specialties.'
        )
    )
    patient_address: str = Field(
        ...,
        description="The exact address or location of the patient."
    )
    required_specialty: str = Field(
        ...,
        description="The medical specialty required (e.g., Cardiology, Trauma, Emergency Medicine)."
    )


class HospitalLocatorTool(BaseTool):
    name: str = "Hospital Locator Tool"
    description: str = (
        "Finds the best available hospital for a patient based on: "
        "free bed availability, required medical specialization, "
        "and real travel time from the patient's location."
    )
    args_schema: Type[BaseModel] = HospitalLocatorInput

    def _run(
        self,
        hospitals_data: str,
        patient_address: str,
        required_specialty: str,
    ) -> str:
        try:
            hospitals = json.loads(hospitals_data)

            # Filter hospitals with free beds
            available = [h for h in hospitals if h["capacity"] > h["current_patients"]]
            if not available:
                return "ERROR: No hospitals have free beds available."

            # Filter by specialty match (case-insensitive)
            specialty_lower = required_specialty.lower()
            matched = [
                h for h in available
                if any(specialty_lower in s.lower() for s in h["specialties"])
            ]

            candidates = matched if matched else available
            fallback_note = "" if matched else (
                f"\nNOTE: No hospital with '{required_specialty}' specialty found. "
                "Using all hospitals with free beds.\n"
            )

            report = (
                f"Hospital analysis for patient at: {patient_address}\n"
                f"Required specialty: {required_specialty}{fallback_note}\n"
            )

            # Use Google Routes API for ETAs (same approach as AmbulanceEtaTool)
            best_hospital = None
            best_time_s = float("inf")
            best_eta_str = ""

            for hospital in candidates:
                free_beds = hospital["capacity"] - hospital["current_patients"]
                specs = ", ".join(hospital["specialties"])

                payload = {
                    "origin": {"address": hospital["address"]},
                    "destination": {"address": patient_address},
                    "travelMode": "DRIVE",
                    "routingPreference": "TRAFFIC_AWARE",
                }
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": GOOGLE_API_KEY,
                    "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
                }

                response = requests.post(ROUTES_API_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if "routes" in data and data["routes"]:
                        route = data["routes"][0]
                        time_s = int(route["duration"].rstrip("s"))
                        dist_km = route["distanceMeters"] / 1000
                        time_min = time_s // 60
                        report += (
                            f"- {hospital['name']}: ETA {time_min}m ({dist_km:.1f} km) | "
                            f"Free beds: {free_beds} | Specialties: {specs}\n"
                        )
                        if time_s < best_time_s:
                            best_time_s = time_s
                            best_hospital = hospital
                            best_eta_str = f"{time_min}m"
                    else:
                        report += f"- {hospital['name']}: NO ROUTE FOUND\n"
                else:
                    report += f"- {hospital['name']}: API ERROR ({response.status_code})\n"

            if best_hospital:
                free_beds = best_hospital["capacity"] - best_hospital["current_patients"]
                report += (
                    f"\nCONCLUSION: Best hospital is '{best_hospital['name']}' "
                    f"at {best_hospital['address']}. "
                    f"ETA: {best_eta_str} | Free beds: {free_beds} | "
                    f"Specialties: {', '.join(best_hospital['specialties'])}"
                )
            else:
                report += "\nERROR: Could not calculate routes to any hospital."

            return report

        except Exception as e:
            return f"Error during hospital location: {str(e)}"        
from crewai.tools import BaseTool
from typing import Type, Union, Optional
from pydantic import BaseModel, Field, field_validator
import os
import json
import requests
import ast
import re
from pathlib import Path
from dotenv import load_dotenv
import random
import threading

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[3]
AMBULANCES_PATH = ROOT_DIR / "ambulances.json"
HOSPITALS_PATH = ROOT_DIR / "hospitals.json"
AMBULANCES_FILE_LOCK = threading.Lock()
HOSPITALS_FILE_LOCK = threading.Lock()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

from datetime import datetime, timedelta

class AmbulanceStateManager:
    """Manager class to handle ambulance states in the ambulances.json file"""
    
    @staticmethod
    def assign_ambulance(ambulance_id: int, duration_minutes: int, lock: Optional[threading.Lock] = None):
        """
        Assigns an ambulance by marking it as 'occupied' and setting the expected free time based on the mission duration.
        """
        if lock is None:
            lock = AMBULANCES_FILE_LOCK

        with lock:
            with AMBULANCES_PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)

            for amb in data['ambulances']:
                if amb['id'] == ambulance_id:
                    now = datetime.now()
                    amb['state'] = 'occupied'
                    amb['occupied_until'] = (now + timedelta(minutes=duration_minutes)).isoformat()
                    break

            with AMBULANCES_PATH.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    
    @staticmethod
    def release_ambulance(ambulance_id: int, lock: Optional[threading.Lock] = None):
        """Releases an ambulance, marking it as 'available'"""
        if lock is None:
            lock = AMBULANCES_FILE_LOCK

        with lock:
            with AMBULANCES_PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)

            for amb in data['ambulances']:
                if amb['id'] == ambulance_id:
                    amb['state'] = 'available'
                    amb['occupied_until'] = None
                    break

            with AMBULANCES_PATH.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    
    @staticmethod
    def check_and_free_ambulances(lock: Optional[threading.Lock] = None):
        """Periodically checks if occupied ambulances can become available"""
        if lock is None:
            lock = AMBULANCES_FILE_LOCK

        with lock:
            with AMBULANCES_PATH.open('r', encoding='utf-8') as f:
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
                with AMBULANCES_PATH.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)

    @staticmethod
    def move_ambulances(lock: Optional[threading.Lock] = None):
        """Simulates ambulances moving towards their destinations by updating their coordinates"""
        if lock is None:
            lock = AMBULANCES_FILE_LOCK

        with lock:
            with AMBULANCES_PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)

            for amb in data.get('ambulances', []):
                if amb.get('state') != 'available':
                    continue

                coords = amb.get('coordinates')
                if isinstance(coords, dict):
                    lat = float(coords.get('lat', coords.get('latitude', 0)))
                    lng = float(coords.get('lng', coords.get('longitude', 0)))
                    symb = 1 if random.random() < 0.5 else -1
                    lat += 0.001 * symb
                    lng += 0.001 * symb
                    amb['coordinates'] = {
                        'lat': round(lat, 6),
                        'lng': round(lng, 6),
                    }
                elif isinstance(coords, str):
                    lat, lng = map(float, coords.split(','))
                    symb = 1 if random.random() < 0.5 else -1
                    lat += 0.001 * symb
                    lng += 0.001 * symb
                    amb['coordinates'] = f"{lat:.6f},{lng:.6f}"
                else:
                    # Preserve data if the coordinate format is unexpected
                    continue

            with AMBULANCES_PATH.open('w', encoding='utf-8') as f:
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


class HospitalBedManager:
    """Manager class to handle hospital bed reservations in hospitals.json"""

    @staticmethod
    def reserve_bed(hospital_name: str, duration_minutes: int = 240, lock: Optional[threading.Lock] = None):
        """
        Reserves one bed at the given hospital by decrementing available_beds
        and adding a 'release_at' timestamp for that bed reservation.
        Default reservation: 4 hours (240 min).
        """
        if lock is None:
            lock = HOSPITALS_FILE_LOCK

        with lock:
            with HOSPITALS_PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)

            for hosp in data['hospitals']:
                if hosp['name'] == hospital_name:
                    if hosp['capacity']['available_beds'] > 0:
                        hosp['capacity']['available_beds'] -= 1
                        hosp['current_patients'] = hosp.get('current_patients', 0) + 1

                        # Track reservation expiry times (multiple beds can be reserved)
                        now = datetime.now()
                        release_time = (now + timedelta(minutes=duration_minutes)).isoformat()
                        hosp.setdefault('reserved_until', []).append(release_time)
                        break
                    else:
                        raise ValueError(f"Hospital '{hospital_name}' has no available beds.")

            with HOSPITALS_PATH.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

    @staticmethod
    def release_bed(hospital_name: str, lock: Optional[threading.Lock] = None):
        """Releases one bed at the given hospital (incrementing available_beds)."""
        if lock is None:
            lock = HOSPITALS_FILE_LOCK

        with lock:
            with HOSPITALS_PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)

            for hosp in data['hospitals']:
                if hosp['name'] == hospital_name:
                    if hosp['capacity']['available_beds'] < hosp['capacity']['total_beds']:
                        hosp['capacity']['available_beds'] += 1
                        hosp['current_patients'] = max(0, hosp.get('current_patients', 0) - 1)
                        break

            with HOSPITALS_PATH.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

    @staticmethod
    def check_and_free_beds(lock: Optional[threading.Lock] = None):
        """
        Periodically checks reserved beds and frees any whose reservation
        time has expired.
        """
        if lock is None:
            lock = HOSPITALS_FILE_LOCK

        with lock:
            with HOSPITALS_PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)

            now = datetime.now()
            updated = False

            for hosp in data['hospitals']:
                reservations = hosp.get('reserved_until', [])
                still_active = []
                freed = 0
                for ts in reservations:
                    if datetime.fromisoformat(ts) > now:
                        still_active.append(ts)
                    else:
                        freed += 1

                if freed > 0:
                    hosp['capacity']['available_beds'] = min(
                        hosp['capacity']['total_beds'],
                        hosp['capacity']['available_beds'] + freed
                    )
                    hosp['current_patients'] = max(0, hosp.get('current_patients', 0) - freed)
                    hosp['reserved_until'] = still_active
                    updated = True

            if updated:
                with HOSPITALS_PATH.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)

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
                "destinations": [
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

    hospitals_addresses: str = Field(
        ...,
        description=(
            'A JSON-formatted string mapping hospital names to their current coordinates, '
            'available beds, and specialties. Example: '
            '{"Hospital A": "39.3505,16.2466|4|Cardiology,Trauma", '
            '"Hospital B": "39.3585,16.2373|2|Emergency Medicine"}'
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


def _parse_hospital_entry(name: str, value: str) -> dict[str, object]:
    """Parse a hospital entry from the combined string format."""
    parts = [part.strip() for part in value.split("|")]
    coord_part = parts[0] if parts else ""
    lat_lng = coord_part.split(",") if "," in coord_part else ["", ""]
    latitude = float(lat_lng[0].strip()) if lat_lng[0] else 0.0
    longitude = float(lat_lng[1].strip()) if len(lat_lng) > 1 else 0.0

    available_beds = None
    specialties = []
    if len(parts) > 1 and parts[1].isdigit():
        available_beds = int(parts[1])
    if len(parts) > 2:
        specialties = [s.strip() for s in parts[2].split(",") if s.strip()]

    return {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "available_beds": available_beds,
        "specialties": specialties,
    }


class HospitalLocatorTool(BaseTool):
    name: str = "Hospital Locator Tool"
    description: str = (
        "Finds the best available hospital for a patient based on: "
        "required medical specialization, "
        "and real travel time from the patient's location."
    )
    args_schema: Type[BaseModel] = HospitalLocatorInput

    def _run(
        self,
        hospitals_addresses: str,
        patient_address: str,
        required_specialty: str,
    ) -> str:
        try:
            hospitals_raw = json.loads(hospitals_addresses)
            hospitals = [
                _parse_hospital_entry(name, value)
                for name, value in hospitals_raw.items()
            ]

            specialty_lower = required_specialty.lower()
            matched = [
                h for h in hospitals
                if any(specialty_lower in s.lower() for s in h["specialties"])
                and h["available_beds"] is not None and h["available_beds"] > 0
            ]

            candidates = matched if matched else [
                h for h in hospitals if h["available_beds"] is not None and h["available_beds"] > 0
            ]
            fallback_note = "" if matched else (
                f"\nNOTE: No hospital with '{required_specialty}' specialty found. "
                "Using all hospitals with available beds.\n"
            )

            if not candidates:
                return "ERROR: No hospitals with available beds were provided."

            report = (
                f"Hospital analysis for patient at: {patient_address}\n"
                f"Required specialty: {required_specialty}{fallback_note}\n"
            )

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_API_KEY,
                "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status",
            }

            origins = [
                {
                    "waypoint": {
                        "location": {
                            "latLng": {
                                "latitude": h["latitude"],
                                "longitude": h["longitude"],
                            }
                        }
                    }
                }
                for h in candidates
            ]

            request_body = {
                "origins": origins,
                "destinations": [
                    {"waypoint": {"address": patient_address}}
                ],
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE",
            }

            routes_matrix_url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
            response = requests.post(routes_matrix_url, json=request_body, headers=headers)
            if response.status_code != 200:
                return f"Error: API returned status {response.status_code} - {response.text}"

            matrix_data = response.json()
            elements = []
            if isinstance(matrix_data, dict):
                if "routeMatrixElements" in matrix_data:
                    elements = matrix_data["routeMatrixElements"]
                elif "rows" in matrix_data:
                    for row in matrix_data["rows"]:
                        elements.extend(row.get("elements", []))
                elif "originIndex" in matrix_data:
                    elements = [matrix_data]
            elif isinstance(matrix_data, list):
                elements = matrix_data

            best_hospital = None
            best_time_s = float("inf")
            best_eta_str = ""

            for element in elements:
                origin_index = element.get("originIndex", 0)
                hospital = candidates[origin_index]
                status_value = element.get("status", "UNKNOWN")
                if isinstance(status_value, dict):
                    status_str = status_value.get("code") or status_value.get("message") or ""
                else:
                    status_str = str(status_value)

                duration_raw = element.get("duration", 0)
                if isinstance(duration_raw, dict):
                    duration_seconds = int(duration_raw.get("seconds", 0))
                elif isinstance(duration_raw, str):
                    duration_seconds = int(duration_raw.rstrip("s")) if duration_raw else 0
                else:
                    duration_seconds = int(duration_raw or 0)

                distance_raw = element.get("distanceMeters", element.get("distance_meters", 0))
                if isinstance(distance_raw, dict):
                    distance_meters = int(distance_raw.get("value", 0))
                else:
                    distance_meters = int(distance_raw or 0)

                if status_str not in {"OK", "ok", "Ok"} and duration_seconds == 0 and distance_meters == 0:
                    display_status = status_str or json.dumps(status_value)
                    report += f"- {hospital['name']}: ROUTE ERROR ({display_status})\n"
                    continue

                distance_raw = element.get("distanceMeters", element.get("distance_meters", 0))
                distance_meters = int(distance_raw or 0)
                minutes = duration_seconds // 60
                hours = minutes // 60
                remaining_minutes = minutes % 60
                distance_km = distance_meters / 1000
                time_str = f"{hours}h {remaining_minutes}m" if hours > 0 else f"{minutes}m"

                report += (
                    f"- {hospital['name']}: ETA {time_str} ({distance_km:.1f} km) | "
                    f"Available beds: {hospital['available_beds']} | "
                    f"Specialties: {', '.join(hospital['specialties'])}\n"
                )

                if duration_seconds < best_time_s:
                    best_time_s = duration_seconds
                    best_hospital = hospital
                    best_eta_str = time_str

            if best_hospital:
                report += (
                    f"\nCONCLUSION: Best hospital is '{best_hospital['name']}' "
                    f"with ETA {best_eta_str}, available beds: {best_hospital['available_beds']}, "
                    f"specialties: {', '.join(best_hospital['specialties'])}."
                )
            else:
                report += "\nERROR: Could not calculate routes to any hospital."

            return report

        except Exception as e:
            return f"Error during hospital location: {str(e)}"        
        

class ReserveHospitalBedInput(BaseModel):
    hospital_name: str = Field(
        ...,
        description="The exact name of the hospital to reserve a bed at."
    )
    duration_minutes: Union[int, str] = Field(
        240,
        description="How long to hold the bed reservation (default 240 minutes / 4 hours)."
    )

    @field_validator('duration_minutes', mode='before')
    @classmethod
    def parse_duration(cls, v):
        return _parse_int_field(v, 'duration_minutes')


class ReserveHospitalBedTool(BaseTool):
    name: str = "reserve_hospital_bed"
    description: str = (
        "Reserves one bed at a hospital after the hospital_locator has chosen it. "
        "Decrements the hospital's available_beds. Call this AFTER selecting the "
        "hospital and pass the hospital's exact name and the estimated mission "
        "duration in minutes."
    )
    args_schema: Type[BaseModel] = ReserveHospitalBedInput

    def _run(self, hospital_name: str, duration_minutes: int = 240) -> str:
        try:
            HospitalBedManager.reserve_bed(hospital_name, duration_minutes)
            return (
                f"✓ Bed reserved at '{hospital_name}' for {duration_minutes} minutes. "
                f"The hospital's available_beds count has been decremented."
            )
        except ValueError as e:
            return f"✗ {str(e)}"
        except Exception as e:
            return f"✗ Error reserving bed: {str(e)}"        
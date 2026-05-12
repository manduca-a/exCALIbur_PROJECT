from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import googlemaps
import os
import json # <--- Nuova importazione necessaria
from dotenv import load_dotenv

load_dotenv()

gmaps = googlemaps.Client(key=os.environ.get("GOOGLE_API_KEY"))

class AmbulanceEtaInput(BaseModel):
    """Input schema for the Ambulance ETA Tool"""
    
    ambulances_addresses: str = Field(
        ..., 
        description='A JSON-formatted string mapping ambulance IDs to their current addresses. Example: \'{"Alpha": "Via Roma 1, Milano", "Bravo": "Piazza Duomo, Milano"}\''
    )
    patient_address: str = Field(
        ..., 
        description="The exact address or location of the patient."
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
            
            origins = list(amb_dict.values())
            distances = gmaps.distance_matrix(origins=origins, destinations=[patient_address], mode='driving')
            
            fastest: float = float('inf')
            chosen_ambulance: str = ""
            chosen_time: str = ""
            
            report = f"Traffic analysis for destination: {patient_address}\n"

            for i, (amb_id, address) in enumerate(amb_dict.items()):
                path = distances['rows'][i]['elements'][0]
                
                if path['status'] == 'OK':
                    time_in_seconds = path['duration']['value']
                    time_str = path['duration']['text']
                    distance = path['distance']['text']

                    report += f"- {amb_id}: ETA {time_str} ({distance})\n"

                    if time_in_seconds < fastest:
                        fastest = time_in_seconds
                        chosen_ambulance = amb_id
                        chosen_time = time_str
                else:
                    report += f"- {amb_id}: ROUTE ERROR\n"

            report += f"\nCONCLUSION: The fastest unit is {chosen_ambulance} with an ETA of {chosen_time}."
            return report
            
        except Exception as e:
            return f"Error during route calculation: {str(e)}. Make sure the input is a valid JSON string."
from crewai.tools import tool
import googlemaps
import os

from typing import Dict, Any

gmaps = googlemaps.Client(key=os.environ.get("GOOGLE_MAPS_API_KEY"))

@tool("Google Maps calculator")
def ambulance_eta_calculator(ambulances_addresses: Dict[str, str], patient_address: str) -> str:
    """
    Tool to calculate the Estimated Time of Arrival (ETA) considering real-time traffic.
    You must provide 'ambulances_addresses' (a dictionary, e.g., {"Alpha": "Via Roma 1", "Bravo": "Via Milano 2"})
    and 'patient_address' (the destination address as a string).
    Returns a detailed report on the arrival times.
    """
    try:
        origins = list(ambulances_addresses.values())
        distances = gmaps.distance_matrix(origins=origins, destinations=[patient_address], mode='driving')
        
        fastest: float = float('inf')
        chosen_ambulance: str = ""
        chosen_time: str = ""
        
        # Prepariamo il testo da restituire all'Intelligenza Artificiale
        report = f"Traffic analysis for destination: {patient_address}\n"

        # Corretto: ambulances_addresses al posto di ambulances_positions
        for i, (amb_id, address) in enumerate(ambulances_addresses.items()):
            path: Dict[str, Any] = distances['rows'][i]['elements'][0]
            
            if path['status'] == 'OK':
                time_in_seconds: int = path['duration']['value']
                time_str: str = path['duration']['text']
                distance: str = path['distance']['text']

                report += f"- {amb_id}: ETA {time_str} ({distance})\n"

                if time_in_seconds < fastest:
                    fastest = time_in_seconds
                    chosen_ambulance = amb_id
                    chosen_time = time_str
            else:
                report += f"- {amb_id}: ROUTE ERROR\n"

        # Corretto: Aggiunto il return fondamentale per l'Agente!
        report += f"\nCONCLUSION: The fastest unit is {chosen_ambulance} with an ETA of {chosen_time}."
        return report
        
    except Exception as e:
        return f"Errore nel calcolo del percorso: {str(e)}"
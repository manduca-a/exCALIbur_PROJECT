import json
import random
from typing import Dict, Any, Tuple

def load_ambulances(filename: str = 'ambulances.json') -> Dict[str, Any]:
    """Carica le ambulanze dal JSON."""
    with open(filename, 'r') as f:
        return json.load(f)

def save_ambulances(data: Dict[str, Any], filename: str = 'ambulances.json') -> None:
    """Salva le ambulanze nel JSON."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def simulate_movement(ambulanze_data: Dict[str, Any], max_variation: float = 0.01) -> Dict[str, Any]:
    """
    Simula il movimento delle ambulanze variando le coordinate.
    
    Args:
        ambulanze_data: Dati delle ambulanze caricate da JSON
        max_variation: Massima variazione in coordinate (default ~1km per cambi di via)
    
    Returns:
        Dati aggiornati con coordinate variate
    """
    for ambulanza in ambulanze_data['ambulanze']:
        # Varia lat e lng con valori random tra -max_variation e +max_variation
        ambulanza['coordinate']['lat'] += random.uniform(-max_variation, max_variation)
        ambulanza['coordinate']['lng'] += random.uniform(-max_variation, max_variation)
    
    return ambulanze_data

def get_address_from_coordinates(gmaps_client, lat: float, lng: float) -> str:
    """
    Converte coordinate in indirizzo tramite reverse geocoding di Google Maps.
    
    Args:
        gmaps_client: Client di googlemaps autenticato
        lat: Latitudine
        lng: Longitudine
    
    Returns:
        Indirizzo formattato
    """
    try:
        result = gmaps_client.reverse_geocode((lat, lng))
        if result:
            return result[0]['formatted_address']
        return f"{lat}, {lng}"
    except Exception as e:
        print(f"Errore nel reverse geocoding: {e}")
        return f"{lat}, {lng}"

def get_ambulance_addresses(gmaps_client, ambulanze_data: Dict[str, Any]) -> Dict[int, str]:
    """
    Ottiene gli indirizzi di tutte le ambulanze dalle loro coordinate.
    
    Args:
        gmaps_client: Client di googlemaps autenticato
        ambulanze_data: Dati delle ambulanze
    
    Returns:
        Dizionario con id ambulanza -> indirizzo
    """
    addresses = {}
    for ambulanza in ambulanze_data['ambulanze']:
        lat = ambulanza['coordinate']['lat']
        lng = ambulanza['coordinate']['lng']
        addresses[ambulanza['id']] = get_address_from_coordinates(gmaps_client, lat, lng)
    return addresses

def update_ambulanze_status(ambulanze_data: Dict[str, Any], ambulanza_id: int, stato: str) -> Dict[str, Any]:
    """Aggiorna lo stato di un'ambulanza."""
    for ambulanza in ambulanze_data['ambulanze']:
        if ambulanza['id'] == ambulanza_id:
            ambulanza['stato'] = stato
            break
    return ambulanze_data

# Esempio di utilizzo
if __name__ == "__main__":
    # Carica ambulanze
    data = load_ambulances()
    print("Ambulanze iniziali:")
    print(json.dumps(data, indent=2))
    
    # Simula movimento (1km di variazione = cambio via)
    print("\nSimulazione movimento...")
    data = simulate_movement(data, max_variation=0.01)
    print(json.dumps(data, indent=2))
    
    # Salva
    save_ambulances(data)
    print("\nAmbulanze salvate!")

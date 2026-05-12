import googlemaps
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.spinner import Spinner
import time
from typing import Dict, Any, Optional, List, Tuple, Union

from utils import load_ambulances, simulate_movement, save_ambulances, get_ambulance_addresses

# Initialize rich console
console = Console()

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY')

gmaps = googlemaps.Client(key=API_KEY)

console.print("[bold cyan]Ambulance Dispatch System[/bold cyan]")
patience_address = console.input("[bold yellow]Where is the patient located? [/bold yellow]")

ambulances_data = load_ambulances()

# simulate movement of ambulances to get more realistic results
ambulances_data = simulate_movement(ambulances_data, max_variation=0.01)

# Save the updated ambulance data back to the JSON file
save_ambulances(ambulances_data)

# Get addresses from coordinates using reverse geocoding
with console.status("[bold green]Fetching ambulance locations...", spinner="dots"):
    ambulances_positions = get_ambulance_addresses(gmaps, ambulances_data)
    ambulances_positions_list = list(ambulances_positions.values())

console.print()

try:
    with console.status("[bold green]Calculating routes...", spinner="dots"):
        distances = gmaps.distance_matrix(origins=ambulances_positions_list, destinations=[patience_address], mode='driving')
    
    fastest: float = float('inf')
    chosen_ambulance: str = ""
    chosen_time: str = ""
    
    # Create table for results
    table: Table = Table(title="[bold]Route Results[/bold]", show_header=True, header_style="bold magenta")
    table.add_column("Ambulance", style="cyan")
    table.add_column("Address", style="white")
    table.add_column("Arrival Time", style="yellow")
    table.add_column("Distance", style="green")

    for i, (amb_id, address) in enumerate(ambulances_positions.items()):
        path: Dict[str, Any] = distances['rows'][i]['elements'][0]
        
        if path['status'] == 'OK':
            time_in_seconds: int = path['duration']['value']
            time_str: str = path['duration']['text']
            distance: str = path['distance']['text']

            table.add_row(f"Ambulance {amb_id}", address, time_str, distance)
            
            if time_in_seconds < fastest:
                fastest = time_in_seconds
                chosen_ambulance = f"Ambulance {amb_id}"
                chosen_time = time_str
        else:
            table.add_row(f"Ambulance {amb_id}", address, "[red]ERROR[/red]", "[red]N/A[/red]")

    console.print(table)
    console.print()
    
    # Display final decision in a panel
    panel: Panel = Panel(
        f"[bold green]DISPATCH DECISION[/bold green]\n\n"
        f"Send: [bold cyan]{chosen_ambulance}[/bold cyan]\n"
        f"Estimated arrival: [bold yellow]{chosen_time}[/bold yellow]",
        style="green"
    )
    console.print(panel)

except Exception as e:
    console.print(f"[bold red]Error: {e}[/bold red]")
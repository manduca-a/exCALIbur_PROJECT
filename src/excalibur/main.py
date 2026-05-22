#!/usr/bin/env python
import sys
import warnings
import json
from datetime import datetime
import threading
import time
import random
from pathlib import Path


from excalibur.crew import Excalibur
from excalibur.simulator_crew import SimulatorCrew
from excalibur.tools.custom_tool import AmbulanceStateManager, HospitalBedManager

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

ROOT_DIR = Path(__file__).resolve().parents[2]
AMBULANCES_PATH = ROOT_DIR / "ambulances.json"
HOSPITALS_PATH = ROOT_DIR / "hospitals.json"

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def load_json_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_text_output(output) -> str:
    if hasattr(output, "raw"):
        return str(output.raw)
    return str(output)

def background_ambulance_checker(stop_event: threading.Event):
    """
    Background thread that checks every 30 seconds if any occupied ambulances
    should be released (when their mission duration expires).
    """
    while not stop_event.is_set():
        try:
            AmbulanceStateManager.check_and_free_ambulances()
        except Exception as e:
            print(f"Error in background ambulance checker: {e}")
        stop_event.wait(30)  # Check every 30 seconds, but wake early on shutdown

ambulances_file_lock = threading.Lock()
hospitals_file_lock = threading.Lock()


def background_hospital_bed_checker(stop_event: threading.Event):
    """
    Background thread that checks every 60 seconds if any reserved beds
    should be released (when their reservation duration expires).
    """
    while not stop_event.is_set():
        try:
            HospitalBedManager.check_and_free_beds()
        except Exception as e:
            print(f"Error in background hospital bed checker: {e}")
        stop_event.wait(60)  # Check every 60 seconds

def process_emergency_in_parallel(call_index, call_transcription, stop_event: threading.Event):
    """
    Worker function executed inside a dedicated thread to process a single medical emergency
    without locking the main telephone simulator line.
    """
    try:
        if stop_event.is_set():
            return

        with ambulances_file_lock:
            ambulances_data = load_json_file(AMBULANCES_PATH)

        ambulances_data_str = { # Only include available ambulances, format: "Ambulance Name": "Lat,Lng"
            amb["name"]: f"{amb['coordinates']['lat']},{amb['coordinates']['lng']}"
            for amb in ambulances_data["ambulances"]
            if amb["state"] == "available"
        }
        
        if not ambulances_data_str:
            print(f"[System Warning] Call #{call_index} put on hold: No ambulances available at this time.")
            return
        
        with hospitals_file_lock:
            hospitals_data = load_json_file(HOSPITALS_PATH)

        # Build hospital data in the format the HospitalLocatorTool expects:
        # "Hospital Name": "lat,lng|available_beds|specialty1,specialty2,..."
        hospitals_data_str = {
            hosp["name"]: (
                f"{hosp['coordinates']['lat']},{hosp['coordinates']['lng']}"
                f"|{hosp['capacity']['available_beds']}"
                f"|{','.join(hosp['specialties'])}"
            )
            for hosp in hospitals_data["hospitals"]
            if hosp["capacity"]["available_beds"] > 0
        }

        if not hospitals_data_str:
            print(f"[System Warning] Call #{call_index} put on hold: No hospitals with available capacity at this time.")
            return

        inputs = {
            'call_transcription': call_transcription,
            'ambulances': json.dumps(ambulances_data_str),
            'hospitals': json.dumps(hospitals_data_str)
        }
        
        print(f"[Thread-Call-{call_index}] Excalibur Crew is now processing Call #{call_index}...")
        Excalibur().crew().kickoff(inputs=inputs)
        print(f"[Thread-Call-{call_index}] Emergency Call #{call_index} successfully processed.")
        
    except Exception as e:
        import traceback
        print(f"Error processing Call #{call_index} inside parallel thread: {e}")
        print(f"[FULL TRACEBACK]")
        traceback.print_exc()

def phone_line_simulator(stop_event: threading.Event, first_time=True):
    """
    Infinite loop thread simulating real incoming emergency phone calls at random intervals.
    Each incoming call triggers a separate Excalibur instance to process the crisis concurrently.
    """
    print("Phone line simulator is active. Waiting for random incoming calls...")
    call_index = 1
    
    while not stop_event.is_set():
        try:
            
            seconds_to_wait = random.randint(60,90)                
            sys.stdout.write(f"\r[System] Next emergency call #{call_index} will arrive in {seconds_to_wait} seconds... ")
            
            if stop_event.wait(seconds_to_wait):
                break
            
            print(f"[System] INCOMING EMERGENCY CALL #{call_index}")
            
            # Kicking off the Simulator Crew to autonomously generate problem descriptions and positions
            call_output = SimulatorCrew().crew().kickoff()
            call_transcription = get_text_output(call_output)
            
            print(f"[System] Live Call Transcript received from Simulator for Call #{call_index}:\n\"{call_transcription}\"")
            
            # Spin up a separate thread for Excalibur processing to avoid blocking the main line loop
            medical_thread = threading.Thread(
                target=process_emergency_in_parallel,
                args=(call_index, call_transcription, stop_event),
                daemon=True,
                name=f"MedicalThread-{call_index}"
            )
            medical_thread.start()
            
            call_index += 1
            
        except Exception as e:
            print(f"Error in phone line simulator loop: {e}")
            if stop_event.wait(10):
                break

def run():
    """
    Run the crew.
    """
    stop_event = threading.Event()

    # Start background ambulance checker thread
    checker_thread = threading.Thread(
        target=background_ambulance_checker,
        daemon=True,
        args=(stop_event,)
    )
    checker_thread.start()
    print("Background ambulance checker started (checks every 30 seconds)")

    # Start background hospital bed checker thread       
    bed_checker_thread = threading.Thread(                
        target=background_hospital_bed_checker,           
        daemon=True,                                       
        args=(stop_event,)                                 
    )                                                       
    bed_checker_thread.start()                             
    print("Background hospital bed checker started (checks every 60 seconds)")  


    # Start autonomous random phone call generator thread
    phone_thread = threading.Thread(
        target=phone_line_simulator,
        daemon=True,
        name="PhoneLineSimulator",
        args=(stop_event, True),
    )
    phone_thread.start()
    print("Autonomous phone line simulator started")

    # Keep the main process alive to allow background daemon threads to execute
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the emergency management system. Shutting down process.")
        stop_event.set()
        phone_thread.join(timeout=5)
        checker_thread.join(timeout=5)
        bed_checker_thread.join(timeout=5) 
        print("Shutdown signal sent to background threads.")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        Excalibur().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        Excalibur().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }

    try:
        Excalibur().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",
        "current_year": ""
    }

    try:
        result = Excalibur().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")


if __name__ == "__main__":
    run()
#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

import json
import os
from typing import Type
import threading
import time
import random

from excalibur.crew import Excalibur
from excalibur.simulator_crew import SimulatorCrew
from excalibur.tools.custom_tool import AmbulanceStateManager

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def background_ambulance_checker():
    """
    Background thread that checks every 30 seconds if any occupied ambulances
    should be released (when their mission duration expires).
    """
    while True:
        try:
            AmbulanceStateManager.check_and_free_ambulances()
            time.sleep(30)  # Check every 30 seconds
        except Exception as e:
            print(f"Error in background ambulance checker: {e}")
            time.sleep(30)  # Continue trying even if there's an error

def process_emergency_in_parallel(call_index, call_transcription):
    """
    Worker function executed inside a dedicated thread to process a single medical emergency
    without locking the main telephone simulator line.
    """
    try:
        with open('ambulances.json', 'r') as file:
            ambulances_data = json.load(file)
            
        ambulances_data_str = {
            amb["name"]: f"{amb['coordinates']['lat']},{amb['coordinates']['lng']}"
            for amb in ambulances_data["ambulances"]
            if amb["state"] == "available"
        }
        
        if not ambulances_data_str:
            print(f"[System Warning] Call #{call_index} put on hold: No ambulances available at this time.")
            return

        inputs = {
            'call_transcription': call_transcription,
            'ambulances': json.dumps(ambulances_data_str)
        }
        
        print(f"[Thread-Call-{call_index}] Excalibur Crew is now processing Call #{call_index}...")
        Excalibur().crew().kickoff(inputs=inputs)
        print(f"[Thread-Call-{call_index}] Emergency Call #{call_index} successfully processed.")
        
    except Exception as e:
        print(f"Error processing Call #{call_index} inside parallel thread: {e}")

def phone_line_simulator():
    """
    Infinite loop thread simulating real incoming emergency phone calls at random intervals.
    Each incoming call triggers a separate Excalibur instance to process the crisis concurrently.
    """
    print("Phone line simulator is active. Waiting for random incoming calls...")
    call_index = 1
    
    while True:
        try:
            seconds_to_wait = random.randint(10, 60)
            print(f"[System] Next emergency call will arrive in {seconds_to_wait} seconds...")
            time.sleep(seconds_to_wait)
            
            print(f"[System] INCOMING EMERGENCY CALL #{call_index}")
            
            # Kicking off the Simulator Crew to autonomously generate problem descriptions and positions
            call_output = SimulatorCrew().crew().kickoff()
            call_transcription = str(call_output)
            
            print(f"[System] Live Call Transcript received from Simulator for Call #{call_index}:\n\"{call_transcription}\"")
            
            # Spin up a separate thread for Excalibur processing to avoid blocking the main line loop
            medical_thread = threading.Thread(
                target=process_emergency_in_parallel,
                args=(call_index, call_transcription)
            )
            medical_thread.start()
            
            call_index += 1
            
        except Exception as e:
            print(f"Error in phone line simulator loop: {e}")
            time.sleep(10)

def run():
    """
    Run the crew.
    """
    
    # Start background ambulance checker thread
    checker_thread = threading.Thread(target=background_ambulance_checker, daemon=True)
    checker_thread.start()
    print("Background ambulance checker started (checks every 30 seconds)")

    # Start autonomous random phone call generator thread
    phone_thread = threading.Thread(target=phone_line_simulator, daemon=True)
    phone_thread.start()
    print("Autonomous phone line simulator started")

    # Keep the main process alive to allow background daemon threads to execute
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the emergency management system. Shutting down process.")


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
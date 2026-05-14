#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

import json
import os
from typing import Type
import threading
import time

from excalibur.crew import Excalibur
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

def run():
    """
    Run the crew.
    """
    
    # Start background ambulance checker thread
    checker_thread = threading.Thread(target=background_ambulance_checker, daemon=True)
    checker_thread.start()
    print("Background ambulance checker started (checks every 30 seconds)")

    with open('ambulances.json', 'r') as file:
            ambulances_data = json.load(file)
            
    ambulances_data_str = {
        amb["name"]: f"{amb['coordinates']['lat']},{amb['coordinates']['lng']}"
        for amb in ambulances_data["ambulances"]
        if amb["state"] == "available"
    }

    inputs = {
        'call_transcription': "Sono a villa giorcelli, a Rende, mi fa male la gamba",
        'ambulances': json.dumps(ambulances_data_str)
    }

    try:
        Excalibur().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


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

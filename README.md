# Excalibur Crew - Emergency Ambulance Dispatch System

**Excalibur** is an AI-powered emergency dispatch system that intelligently routes ambulances to patients in need. Using real-time traffic data and emergency call analysis, Excalibur ensures that the fastest available ambulance reaches the patient location, not just the geographically closest one.

Powered by [CrewAI](https://crewai.com), this system orchestrates multiple AI agents working together:
- **Emergency Call Analyzer**: Extracts critical patient information from call transcriptions (location, medical condition, urgency level)
- **Ambulance Dispatcher**: Evaluates available fleet and dispatches the unit with the lowest ETA using live traffic data

## Features

- **Live Traffic Integration**: Uses Google Maps API to calculate real-time ETAs considering current traffic conditions
- **Smart Fleet Management**: Automatically selects the fastest ambulance, not just the closest one
- **Call Analysis**: Extracts structured information from emergency call transcriptions
- **Multi-Agent Orchestration**: AI agents collaborate seamlessly to process calls and dispatch ambulances

## Prerequisites

- **Python**: 3.10 - 3.13
- **UV**: Dependency manager (install via `pip install uv`)
- **API Keys**: 
  - **GROQ_API_KEY** (for LLM inference)
  - **GOOGLE_API_KEY** (for Maps API - traffic data)
  - **SERPER_API_KEY** (optional, for web search)

## Installation

1. **Clone the repository** and navigate to the project directory
2. **Install dependencies**:
   ```bash
   crewai install
   ```
   Or manually: `uv sync`

3. **Set up environment variables**:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Fill in your API keys in `.env`

## Configuration

- **Agents**: Define agent roles, goals, and backstories in `src/excalibur/config/agents.yaml`
- **Tasks**: Configure tasks and their descriptions in `src/excalibur/config/tasks.yaml`
- **Crew Logic**: Customize crew orchestration in `src/excalibur/crew.py`
- **Input Data**: Modify test inputs in `src/excalibur/main.py`
- **Custom Tools**: Add new tools in `src/excalibur/tools/`

## Running the System

Execute from the project root:

```bash
crewai run
```

This will:
1. Load ambulance availability data from `ambulances.json`
2. Process an emergency call transcription through the Analyzer agent
3. Dispatch the fastest available ambulance via the Dispatcher agent

### Example Input

The system expects:
- **Emergency call transcription**: Natural language description of the emergency
- **Available ambulances**: JSON data with ambulance IDs and current coordinates/addresses
- **Patient location**: Will be extracted from the call analysis

## Project Structure

```
src/excalibur/
├── crew.py                  # Crew orchestration and agent setup
├── main.py                  # Entry point with test inputs
├── config/
│   ├── agents.yaml         # Agent definitions (Analyzer, Dispatcher)
│   └── tasks.yaml          # Task definitions (analysis, dispatch)
└── tools/
    └── custom_tool.py      # Google Maps ETA Calculator tool

ambulances.json             # Fleet data with ambulance locations
hospitals.json              # Hospital locations and info (for future use)
knowledge/                  # Knowledge base for agents
```

## Understanding the Workflow

1. **Call Analysis Phase** (Analyzer Agent):
   - Receives emergency call transcription
   - Extracts patient location, medical condition, and severity level
   - Prepares structured data for dispatcher

2. **Dispatch Phase** (Ambulance Dispatcher Agent):
   - Receives patient location and available ambulance list
   - Uses Google Maps API to calculate real-time ETAs for each ambulance
   - Selects the ambulance with the fastest arrival time
   - Returns dispatch decision with ETA and justification

## API Keys Required

| API | Purpose | How to Get |
|-----|---------|-----------|
| **GROQ_API_KEY** | LLM inference for agents | https://console.groq.com |
| **GOOGLE_API_KEY** | Google Maps (traffic, directions) | https://console.cloud.google.com |
| **SERPER_API_KEY** | Web search (optional) | https://serper.dev |

## Troubleshooting

- **"API Key not found" errors**: Ensure all required keys in `.env` match your actual API credentials
- **Google Maps errors**: Verify your Google API key has Maps JavaScript API and Distance Matrix API enabled
- **Empty ambulance list**: Check that `ambulances.json` has at least one ambulance with `"state": "available"`

## Future Enhancements

- [ ] Hospital locator agent (optimal hospital routing based on availability and specialty)
- [ ] Actor agent (coordinated response management)
- [ ] Mobile app integration for real-time tracking
- [ ] Historical performance analytics

## Support & Resources

For more information:
- [CrewAI Documentation](https://docs.crewai.com)
- [CrewAI GitHub](https://github.com/joaomdmoura/crewai)
- [CrewAI Discord Community](https://discord.com/invite/X4JWnZnxPb)

---

**Built using CrewAI** | Emergency dispatch, powered by AI

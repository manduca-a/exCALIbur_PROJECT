# Ambulance Dispatch Optimizer

A smart emergency response system that automatically selects the closest ambulance based on real-time traffic conditions and routing data.

## What It Does

This application optimizes emergency ambulance dispatch by:

- **Calculates distances** from multiple ambulance stations to the patient location
- **Estimates arrival times** accounting for current traffic conditions
- **Automatically selects** the ambulance with the shortest arrival time
- **Displays detailed information** about each route option in a beautiful formatted table
- **Simulates movement** - Ambulances change location realistically for testing

Perfect for emergency medical services that need quick, data-driven dispatch decisions.

## How to Use

### 1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

### 2. **Set Up Environment Variables**

Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

Then edit `.env` and add your Google Maps API key:

```env
GOOGLE_API_KEY=your_actual_api_key_here
```

**Get your API key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the **Maps API** and **Distance Matrix API**
4. Create credentials (API key)
5. Paste the key in `.env`

⚠️ **Important:** Never commit `.env` to git - it contains sensitive API keys. The file is already in `.gitignore`.

### 3. **Configure Ambulance Locations**

Edit `ambulances.json` to add your ambulance fleet:

```json
{
  "ambulances": [
    {
      "id": 1,
      "nome": "Ambulance 1",
      "coordinate": {
        "lat": 39.3601,
        "lng": 16.2289
      },
      "stato": "available"
    }
  ]
}
```

Coordinates are used instead of addresses for more realistic ambulance movement simulation.

### 4. **Run the System**

```bash
python map_try.py
```

Then enter the patient location when prompted:
```
🚑 Ambulance Dispatch System
Where is the patient located? viale delle scienze arcavacata
```

## Example Output

```
🚑 Ambulance Dispatch System
Where is the patient located? viale delle scienze arcavacata

Fetching ambulance locations...

╭────────────────────── Route Results ──────────────────────╮
│ Ambulance │      Address      │ Arrival Time │ Distance │
├───────────┼──────────────────┼──────────────┼──────────┤
│ Ambulanza 1 │ Via Marconi, Rende │     12 mins  │  8.5 km  │
│ Ambulanza 2 │ Via Rossini, Rende │      8 mins  │  6.2 km  │
╰────────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃    ✅ DISPATCH DECISION                   ┃
┃                                          ┃
┃    Send: Ambulance 2                     ┃
┃    Estimated arrival: 8 mins             ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Project Structure

```
├── map_try.py                 # Main application
├── utils.py                   # Utility functions
├── ambulanze.json             # Ambulance fleet data
├── .env                       # Environment variables (API keys) - NOT in git
├── .env.example               # Template for .env setup
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Key Features

- **Real-time traffic data** - Uses Google Maps Distance Matrix API
- **Dynamic ambulance positioning** - Coordinates change to simulate movement
- **Reverse geocoding** - Converts coordinates to addresses automatically
- **Rich terminal UI** - Colored output with tables and panels
- **Multiple ambulances** - Support for fleet-wide optimization
- **Safe credentials** - API keys in `.env` (not in git)

## Requirements

- Python 3.12 max (for crewai)
- Google Maps API key with Distance Matrix API enabled
- Internet connection for real-time traffic data

## Technologies Used

- **Google Maps API** - Real-time traffic and routing
- **Rich** - Beautiful terminal formatting
- **Python-dotenv** - Environment variable management

## How It Works

1. User provides patient location
2. System loads ambulance fleet from `ambulanze.json`
3. Ambulance coordinates are updated slightly to simulate movement
4. For each ambulance:
   - Reverse geocode coordinates to get address
   - Request distance matrix from Google Maps API
   - Calculate travel time considering traffic
5. System selects ambulance with shortest arrival time
6. Results displayed in formatted table with final dispatch decision

## Troubleshooting

**Error: "GOOGLE_API_KEY not found"**
- Make sure `.env` file exists in the project root
- Check that it contains: `GOOGLE_API_KEY=your_key_here`

**Error: "Could not authenticate with Google Maps"**
- Verify your API key is correct
- Ensure Distance Matrix API is enabled in Google Cloud Console
- Check API quota and rate limits

**Wrong addresses displayed**
- Reverse geocoding depends on Google Maps database
- Coordinates might be outside mapped areas
- Try with well-known locations first

---

**Built with ❤️ for emergency response optimization**


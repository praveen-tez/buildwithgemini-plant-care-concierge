# Plant Care Concierge 🌿

A conversational AI assistant designed to help plant parents manage, track, and care for their houseplant collection. Built with Google's Agent Development Kit (ADK) and Gemini on Google Cloud Agent Platform.

---

## 🌟 What the Agent Does

Based on the implemented tools and integrations in [`app/agent.py`](app/agent.py):

- **Houseplant Inventory & Care Log (Cloud Firestore)**:
  - `list_plants`: Retrieves your plant collection from a Firestore database.
  - `get_plant_details`: Looks up species requirements, lighting, watering frequency, and care notes.
  - `log_watering`: Records timestamps when specific plants are watered.
  - `add_plant`: Adds new houseplants with care attributes directly to Firestore.
- **Plant Nursery & Garden Center Locator (Google Maps Places API)**:
  - `geocode_address`: Converts an address or neighborhood into geographic coordinates.
  - `find_nearby_places`: Finds nearby plant nurseries, garden centers, and florist shops within a specified radius.
- **Botanical Image Generation (Gemini 3.1 Flash Lite Image + Cloud Storage)**:
  - `generate_plant_image`: Generates visual care guides and botanical images using `gemini-3.1-flash-lite-image`. Saves output as ADK session artifacts and uploads them to a public Cloud Storage bucket for direct image rendering.
- **Botanical Video Generation (Google Omni + Cloud Storage)**:
  - `generate_plant_video`: Generates short plant videos using `gemini-omni-flash-preview` in the global region, saving artifacts to the session and uploading to Cloud Storage.
- **Precise Calculations Sandbox (Agent Engine Code Sandbox)**:
  - Safely executes arbitrary Python code in an isolated `AgentEngineSandboxCodeExecutor` environment for watering interval calculations, humidity metrics, and fertilizer dilution ratios.
- **Long-Term Memory & User Allergy Guardrails (Vertex AI Memory Bank)**:
  - Preloads and extracts memories across sessions via `PreloadMemoryTool` and callback hooks.
  - Specifically tracks user allergies, sensitivities (e.g. sap, pollen, pet safety), and household lighting conditions to prevent harmful recommendations.
- **Rich Display Cards (A2UI v0.8)**:
  - Formats responses with cards, columns, rows, images, and text hints adhering to the A2UI v0.8 Basic Catalog.

---

## 🛠️ Google Cloud Services & Tools Wired Up

| Capability | Technology / Service | Status |
| :--- | :--- | :--- |
| **Reasoning Model** | Gemini 3.8 Flash (`gemini-3.8-flash`) | ✅ Implemented |
| **Image Generation** | Gemini 3.1 Flash Lite Image (`gemini-3.1-flash-lite-image`) | ✅ Implemented |
| **Video Generation** | Google Omni (`gemini-omni-flash-preview`) | ✅ Implemented |
| **Long-Term Memory** | Vertex AI Memory Bank | ✅ Implemented |
| **Database** | Google Cloud Firestore | ✅ Implemented |
| **Object Storage** | Google Cloud Storage (GCS) | ✅ Implemented |
| **Code Execution** | Vertex AI Agent Engine Sandbox | ✅ Implemented |
| **Location Services** | Google Maps Places & Geocoding APIs | ✅ Implemented |
| **UI Components** | A2UI (Agent-to-User Interface v0.8) | ✅ Implemented |
| **Frontend Proxy** | FastAPI + A2A Protocol Client | ✅ Implemented |

---

## 🚀 Local Setup & Running

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Google Cloud CLI (`gcloud`) authenticated with access to Vertex AI, Cloud Storage, and Firestore

### 1. Install Dependencies

In the project root:
```bash
uv sync
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure your Google Cloud project settings and optional Maps API key:
```bash
cp .env.example .env
```

Ensure the following variables are set in `.env`:
```env
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=<your-project-id>
GOOGLE_CLOUD_LOCATION=us-east1
GOOGLE_MAPS_API_KEY=<your-maps-api-key>
```

### 3. Launch Agent in ADK Playground

Run the ADK development web UI connected to your Agent Engine Memory Bank:
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://<AGENT_ENGINE_ID>
```

### 4. Run the Standalone Chat Frontend

Navigate to the `frontend/` directory:
```bash
cd frontend
uv venv
uv pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/<project-num>/locations/<location>/reasoningEngines/<id>"
export AGENT_DIRECTORY="app"
export PORT="8080"
python main.py
```

---

## 📁 Repository Structure

```
plant-care-concierge/
├── app/
│   ├── agent.py               # Core ADK agent, tools, callbacks, and sandbox executor
│   ├── a2ui_utils.py          # A2UI callback and card transformation helpers
│   ├── fast_api_app.py        # FastAPI A2A deployment wrapper
│   └── app_utils/             # Reasoning Engine and A2A routing adapters
├── frontend/
│   ├── main.py                # FastAPI proxy communicating via A2A protocol
│   ├── requirements.txt       # Frontend proxy dependencies
│   └── static/
│       └── index.html         # Custom chat UI with A2UI renderer and example prompts
├── tests/                     # Unit and integration test suites
├── agents-cli-manifest.yaml   # Agent deployment manifest
└── pyproject.toml             # Project dependencies and uv configuration
```

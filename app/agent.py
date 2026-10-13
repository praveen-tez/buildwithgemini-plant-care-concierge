# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import uuid
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
from dotenv import load_dotenv

from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore
from google.cloud import storage
from google.genai import types

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback

load_dotenv()

MODEL = "gemini-3.8-flash"
PROJECT_ID = "qwiklabs-gcp-04-839801f0229c"
BUCKET_NAME = "plant-care-concierge-qwiklabs-gcp-04-839801f0229c"
SANDBOX_RESOURCE_NAME = (
    "projects/538446417053/locations/us-east1/reasoningEngines/403966069603041280"
    "/sandboxEnvironments/6692463395481845760"
)

db = firestore.Client(project=PROJECT_ID)
plants_ref = db.collection("plants")

storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)

genai_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="global",
)


def list_plants() -> List[Dict[str, Any]]:
    """List all plants in the houseplant collection/catalog.

    Returns:
        A list of dictionaries with plant details (id, name, species, light_level,
        watering_frequency_days, difficulty, last_watered, notes).
    """
    docs = plants_ref.stream()
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        result.append(data)
    return result


def get_plant_details(plant_name_or_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific plant by its name or ID.

    Args:
        plant_name_or_id: The ID (e.g. 'monstera-deliciosa') or common name (e.g. 'Monstera') of the plant.

    Returns:
        A dictionary of the plant's attributes and care requirements.
    """
    doc = plants_ref.document(plant_name_or_id.lower().replace(" ", "-")).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    search_term = plant_name_or_id.lower()
    for doc in plants_ref.stream():
        data = doc.to_dict()
        if (
            search_term in data.get("name", "").lower()
            or search_term in data.get("species", "").lower()
            or search_term in doc.id.lower()
        ):
            data["id"] = doc.id
            return data

    return {"error": f"Plant '{plant_name_or_id}' not found in the collection."}


def log_watering(plant_id: str) -> Dict[str, Any]:
    """Log that a plant was watered right now.

    Args:
        plant_id: The unique ID or name of the plant to log watering for.

    Returns:
        Confirmation status and the updated timestamp.
    """
    plant = get_plant_details(plant_id)
    if "error" in plant:
        return plant

    real_id = plant["id"]
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    plants_ref.document(real_id).update({"last_watered": now_str})
    return {
        "status": "success",
        "message": f"Recorded watering for {plant.get('name', real_id)} at {now_str}.",
        "last_watered": now_str,
    }


def add_plant(
    name: str,
    species: str,
    light_level: str,
    watering_frequency_days: int,
    difficulty: str = "Easy",
    notes: str = "",
) -> Dict[str, Any]:
    """Add a new plant to the Firestore collection.

    Args:
        name: Common name of the plant (e.g. 'Pilea Peperomioides').
        species: Botanical species name (e.g. 'Pilea peperomioides').
        light_level: Preferred light level (e.g. 'Bright indirect', 'Low light').
        watering_frequency_days: Recommended interval in days between waterings (e.g. 7).
        difficulty: Care difficulty ('Very Easy', 'Easy', 'Medium', 'Hard').
        notes: Care notes or guidance.

    Returns:
        The created plant record.
    """
    plant_id = name.lower().strip().replace(" ", "-")
    doc_ref = plants_ref.document(plant_id)
    new_plant = {
        "id": plant_id,
        "name": name,
        "species": species,
        "light_level": light_level,
        "watering_frequency_days": watering_frequency_days,
        "difficulty": difficulty,
        "notes": notes,
        "last_watered": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    doc_ref.set(new_plant)
    return {"status": "success", "plant": new_plant}


def geocode_address(address: str) -> Dict[str, Any]:
    """Convert an address, neighborhood, or city into geographical coordinates (latitude and longitude).

    Args:
        address: The address or place query to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary with formatted address and latitude/longitude coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {
            "error": "GOOGLE_MAPS_API_KEY is not configured in .env. Please set a valid API key."
        }

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "error": f"Geocoding failed for '{address}': {data.get('status', 'No results')}"
            }

        first = data["results"][0]
        location = first["geometry"]["location"]
        return {
            "formatted_address": first.get("formatted_address"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "status": "success",
        }
    except Exception as e:
        return {"error": f"Error calling Geocoding API: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "florist",
    radius_meters: float = 5000.0,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Search for nearby places of a specific type around a location using the Google Places API (New).
    Useful to find plant nurseries, garden centers, or flower shops near the user.

    Args:
        latitude: Latitude of the center point.
        longitude: Longitude of the center point.
        place_type: Included place type (e.g. 'florist', 'home_goods_store', 'store').
        radius_meters: Search radius in meters (default 5000.0).
        max_results: Maximum places to return (default 5).

    Returns:
        A dictionary containing a list of nearby places with name, formatted address, and location.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {
            "error": "GOOGLE_MAPS_API_KEY is not configured in .env. Please set a valid API key."
        }

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": min(max_results, 20),
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_meters,
            }
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        raw_places = data.get("places", [])
        places = []
        for p in raw_places:
            display_name = p.get("displayName", {}).get("text", "")
            address = p.get("formattedAddress", "")
            loc = p.get("location", {})
            places.append(
                {
                    "name": display_name,
                    "address": address,
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                }
            )

        return {
            "places": places,
            "count": len(places),
            "status": "success",
        }
    except Exception as e:
        return {"error": f"Error calling Places API (New): {str(e)}"}


async def generate_plant_image(
    plant_name: str,
    prompt_description: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a photo or visual care guide for a plant using the gemini-3.1-flash-lite-image model.
    Saves the image into the agent's session artifacts panel and uploads it to the public Cloud Storage bucket.

    Args:
        plant_name: Name of the plant (e.g. 'Monstera Deliciosa', 'Snake Plant').
        prompt_description: A descriptive prompt detailing the scene, setting, or health of the plant.
        tool_context: ToolContext provided automatically by the ADK runtime.

    Returns:
        A dictionary with the public image URL, filename, and status.
    """
    try:
        full_prompt = (
            f"Vibrant, professional botanical photography of {plant_name}. "
            f"{prompt_description}. Healthy foliage, clear lighting, beautiful indoor planter."
        )

        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=[full_prompt],
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.parts:
            for part in response.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {"error": "Model did not return image data."}

        filename = f"{plant_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}.jpg"

        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=part)

        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "plant_name": plant_name,
            "filename": filename,
            "public_image_url": public_url,
            "message": f"Generated image saved to artifacts and published to {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload plant image: {str(e)}"}


async def generate_plant_video(
    plant_name: str,
    prompt_description: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a short video for a plant using Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the video artifact with tool_context.save_artifact so it appears in the Artifacts panel,
    and uploads the video bytes to the public Cloud Storage bucket, returning its public https URL.

    Args:
        plant_name: Name of the plant (e.g. 'Monstera Deliciosa', 'Snake Plant').
        prompt_description: A descriptive prompt detailing the scene, time-lapse, or care action.
        tool_context: ToolContext provided automatically by the ADK runtime.

    Returns:
        A dictionary with the public video URL, filename, and status.
    """
    try:
        full_prompt = (
            f"Smooth, high quality botanical video of {plant_name}. "
            f"{prompt_description}. Natural lighting, vibrant foliage, gentle movement."
        )

        interaction = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=full_prompt,
        )

        video_bytes = None
        if hasattr(interaction, "output_video") and interaction.output_video:
            if hasattr(interaction.output_video, "data") and interaction.output_video.data:
                import base64
                data_val = interaction.output_video.data
                video_bytes = base64.b64decode(data_val) if isinstance(data_val, str) else data_val
            elif hasattr(interaction.output_video, "uri") and interaction.output_video.uri:
                # If delivered as URI
                pass

        if not video_bytes and hasattr(interaction, "steps"):
            import base64
            for step in interaction.steps:
                contents = getattr(step, "content", []) or []
                for item in contents:
                    if getattr(item, "type", "") == "video" and getattr(item, "data", None):
                        v_data = item.data
                        video_bytes = base64.b64decode(v_data) if isinstance(v_data, str) else v_data
                        break

        if not video_bytes:
            return {"error": "Model did not return video bytes."}

        filename = f"{plant_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}.mp4"
        mime_type = "video/mp4"

        part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=part)

        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "plant_name": plant_name,
            "filename": filename,
            "public_video_url": public_url,
            "message": f"Generated video saved to artifacts and published to {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload plant video: {str(e)}"}


async def generate_memories_callback(callback_context: CallbackContext):
    """After each turn, send the session to Memory Bank for extraction and persistence."""
    await callback_context.add_session_to_memory()
    return None


code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME,
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the Plant Care Concierge, an expert houseplant assistant. "
        "You diligently remember and respect all user allergies and sensitivities (such as plant pollen, "
        "latex/sap, skin irritants, fragrance, or food/environmental allergies) as well as stated preferences, "
        "home environment details (pet ownership, lighting, humidity), and facts across conversations. "
        "Never recommend, suggest, or include plants or care routines that conflict with the user's remembered allergies. "
        "When calculating numbers, ratios, unit conversions, or data, execute Python code using your code execution sandbox. "
        "After code execution, summarize the final answer clearly in the UI. "
        "When a user asks for an image, photo, or visual guide of a plant, call generate_plant_image. "
        "Use your other tools to list plants, get details, log waterings, add plants, and find nurseries."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_plants,
        get_plant_details,
        log_watering,
        add_plant,
        geocode_address,
        find_nearby_places,
        generate_plant_image,
        generate_plant_video,
    ],
    code_executor=code_executor,
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

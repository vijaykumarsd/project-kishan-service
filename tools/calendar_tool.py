import json
import os


async def crop_calendar_tool(crop: str, state: str) -> str:
    """
    Returns sowing and harvesting periods for a crop in a given state.
    """
    try:
        with open("data/crop_calendar.json", "r") as f:
            calendar = json.load(f)

        crop_data = calendar.get(crop.lower(), {})
        state_data = crop_data.get(state.title())
        if not state_data:
            return json.dumps({"error": f"No data for {crop} in {state}"})

        return json.dumps(state_data)

    except Exception as e:
        return json.dumps({"error": str(e)})

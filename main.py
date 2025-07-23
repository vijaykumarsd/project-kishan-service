# main.py
import os
import uuid
import asyncio
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
import logging

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types  # The types module

import pkg_resources

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logging.getLogger('google_adk').setLevel(logging.DEBUG)
logging.getLogger('vertexai').setLevel(logging.DEBUG)
logging.getLogger('google.generativeai').setLevel(logging.DEBUG)
logging.getLogger('google.cloud.aiplatform').setLevel(logging.DEBUG)
logging.getLogger('uvicorn').setLevel(logging.INFO)
logging.getLogger('uvicorn.access').setLevel(logging.INFO)
print("DEBUG: Logging configured for DEBUG level for ADK and Vertex AI components.")

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    print(f"DEBUG (main.py): .env file found and loaded from: {dotenv_path}")
else:
    print("ERROR (main.py): .env file not found. Please ensure it's in the correct directory.")
    exit(1)

try:
    from agent import kisan_orchestrator_agent

    print("kisan_orchestrator_agent imported successfully from agent.py")
except ImportError as e:
    print(f"ERROR (main.py): Could not import 'kisan_orchestrator_agent' from 'agent.py'. Error: {e}")
    print("Please ensure 'agent.py' exists in the same directory and defines 'kisan_orchestrator_agent'.")
    exit(1)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_NAME = "KisanAgriApp"
USER_ID = "default_user"

try:
    try:
        adk_version = pkg_resources.get_distribution("google-adk").version
        print(f"DEBUG: google-adk version installed: {adk_version}")
    except pkg_resources.DistributionNotFound:
        print("DEBUG: google-adk package not found.")

    session_service = InMemorySessionService()
    print("Session Service initialized successfully.")

    runtime = Runner(
        app_name=APP_NAME,
        agent=kisan_orchestrator_agent,
        session_service=session_service
    )
    print("Agent Runner initialized successfully.")
except Exception as e:
    print(f"ERROR (main.py): Failed to initialize Agent Runner. Error: {e}")
    import traceback

    traceback.print_exc()
    exit(1)


@app.post("/api/simple")
async def simple_route(
        query: str | None = Form(None),
        image: UploadFile | None = File(None)
):
    print("DEBUG: Request received by /api/simple endpoint!")
    print(f"Received query: '{query}'")
    print(f"Received image: {image.filename if image else 'None'}")
    if image:
        print(f"DEBUG: Image content_type from client: {image.content_type}")

    if query is None and image is None:
        return {"error": "At least 'query' or 'image' must be provided."}, 400

    session_id = str(uuid.uuid4())

    try:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id
        )
        print(f"DEBUG: Session '{session_id}' created successfully.")
    except Exception as e:
        print(f"ERROR: Failed to create session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to create session: {str(e)}"}, 500

    message_parts = []
    if query:
        message_parts.append(types.Part(text=query))

    if image:
        try:
            image_bytes = await image.read()
            print(f"DEBUG: Read {len(image_bytes)} bytes from image file.")
            if not image_bytes:
                print("ERROR: Image bytes are empty after reading from UploadFile!")
                return {"error": "Uploaded image file is empty."}, 400

            detected_mime_type = image.content_type
            if not detected_mime_type:
                if image.filename and '.' in image.filename:
                    ext = image.filename.rsplit('.', 1)[1].lower()
                    if ext == 'jpg' or ext == 'jpeg':
                        detected_mime_type = "image/jpeg"
                    elif ext == 'png':
                        detected_mime_type = "image/png"
                    elif ext == 'gif':
                        detected_mime_type = "image/gif"
                    elif ext == 'webp':
                        detected_mime_type = "image/webp"
                    else:
                        print(f"WARNING: Unknown image extension: {ext}. Defaulting to image/jpeg.")
                        detected_mime_type = "image/jpeg"
                else:
                    print("WARNING: No content_type and no file extension. Defaulting to image/jpeg.")
                    detected_mime_type = "image/jpeg"

            print(f"DEBUG: Using MIME type for image: {detected_mime_type}")
            print(f"DEBUG: First 20 bytes (hex): {image_bytes[:20].hex()}")

            # --- Attempting types.Part.from_data() again as it's the standard,
            # but relying on the traceback for exact error info ---
            try:
                message_parts.append(
                    types.Part(
                        inline_data={  # Pass a dictionary for inline_data
                            'mime_type': detected_mime_type,
                            'data': image_bytes
                        }
                    )
                )
                print(
                    f"DEBUG: Image {image.filename} ({len(image_bytes)} bytes) with MIME type {detected_mime_type} added to message parts.")
                print(f"DEBUG: Successfully created image part using from_data().")
            except Exception as inner_e:
                print(f"CRITICAL ERROR: Exception during types.Part.from_data() call: {inner_e}")
                import traceback
                traceback.print_exc()
                raise inner_e

        except Exception as e:
            print(f"ERROR: Failed to process image: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to process image: {str(e)}"}, 400

    if not message_parts:
        return {"error": "No content (query or image) provided for the agent to process."}, 400

    new_message_content = types.Content(
        role="user",
        parts=message_parts
    )
    print(f"DEBUG: Prepared new_message_content: {new_message_content}")

    try:
        final_response_text = "The agent could not generate a response."

        async def get_events_from_sync_runner():
            print(f"DEBUG: Calling runtime.run() in a separate thread via asyncio.to_thread...")
            results_list = await asyncio.to_thread(
                lambda: list(runtime.run(
                    user_id=USER_ID,
                    session_id=session_id,
                    new_message=new_message_content
                ))
            )
            print(f"DEBUG: Collected {len(results_list)} events from sync generator in thread.")
            for event in results_list:
                yield event

        async for event in get_events_from_sync_runner():
            print(f"  DEBUG: Type of event object in loop: {type(event)}")

            event_type = getattr(event, 'type', 'N/A')
            _is_final_attr = getattr(event, 'is_final_response', False)
            is_final = _is_final_attr() if callable(_is_final_attr) else _is_final_attr

            event_content = getattr(event, 'content', None)

            print(f"  DEBUG: Received event type: {event_type}")
            print(f"  DEBUG: is_final_response: {is_final}")

            if event_content:
                print(f"    DEBUG: Event content: {event_content}")
                if getattr(event_content, 'parts', None):
                    for part in event_content.parts:
                        if getattr(part, 'text', None):
                            print(f"      DEBUG: Event text part: {part.text}")
                            if is_final:
                                final_response_text = part.text
                                if final_response_text != "The agent could not generate a response.":
                                    break
                        if getattr(part, 'function_call', None):
                            print(f"      DEBUG: Function Call: {part.function_call.name}({part.function_call.args})")
                        if getattr(part, 'function_response', None):
                            print(f"      DEBUG: Function Response: {part.function_response}")

            if is_final and final_response_text != "The agent could not generate a response.":
                break

        print(f"DEBUG: Agent execution completed. Final response text: {final_response_text}")
        return {"response": final_response_text}

    except Exception as e:
        print(f"ERROR: An error occurred during agent execution: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to get response from agent: {str(e)}"}, 500


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8005))
    print(f"Starting FastAPI app on http://127.0.0.1:{port}/")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
# main.py
import os
import uuid
import asyncio
from fastapi import FastAPI, Form, UploadFile, File, Depends, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
import logging
import json
from typing import Annotated

# Firebase Imports
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import storage
from firebase_admin import auth

# Import the Runner class from google.adk.runners
from google.adk.runners import Runner
# Import InMemorySessionService for local session management
from google.adk.sessions import InMemorySessionService
# Import necessary types for the agent's input content
from google.genai import types

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
print("DEBUG: Logging configured.")

# --- Load environment variables EARLY and explicitly ---
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    print(f"DEBUG (main.py): .env file found and loaded from: {dotenv_path}")
else:
    print("ERROR (main.py): .env file not found. Ensure it's in the correct directory.")
    exit(1)

# --- Import your orchestrator agent from the local 'agent.py' file ---
try:
    from agent import kisan_orchestrator_agent, MODEL_NAME

    print("kisan_orchestrator_agent imported successfully from agent.py")
except ImportError as e:
    print(f"ERROR (main.py): Could not import 'kisan_orchestrator_agent' from 'agent.py'. Error: {e}")
    print("Please ensure 'agent.py' exists and defines 'kisan_orchestrator_agent'.")
    exit(1)

# --- FastAPI Application Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Firebase Initialization ---
service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not service_account_path:
    raise ValueError(
        "GOOGLE_APPLICATION_CREDENTIALS environment variable not set. Please set it to the path of your Firebase service account JSON key."
    )

absolute_service_account_path = os.path.abspath(service_account_path)
print(f"DEBUG: Attempting to load Firebase credentials from: {absolute_service_account_path}")

if not os.path.exists(absolute_service_account_path):
    raise FileNotFoundError(f"Firebase service account file not found at {absolute_service_account_path}")

db = None
bucket = None

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(absolute_service_account_path)
        with open(absolute_service_account_path, 'r') as f:
            firebase_config_from_file = json.load(f)

        storage_bucket_name = "project-kisan-app.appspot.com"
        print(storage_bucket_name)

        firebase_admin.initialize_app(cred, {
            'storageBucket': storage_bucket_name
        })
        print(f"Firebase Admin SDK initialized successfully for bucket: {storage_bucket_name}")

    db = firestore.client()
    print("Firestore client initialized.")

    bucket = storage.bucket()
    print(f"Firebase Storage bucket initialized: {bucket.name}")

except Exception as e:
    print(f"ERROR: Failed to initialize Firebase, Firestore, or Storage: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# --- Agent Runtime Initialization ---
APP_NAME = "KisanAgriApp"
APP_ID = "kisan_agri_app_v1"
MODEL_NAME = "gemini-1.5-flash-001" # Assuming the model name is defined here or in agent.py

try:
    session_service = InMemorySessionService()
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


# --- Dependency to validate Firebase ID token and get user ID ---
async def get_user_id_from_token(
        authorization: Annotated[str, Header(description="Bearer token from Firebase Authentication")]
):
    """
    FastAPI dependency that validates a Firebase ID token and returns the user ID.
    This function now makes authentication mandatory.
    """
    try:
        scheme, token = authorization.split(" ")
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")

        decoded_token = await asyncio.to_thread(auth.verify_id_token, token)
        user_uid = decoded_token['uid']
        print(f"DEBUG: Token verified. Authenticated user ID: {user_uid}")
        return user_uid
    except Exception as e:
        print(f"WARNING: Failed to verify Firebase ID token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or missing authentication token: {str(e)}"
        )


# --- FastAPI Route Definition for Agent Interaction ---
@app.post("/api/simple")
async def simple_route(
        query: Annotated[str | None, Form()] = None,
        image: Annotated[UploadFile | None, File()] = None,
        current_user_id: str = Depends(get_user_id_from_token)
):
    """
    API endpoint to interact with the kisan_orchestrated_agent.
    Requires a valid Firebase ID token for authentication.
    """
    print("DEBUG: Request received by /api/simple endpoint!")
    print(f"User ID for this request: '{current_user_id}'")
    print(f"Received query: '{query}'")
    print(f"Received image: {image.filename if image else 'None'}")

    if query is None and image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 'query' or 'image' must be provided."
        )

    session_id = str(uuid.uuid4())
    image_public_url = None

    try:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=current_user_id,
            session_id=session_id
        )
        print(f"DEBUG: Session '{session_id}' created successfully for user '{current_user_id}'.")
    except Exception as e:
        print(f"ERROR: Failed to create session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )

    message_parts = []
    if query:
        message_parts.append(types.Part(text=query))

    if image:
        if not bucket:
            print("ERROR: Firebase Storage not initialized. Cannot upload image.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Firebase Storage not initialized. Image upload failed."
            )

        try:
            image_bytes = await image.read()
            if not image_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded image file is empty."
                )

            detected_mime_type = image.content_type
            if not detected_mime_type:
                file_extension = image.filename.rsplit('.', 1)[-1].lower() if '.' in image.filename else ''
                mime_type_mapping = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif'}
                detected_mime_type = mime_type_mapping.get(file_extension, 'image/jpeg')
                print(f"WARNING: No MIME type provided. Inferred as: {detected_mime_type}")

            file_extension = image.filename.split('.')[-1] if '.' in image.filename else 'bin'
            destination_blob_name = f"artifacts/{APP_ID}/users/{current_user_id}/images/{uuid.uuid4()}.{file_extension}"
            blob = bucket.blob(destination_blob_name)

            await asyncio.to_thread(blob.upload_from_string, image_bytes, content_type=detected_mime_type)
            await asyncio.to_thread(blob.make_public)
            image_public_url = blob.public_url
            print(f"DEBUG: Image uploaded to Firebase Storage: {image_public_url}")

            message_parts.append(
                types.Part(
                    inline_data={
                        'mime_type': detected_mime_type,
                        'data': image_bytes
                    }
                )
            )

        except Exception as e:
            print(f"ERROR: Failed to process or upload image: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process or upload image: {str(e)}"
            )

    new_message_content = types.Content(
        role="user",
        parts=message_parts
    )

    final_response_text = "The agent could not generate a response."
    try:
        events_generator = runtime.run(
            user_id=current_user_id,
            session_id=session_id,
            new_message=new_message_content
        )

        for event in events_generator:
            is_final = getattr(event, 'is_final_response', False)
            event_content = getattr(event, 'content', None)

            if event_content and getattr(event_content, 'parts', None):
                for part in event_content.parts:
                    if getattr(part, 'text', None):
                        if is_final:
                            final_response_text = part.text
                            if final_response_text != "The agent could not generate a response.":
                                break

            if is_final and final_response_text != "The agent could not generate a response.":
                break

        print(f"DEBUG: Agent execution completed. Final response text: {final_response_text}")

        # --- Store Response in Firestore ---
        if db:
            try:
                conversations_ref = db.collection(f"artifacts/{APP_ID}/users/{current_user_id}/conversations")
                doc_data = {
                    "query": query,
                    "response": final_response_text,
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "session_id": session_id,
                    "model_used": MODEL_NAME,
                    "image_url": image_public_url,
                    "image_filename": image.filename if image else None
                }
                doc_ref = await asyncio.to_thread(conversations_ref.add, doc_data)
                print(f"DEBUG: Response stored in Firestore with ID: {doc_ref[1].id}")
            except Exception as e:
                print(f"ERROR: Failed to store response in Firestore: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to store conversation in Firestore due to insufficient permissions. Please check your Firebase rules and service account roles: {str(e)}"
                )

        return {"response": final_response_text}

    except Exception as e:
        print(f"ERROR: An error occurred during agent execution: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get response from agent: {str(e)}"
        )


@app.get("/api/chat-history")
async def get_chat_history(
        current_user_id: str = Depends(get_user_id_from_token)
):
    """
    Get the conversation history (query + response) for the authenticated user.
    """
    try:
        conversations_ref = db.collection(f"artifacts/{APP_ID}/users/{current_user_id}/conversations")
        docs = await asyncio.to_thread(lambda: list(conversations_ref.stream()))

        history = []
        for doc in docs:
            data = doc.to_dict()
            history.append({
                "query": data.get("query"),
                "response": data.get("response"),
                "timestamp": data.get("timestamp"),
                "model_used": data.get("model_used"),
                "image_url": data.get("image_url"),
                "image_filename": data.get("image_filename"),
            })

        # Optional: sort by timestamp if needed
        history.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)

        return {"history": history}

    except Exception as e:
        print(f"ERROR fetching chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )


# --- Uvicorn Entry Point ---
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8005))
    print(f"Starting FastAPI app on http://127.0.0.1:{port}/")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
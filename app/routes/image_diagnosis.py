from fastapi import APIRouter, UploadFile, File
from vertexai.preview.generative_models import GenerativeModel, Part
from PIL import Image
import io
router = APIRouter()

@router.post("/diagnose-image")
async def diagnose_image(file: UploadFile = File(...)):
    contents = await file.read()

    # Prepare image for Gemini Vision
    image_part = Part.from_data(data=contents, mime_type=file.content_type)

    model = GenerativeModel("gemini-1.5-pro-vision-0409")
    prompt = "What crop disease is this? Suggest treatment in simple terms."

    result = model.generate_content([prompt, image_part])
    return {"response": result.text}

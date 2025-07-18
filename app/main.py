from fastapi import FastAPI

from app.routes import image_diagnosis, schemenavigator, marketanalyst, agronomist
app = FastAPI()
app.include_router(agronomist.router)
app.include_router(marketanalyst.router)
app.include_router(schemenavigator.router)
app.include_router(image_diagnosis.router)
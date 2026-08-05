from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .models import RecommendationRequest, RecommendationResponse
from .rules import recommend


app = FastAPI(title="CityStart Service Matching Service", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "The request is invalid.", "details": exc.errors()}})


@app.get("/health")
def health():
    return {"service": "service-matching-service", "status": "ok"}


@app.post("/recommendations", response_model=RecommendationResponse)
def create_recommendation(payload: RecommendationRequest):
    return recommend(payload)

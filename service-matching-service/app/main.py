from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .models import RecommendationRequest, RecommendationResponse
from .rules import recommend


app = FastAPI(
    title="CityStart Service Matching Service",
    version="0.2.0",
)


@app.exception_handler(RequestValidationError)
async def validation_error(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request body is invalid.",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "service": "service-matching-service",
        "status": "ok",
    }


@app.post(
    "/recommendations",
    response_model=RecommendationResponse,
)
def create_recommendation(
    payload: RecommendationRequest,
) -> RecommendationResponse:
    return recommend(payload)

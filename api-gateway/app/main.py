import asyncio
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import (
    DOWNSTREAM_TIMEOUT_SECONDS,
    EMPLOYMENT_SERVICE_URL,
    HOUSING_SERVICE_URL,
    MATCHING_SERVICE_URL,
    RESIDENCE_SERVICE_URL,
)


app = FastAPI(title="CityStart API Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def error(status_code: int, code: str, message: str, details: list[Any] | None = None):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
    )


async def proxy(request: Request, base_url: str, path: str):
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=DOWNSTREAM_TIMEOUT_SECONDS) as client:
            response = await client.request(
                request.method,
                url,
                params=request.query_params,
                content=await request.body(),
                headers={"content-type": request.headers.get("content-type", "application/json")},
            )
    except httpx.TimeoutException:
        return error(504, "DOWNSTREAM_TIMEOUT", f"Downstream request timed out: {base_url}")
    except httpx.RequestError:
        return error(503, "SERVICE_UNAVAILABLE", f"Downstream service is unavailable: {base_url}")

    try:
        content = response.json()
    except ValueError:
        return error(502, "INVALID_DOWNSTREAM_RESPONSE", "Downstream response is not valid JSON")
    return JSONResponse(status_code=response.status_code, content=content)


@app.get("/health")
def health():
    return {"service": "api-gateway", "status": "ok"}


@app.api_route("/api/residence/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def residence_proxy(path: str, request: Request):
    return await proxy(request, RESIDENCE_SERVICE_URL, path)


@app.api_route("/api/employment/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def employment_proxy(path: str, request: Request):
    return await proxy(request, EMPLOYMENT_SERVICE_URL, path)


@app.api_route("/api/housing/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def housing_proxy(path: str, request: Request):
    return await proxy(request, HOUSING_SERVICE_URL, path)


@app.api_route("/api/recommendations", methods=["POST"])
async def recommendations_proxy(request: Request):
    return await proxy(request, MATCHING_SERVICE_URL, "recommendations")


@app.api_route("/api/recommendations/{path:path}", methods=["GET", "POST"])
async def matching_proxy(path: str, request: Request):
    return await proxy(request, MATCHING_SERVICE_URL, f"recommendations/{path}")


async def fetch_json(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


@app.get("/api/citizens/{citizen_id}/service-plan")
async def service_plan(citizen_id: str):
    try:
        async with httpx.AsyncClient(timeout=DOWNSTREAM_TIMEOUT_SECONDS) as client:
            residence, employment, housing = await asyncio.gather(
                fetch_json(client, f"{RESIDENCE_SERVICE_URL}/citizens/{citizen_id}/residence-status"),
                fetch_json(client, f"{EMPLOYMENT_SERVICE_URL}/citizens/{citizen_id}/employment-status"),
                fetch_json(client, f"{HOUSING_SERVICE_URL}/citizens/{citizen_id}/housing-status"),
            )
            matching_payload = {
                "citizen_id": citizen_id,
                "residence_registered": residence["residence_registered"],
                "residence_permit_approved": residence["residence_permit_approved"],
                "employment_registered": employment["employment_registered"],
                "currently_renting": housing["currently_renting"],
                "owns_local_property": housing["owns_local_property"],
                "available_documents": [],
            }
            matching_response = await client.post(
                f"{MATCHING_SERVICE_URL}/recommendations", json=matching_payload
            )
            matching_response.raise_for_status()
    except httpx.TimeoutException:
        return error(504, "DOWNSTREAM_TIMEOUT", "A service-plan dependency timed out")
    except httpx.RequestError as exc:
        return error(503, "SERVICE_UNAVAILABLE", "A service-plan dependency is unavailable", [str(exc)])
    except (KeyError, ValueError) as exc:
        return error(502, "INVALID_DOWNSTREAM_RESPONSE", "A dependency returned an invalid response", [str(exc)])

    return {
        "citizen_id": citizen_id,
        "service_status": {
            "residence": residence,
            "employment": employment,
            "housing": housing,
        },
        "recommendation": matching_response.json(),
    }

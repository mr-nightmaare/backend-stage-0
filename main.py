from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import httpx

app = FastAPI(title="HNG14 Stage 0 - Name Classifier API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GENDERIZE_URL = "https://api.genderize.io"


@app.get("/api/classify")
async def classify_name(request: Request, name: str = Query(default=None)):
    if name is None or name.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty 'name' query parameter"},
        )

    if not isinstance(name, str):
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "'name' must be a string"},
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(GENDERIZE_URL, params={"name": name})
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Upstream API timed out"},
        )
    except httpx.HTTPStatusError:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Upstream API returned an error"},
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error while contacting upstream API"},
        )

    gender = data.get("gender")
    count = data.get("count", 0)

    if gender is None or count == 0:
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": "No prediction available for the provided name"},
        )

    probability = data.get("probability", 0)
    sample_size = count
    is_confident = probability >= 0.7 and sample_size >= 100
    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "status": "success",
        "data": {
            "name": data.get("name", name),
            "gender": gender,
            "probability": probability,
            "sample_size": sample_size,
            "is_confident": is_confident,
            "processed_at": processed_at,
        },
    }

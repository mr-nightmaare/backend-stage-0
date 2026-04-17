from fastapi import FastAPI, Query, Request, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import httpx
import uuid
import time
import asyncio

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel

DATABASE_URL = "sqlite:///./profiles.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProfileModel(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    gender = Column(String, nullable=True)
    gender_probability = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=True)
    age = Column(Integer, nullable=True)
    age_group = Column(String, nullable=True)
    country_id = Column(String, nullable=True)
    country_probability = Column(Float, nullable=True)
    created_at = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_uuid7():
    timestamp = int(time.time() * 1000)
    time_low = timestamp & 0xFFFFFFFF
    time_mid = (timestamp >> 32) & 0xFFFF
    time_hi_ver = ((timestamp >> 48) & 0xFFF) | 0x7000
    clock_seq = 0x8000 | (uuid.uuid4().int & 0x3FFF)
    node = (uuid.uuid4().int & 0xFFFFFFFFFFFF) | 0x800000000000
    uuid_int = (time_low << 96) | (time_mid << 80) | (time_hi_ver << 64) | (clock_seq << 48) | node
    return str(uuid.UUID(int=uuid_int))


def get_age_group(age: int) -> str:
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="HNG14 Stage 1 - Profile Management API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cors_header_always(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


class CreateProfileRequest(BaseModel):
    name: str = None

    class Config:
        extra = "forbid"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"status": "error", "message": "Missing or empty name"},
    )


@app.post("/api/profiles", status_code=201)
async def create_profile(request: CreateProfileRequest, db: Session = Depends(get_db)):
    name = request.name

    if not name or not isinstance(name, str) or name.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty name"},
        )

    name_lower = name.strip().lower()
    existing = db.query(ProfileModel).filter(ProfileModel.name == name_lower).first()
    if existing:
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Profile already exists",
                "data": {
                    "id": existing.id,
                    "name": existing.name,
                    "gender": existing.gender,
                    "gender_probability": existing.gender_probability,
                    "sample_size": existing.sample_size,
                    "age": existing.age,
                    "age_group": existing.age_group,
                    "country_id": existing.country_id,
                    "country_probability": existing.country_probability,
                    "created_at": existing.created_at,
                },
            },
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            gender_response, agify_response, nationalize_response = await asyncio.gather(
                client.get(f"https://api.genderize.io?name={name}"),
                client.get(f"https://api.agify.io?name={name}"),
                client.get(f"https://api.nationalize.io?name={name}"),
            )

            gender_data = gender_response.json()
            agify_data = agify_response.json()
            nationalize_data = nationalize_response.json()

    except Exception:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Upstream API returned an invalid response"},
        )

    gender = gender_data.get("gender")
    count = gender_data.get("count", 0)
    if gender is None or count == 0:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Genderize returned an invalid response"},
        )

    age = agify_data.get("age")
    if age is None:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Agify returned an invalid response"},
        )

    country_data = nationalize_data.get("country", [])
    if not country_data:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Nationalize returned an invalid response"},
        )

    top_country = max(country_data, key=lambda x: x.get("probability", 0))
    country_id = top_country.get("country_id")
    country_probability = top_country.get("probability")

    profile_id = generate_uuid7()
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    age_group = get_age_group(age)

    profile = ProfileModel(
        id=profile_id,
        name=name_lower,
        gender=gender,
        gender_probability=gender_data.get("probability"),
        sample_size=count,
        age=age,
        age_group=age_group,
        country_id=country_id,
        country_probability=country_probability,
        created_at=created_at,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return {
        "status": "success",
        "data": {
            "id": profile.id,
            "name": profile.name,
            "gender": profile.gender,
            "gender_probability": profile.gender_probability,
            "sample_size": profile.sample_size,
            "age": profile.age,
            "age_group": profile.age_group,
            "country_id": profile.country_id,
            "country_probability": profile.country_probability,
            "created_at": profile.created_at,
        },
    }


@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(ProfileModel).filter(ProfileModel.id == profile_id).first()
    if not profile:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Profile not found"},
        )

    return {
        "status": "success",
        "data": {
            "id": profile.id,
            "name": profile.name,
            "gender": profile.gender,
            "gender_probability": profile.gender_probability,
            "sample_size": profile.sample_size,
            "age": profile.age,
            "age_group": profile.age_group,
            "country_id": profile.country_id,
            "country_probability": profile.country_probability,
            "created_at": profile.created_at,
        },
    }


@app.get("/api/profiles")
async def get_all_profiles(
    gender: str = Query(default=None),
    country_id: str = Query(default=None),
    age_group: str = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(ProfileModel)

    if gender:
        query = query.filter(ProfileModel.gender.ilike(gender))
    if country_id:
        query = query.filter(ProfileModel.country_id.ilike(country_id))
    if age_group:
        query = query.filter(ProfileModel.age_group.ilike(age_group))

    profiles = query.all()

    return {
        "status": "success",
        "count": len(profiles),
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "gender": p.gender,
                "age": p.age,
                "age_group": p.age_group,
                "country_id": p.country_id,
            }
            for p in profiles
        ],
    }


@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(ProfileModel).filter(ProfileModel.id == profile_id).first()
    if not profile:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Profile not found"},
        )

    db.delete(profile)
    db.commit()

    return Response(status_code=204)




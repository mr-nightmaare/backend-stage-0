from fastapi import FastAPI, Query, Request, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import json
import uuid
import time
import re

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Index
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic import BaseModel

DATABASE_URL = "sqlite:///./profiles.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProfileModel(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)
    gender = Column(String, nullable=True)
    gender_probability = Column(Float, nullable=True)
    age = Column(Integer, nullable=True)
    age_group = Column(String, nullable=True, index=True)
    country_id = Column(String, nullable=True, index=True)
    country_name = Column(String, nullable=True)
    country_probability = Column(Float, nullable=True)
    created_at = Column(String, nullable=False)

    __table_args__ = (
        Index('idx_gender', 'gender'),
        Index('idx_age', 'age'),
    )


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


def seed_database():
    db = SessionLocal()
    try:
        existing_count = db.query(ProfileModel).count()
        if existing_count >= 2026:
            return

        with open("seed_profiles.json", "r") as f:
            data = json.load(f)

        profiles = data.get("profiles", [])
        for p in profiles:
            name = p.get("name", "").strip().lower()
            if not name:
                continue

            existing = db.query(ProfileModel).filter(ProfileModel.name == name).first()
            if existing:
                continue

            profile_id = generate_uuid7()
            created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            profile = ProfileModel(
                id=profile_id,
                name=name,
                gender=p.get("gender"),
                gender_probability=p.get("gender_probability"),
                age=p.get("age"),
                age_group=p.get("age_group"),
                country_id=p.get("country_id"),
                country_name=p.get("country_name"),
                country_probability=p.get("country_probability"),
                created_at=created_at,
            )
            db.add(profile)

        db.commit()
    finally:
        db.close()


COUNTRY_NAME_TO_CODE = {
    "nigeria": "NG",
    "kenya": "KE",
    "uganda": "UG",
    "tanzania": "TZ",
    "ghana": "GH",
    "south africa": "ZA",
    "egypt": "EG",
    "morocco": "MA",
    "ethiopia": "ET",
    "sudan": "SD",
    "algeria": "DZ",
    "tunisia": "TN",
    "cameroon": "CM",
    "senegal": "SN",
    "ivory coast": "CI",
    "cote d'ivoire": "CI",
    "benin": "BJ",
    "mali": "ML",
    "niger": "NE",
    "burkina faso": "BF",
    "liberia": "LR",
    "sierra leone": "SL",
    "rwanda": "RW",
    "zimbabwe": "ZW",
    "zambia": "ZM",
    "malawi": "MW",
    "mozambique": "MZ",
    "angola": "AO",
    "botswana": "BW",
    "namibia": "NA",
    "lesotho": "LS",
    "eswatini": "SZ",
    "swaziland": "SZ",
    "djibouti": "DJ",
    "eritrea": "ER",
    "somalia": "SO",
    "libya": "LY",
    "madagascar": "MG",
    "mauritius": "MU",
    "seychelles": "SC",
    "comoros": "KM",
    "maldives": "MV",
    "sri lanka": "LK",
    "india": "IN",
    "pakistan": "PK",
    "bangladesh": "BD",
    "nepal": "NP",
    "bhutan": "BT",
    "china": "CN",
    "japan": "JP",
    "korea": "KR",
    "south korea": "KR",
    "north korea": "KP",
    "taiwan": "TW",
    "hong kong": "HK",
    "mongolia": "MN",
    "indonesia": "ID",
    "malaysia": "MY",
    "thailand": "TH",
    "vietnam": "VN",
    "philippines": "PH",
    "singapore": "SG",
    "brunei": "BN",
    "united states": "US",
    "usa": "US",
    "america": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "britain": "GB",
    "england": "GB",
    "canada": "CA",
    "australia": "AU",
    "new zealand": "NZ",
    "france": "FR",
    "germany": "DE",
    "italy": "IT",
    "spain": "ES",
    "portugal": "PT",
    "netherlands": "NL",
    "belgium": "BE",
    "switzerland": "CH",
    "austria": "AT",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "ireland": "IE",
    "poland": "PL",
    "russia": "RU",
    "ukraine": "UA",
    "brazil": "BR",
    "argentina": "AR",
    "mexico": "MX",
    "colombia": "CO",
    "peru": "PE",
    "venezuela": "VE",
    "chile": "CL",
    "ecuador": "EC",
    "cuba": "CU",
    "guinea": "GN",
    "western sahara": "EH",
    "cape verde": "CV",
}


def parse_natural_query(q: str):
    q_lower = q.lower().strip()
    tokens = q_lower.split()

    filters = {}
    min_age = None
    max_age = None
    gender = None
    age_group = None
    country_id = None

    gender_keywords = {
        "male": "male", "males": "male",
        "female": "female", "females": "female",
        "man": "male", "men": "male",
        "woman": "female", "women": "female",
    }

    age_group_keywords = {
        "child": "child", "children": "child", "kid": "child", "kids": "child",
        "teen": "teenager", "teens": "teenager", "teenager": "teenager", "teenagers": "teenager",
        "adult": "adult", "adults": "adult",
        "senior": "senior", "seniors": "senior", "elderly": "senior", "old": "senior",
    }

    for token in tokens:
        if token in gender_keywords:
            gender = gender_keywords[token]
        elif token in age_group_keywords:
            age_group = age_group_keywords[token]
        elif token == "young":
            min_age = 16
            max_age = 24

    match_from = re.search(r"from\s+(\w+(?:\s+\w+)?)", q_lower)
    if match_from:
        country_name = match_from.group(1)
        if country_name in COUNTRY_NAME_TO_CODE:
            country_id = COUNTRY_NAME_TO_CODE[country_name]
        else:
            parts = country_name.split()
            if parts[0] in COUNTRY_NAME_TO_CODE:
                country_id = COUNTRY_NAME_TO_CODE[parts[0]]

    for i, token in enumerate(tokens):
        if token in ["above", "over", "older"]:
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                min_age = int(tokens[i + 1])
        elif token in ["below", "under", "younger"]:
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                max_age = int(tokens[i + 1])

    if tokens and tokens[-1].isdigit():
        prev_word = tokens[-2] if len(tokens) > 1 else ""
        if prev_word in ["above", "over", "older", "than"]:
            min_age = int(tokens[-1])
        elif prev_word in ["below", "under", "younger", "than"]:
            max_age = int(tokens[-1])

    if gender:
        filters["gender"] = gender
    if age_group:
        filters["age_group"] = age_group
    if country_id:
        filters["country_id"] = country_id
    if min_age is not None:
        filters["min_age"] = min_age
    if max_age is not None:
        filters["max_age"] = max_age

    if not filters:
        return None

    return filters


def exclude_search_from_profile_routes(request: Request, call_next):
    if request.url.path.startswith("/api/profiles/"):
        path_parts = request.url.path.split("/")
        if len(path_parts) > 3 and path_parts[3] == "search":
            return call_next(request)
    return call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(title="HNG Profile Management API", lifespan=lifespan)

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
    from sqlalchemy import func
    import httpx
    import asyncio

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
                    "age": existing.age,
                    "age_group": existing.age_group,
                    "country_id": existing.country_id,
                    "country_name": existing.country_name,
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
            "age": profile.age,
            "age_group": profile.age_group,
            "country_id": profile.country_id,
            "country_name": profile.country_name,
            "country_probability": profile.country_probability,
            "created_at": profile.created_at,
        },
    }


@app.get("/api/profiles/search")
async def search_profiles(
    q: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if q is None or q.strip() == "":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty parameter"},
        )

    filters = parse_natural_query(q)

    if filters is None:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Unable to interpret query"},
        )

    query = db.query(ProfileModel)

    if "gender" in filters:
        query = query.filter(ProfileModel.gender.ilike(filters["gender"]))
    if "country_id" in filters:
        query = query.filter(ProfileModel.country_id.ilike(filters["country_id"]))
    if "age_group" in filters:
        query = query.filter(ProfileModel.age_group.ilike(filters["age_group"]))
    if "min_age" in filters:
        query = query.filter(ProfileModel.age >= filters["min_age"])
    if "max_age" in filters:
        query = query.filter(ProfileModel.age <= filters["max_age"])

    total = query.count()

    offset = (page - 1) * limit
    profiles = query.offset(offset).limit(limit).all()

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "gender": p.gender,
                "gender_probability": p.gender_probability,
                "age": p.age,
                "age_group": p.age_group,
                "country_id": p.country_id,
                "country_name": p.country_name,
                "country_probability": p.country_probability,
                "created_at": p.created_at,
            }
            for p in profiles
        ],
    }


@app.get("/api/profiles")
async def get_all_profiles(
    gender: str = Query(default=None),
    country_id: str = Query(default=None),
    age_group: str = Query(default=None),
    min_age: int = Query(default=None),
    max_age: int = Query(default=None),
    min_gender_probability: float = Query(default=None),
    min_country_probability: float = Query(default=None),
    sort_by: str = Query(default=None),
    order: str = Query(default="asc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if sort_by is not None and sort_by not in ["age", "created_at", "gender_probability"]:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid query parameters"},
        )

    if order not in ["asc", "desc"]:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid query parameters"},
        )

    query = db.query(ProfileModel)

    if gender:
        query = query.filter(ProfileModel.gender.ilike(gender))
    if country_id:
        query = query.filter(ProfileModel.country_id.ilike(country_id))
    if age_group:
        query = query.filter(ProfileModel.age_group.ilike(age_group))
    if min_age is not None:
        query = query.filter(ProfileModel.age >= min_age)
    if max_age is not None:
        query = query.filter(ProfileModel.age <= max_age)
    if min_gender_probability is not None:
        query = query.filter(ProfileModel.gender_probability >= min_gender_probability)
    if min_country_probability is not None:
        query = query.filter(ProfileModel.country_probability >= min_country_probability)

    if sort_by:
        sort_column = getattr(ProfileModel, sort_by)
        if order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    total = query.count()

    offset = (page - 1) * limit
    profiles = query.offset(offset).limit(limit).all()

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "gender": p.gender,
                "gender_probability": p.gender_probability,
                "age": p.age,
                "age_group": p.age_group,
                "country_id": p.country_id,
                "country_name": p.country_name,
                "country_probability": p.country_probability,
                "created_at": p.created_at,
            }
            for p in profiles
        ],
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
            "age": profile.age,
            "age_group": profile.age_group,
            "country_id": profile.country_id,
            "country_name": profile.country_name,
            "country_probability": profile.country_probability,
            "created_at": profile.created_at,
        },
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
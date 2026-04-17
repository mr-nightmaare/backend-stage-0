# Profile Management API

A FastAPI service that creates profiles by integrating with Genderize, Agify, and Nationalize APIs, stores them in a database, and exposes CRUD endpoints for profile management.

Built for **HNG14 — Backend Stage 1**.

---

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite with SQLAlchemy ORM
- **HTTP Client:** httpx (async)
- **ASGI Server:** Uvicorn

---

## External APIs

| API | Endpoint | Purpose |
|-----|----------|---------|
| Genderize | `https://api.genderize.io?name={name}` | Gender prediction |
| Agify | `https://api.agify.io?name={name}` | Age estimation |
| Nationalize | `https://api.nationalize.io?name={name}` | Country prediction |

---

## Endpoints

### `POST /api/profiles`

Create a new profile. If a profile with the same name exists, returns the existing one.

**Request:**
```json
{ "name": "ella" }
```

**Success Response (201 Created):**
```json
{
  "status": "success",
  "data": {
    "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
    "name": "ella",
    "gender": "female",
    "gender_probability": 0.99,
    "sample_size": 1234,
    "age": 46,
    "age_group": "adult",
    "country_id": "CM",
    "country_probability": 0.85,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

**Duplicate Response (201):**
```json
{
  "status": "success",
  "message": "Profile already exists",
  "data": { ...existing profile... }
}
```

---

### `GET /api/profiles/{id}`

Get a single profile by ID.

**Success Response (200):**
```json
{
  "status": "success",
  "data": {
    "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
    "name": "emmanuel",
    "gender": "male",
    "gender_probability": 0.99,
    "sample_size": 383650,
    "age": 49,
    "age_group": "adult",
    "country_id": "NG",
    "country_probability": 0.17,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

---

### `GET /api/profiles`

Get all profiles with optional filtering.

**Query Parameters:**
- `gender` — Filter by gender (case-insensitive)
- `country_id` — Filter by country code (case-insensitive)
- `age_group` — Filter by age group: child, teenager, adult, senior (case-insensitive)

**Example:** `GET /api/profiles?gender=male&country_id=NG`

**Success Response (200):**
```json
{
  "status": "success",
  "count": 2,
  "data": [
    {
      "id": "id-1",
      "name": "emmanuel",
      "gender": "male",
      "age": 49,
      "age_group": "adult",
      "country_id": "NG"
    }
  ]
}
```

---

### `DELETE /api/profiles/{id}`

Delete a profile by ID.

**Success Response (204 No Content)**

---

## Error Responses

| Status | Condition |
|--------|-----------|
| `400`  | Missing or empty name |
| `404`  | Profile not found |
| `502`  | External API returned invalid response |

All errors follow this structure:

```json
{
  "status": "error",
  "message": "<error message>"
}
```

### 502 Conditions

| API | Condition |
|-----|-----------|
| Genderize | `gender: null` or `count: 0` |
| Agify | `age: null` |
| Nationalize | No country data |

---

## Classification Rules

### Age Groups

| Age Range | Group |
|-----------|-------|
| 0–12 | child |
| 13–19 | teenager |
| 20–59 | adult |
| 60+ | senior |

### Nationality

The country with the highest probability from the Nationalize API response is selected.

---

## Data Model

| Field | Type | Description |
|-------|------|-------------|
| id | UUID v7 | Unique identifier |
| name | string | Name (lowercase, indexed) |
| gender | string | Predicted gender |
| gender_probability | float | Gender prediction probability |
| sample_size | int | Genderize sample count |
| age | int | Estimated age |
| age_group | string | Age classification |
| country_id | string | Country code |
| country_probability | float | Country prediction probability |
| created_at | string | UTC timestamp (ISO 8601) |

---

## Setup & Run Locally

```bash
# Clone the repo
git clone https://github.com/<your-username>/<your-repo>.git
cd backend/stage-0

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

---

## Deployment

This project is deployment-ready for platforms like **Railway**, **Render**, **Heroku**, or **AWS**.

A `Procfile` is included for deployment.

---

## CORS

`Access-Control-Allow-Origin: *` is enabled to allow cross-origin requests.

---

## Project Structure

```
├── main.py           # Application code
├── requirements.txt  # Dependencies
├── Procfile          # Deployment config
├── profiles.db       # SQLite database (created on first run)
└── README.md         # This file
```

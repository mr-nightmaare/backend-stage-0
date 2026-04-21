# Profile Management API

A FastAPI service that creates profiles by integrating with Genderize, Agify, and Nationalize APIs, stores them in a database, and exposes CRUD endpoints for profile management with advanced filtering, sorting, pagination, and natural language search.

Built for **HNG14 - Backend Stage 2**.

---

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite with SQLAlchemy ORM
- **HTTP Client:** httpx (async)
- **ASGI Server:** Uvicorn

---

## Data Model

| Field | Type | Description |
|-------|------|-------------|
| id | UUID v7 | Unique identifier (primary key) |
| name | string | Name (unique, lowercase, indexed) |
| gender | string | Predicted gender (male/female) |
| gender_probability | float | Gender prediction confidence |
| age | int | Estimated age |
| age_group | string | Age classification (child/teenager/adult/senior) |
| country_id | string | ISO 3166-1 alpha-2 country code |
| country_name | string | Full country name |
| country_probability | float | Country prediction confidence |
| created_at | string | UTC timestamp (ISO 8601) |

### Age Group Classification

| Age Range | Group |
|-----------|-------|
| 0–12 | child |
| 13–19 | teenager |
| 20–59 | adult |
| 60+ | senior |

---

## Endpoints

### `GET /api/profiles`

Get all profiles with filtering, sorting, and pagination.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| gender | str | None | Filter by gender (male/female) |
| country_id | str | None | Filter by ISO country code |
| age_group | str | None | Filter by age group |
| min_age | int | None | Minimum age (inclusive) |
| max_age | int | None | Maximum age (inclusive) |
| min_gender_probability | float | None | Minimum gender confidence |
| min_country_probability | float | None | Minimum country confidence |
| sort_by | str | None | Sort by: age, created_at, gender_probability |
| order | str | asc | Order: asc, desc |
| page | int | 1 | Page number (>= 1) |
| limit | int | 10 | Results per page (1-50) |

**Example:**
```
GET /api/profiles?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc&page=1&limit=10
```

**Success Response (200):**
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "data": [
    {
      "id": "b3f9c1e2-7d4a-4c91-9c2a-1f0a8e5b6d12",
      "name": "emmanuel",
      "gender": "male",
      "gender_probability": 0.99,
      "age": 34,
      "age_group": "adult",
      "country_id": "NG",
      "country_name": "Nigeria",
      "country_probability": 0.85,
      "created_at": "2026-04-01T12:00:00Z"
    }
  ]
}
```

---

### `GET /api/profiles/search`

Natural language search endpoint.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | str | Required | Natural language query |
| page | int | 1 | Page number (>= 1) |
| limit | int | 10 | Results per page (1-50) |

**Example:**
```
GET /api/profiles/search?q=young males from nigeria
```

**Supported Keywords:**

| Keyword/Phrase | Filter Applied |
|----------------|----------------|
| male, males, man, men | gender=male |
| female, females, woman, women | gender=female |
| young | min_age=16, max_age=24 |
| child, children, kid, kids | age_group=child |
| teen, teens, teenager, teenagers | age_group=teenager |
| adult, adults | age_group=adult |
| senior, seniors, elderly, old | age_group=senior |
| above N, over N, older than N | min_age=N |
| below N, under N, younger than N | max_age=N |
| from <country> | country_id=<ISO code> |

**Country Name Mapping:**
The parser supports mapping common country names to ISO codes. Examples: "nigeria" → "NG", "kenya" → "KE", "united states" → "US", "america" → "US", etc.

**Success Response (200):**
```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 150,
  "data": [...]
}
```

---

### `POST /api/profiles`

Create a new profile using external APIs.

**Request:**
```json
{ "name": "john" }
```

---

### `GET /api/profiles/{id}`

Get a single profile by ID.

---

### `DELETE /api/profiles/{id}`

Delete a profile by ID.

---

## Natural Language Parser

### How It Works

1. **Tokenization:** The query is lowercased and split into tokens.
2. **Gender Extraction:** Keywords like "male", "female", "man", "women" are matched.
3. **Age Group Extraction:** Keywords like "child", "teen", "adult", "senior" are matched.
4. **Age Range Extraction:** "young" maps to ages 16-24. Numeric patterns like "above 30" are parsed.
5. **Country Extraction:** The pattern "from <country>" is matched using regex.
6. **Filter Building:** Extracted keywords are converted into database filters.

### Supported Keywords

- **Gender:** male, males, man, men, female, females, woman, women
- **Age Groups:** child, children, kid, kids, teen, teens, teenager, teenagers, adult, adults, senior, seniors, elderly, old
- **Age Ranges:**
  - "young" → ages 16-24
  - "above N", "over N", "older than N" → min_age=N
  - "below N", "under N", "younger than N" → max_age=N
- **Country:** "from <country_name>" → country_id=<ISO code>
- ** Ignored Terms:** people, persons (no filter applied)

### Parsing Logic Flow

```
Input Query (e.g., "young males from nigeria")
            ↓
        Lowercase + Tokenize
            ↓
    Extract Gender → gender=male
    Extract "young" → min_age=16, max_age=24
    Extract "from nigeria" → country_id=NG
            ↓
        Build Filter Dict
            ↓
    Apply to SQLAlchemy Query
            ↓
    Paginate + Return Results
```

---

## Limitations & Edge Cases

### Unsupported Query Patterns

1. **Complex Boolean Logic:** The parser does NOT support AND/OR operations. "males or females" returns an error.
2. **Age Specifications Outside Ranges:** "age 25" without "above" or "below" is not interpreted.
3. **Multiple Countries:** "from nigeria and kenya" is not supported.
4. **Negation:** "not from nigeria" or "excluding males" is not supported.
5. **Comparative Ages:** "older than 18 but younger than 30" parses only the first numeric.
6. **Hyphenated Country Names:** "south africa" works, but "south-korea" does not.
7. **Partial Matches:** "Niger" (without "ia") may not map correctly.
8. **Spelling Variations:** Only exact keyword matches work. "girl" → not interpreted, must use "female".

### Edge Cases

1. **No Filters Extracted:** If the query contains no recognizable keywords, returns `{ "status": "error", "message": "Unable to interpret query" }`.
2. **Empty Query:** Returns `{ "status": "error", "message": "Missing or empty parameter" }`.
3. **Numeric Age Without Context:** "30 year old male" is not parsed properly; use "males above 30" instead.
4. **Multiple Age Group Keywords:** "adult senior" will use the last one encountered.

---

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Missing or empty parameter, invalid query parameters |
| 404 | Profile not found |
| 422 | Invalid parameter type |
| 500/502 | Server failure or upstream API error |

All errors follow this structure:

```json
{
  "status": "error",
  "message": "<error message>"
}
```

---

## Database Seeding

On startup, the application automatically seeds the database with 2026 profiles from `seed_profiles.json` if the table is empty or has fewer than 2026 records.

- Re-running the seed does NOT create duplicates (uses INSERT OR IGNORE on name).
- Each seeded profile gets a UUID v7 and UTC timestamp.

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

## CORS

`Access-Control-Allow-Origin: *` is enabled to allow cross-origin requests.

---

## Project Structure

```
├── main.py              # Application code
├── seed_profiles.json   # 2026 profiles for seeding
├── requirements.txt    # Dependencies
├── Procfile             # Deployment config
├── profiles.db          # SQLite database (created on first run)
└── README.md           # This file
```
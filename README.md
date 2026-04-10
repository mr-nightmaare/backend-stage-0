# Name Classifier API

A lightweight FastAPI service that integrates with the [Genderize API](https://genderize.io) to classify names by predicted gender, confidence level, and sample size.

Built for **HNG14 — Backend Stage 0**.

---

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **HTTP Client:** httpx (async)
- **ASGI Server:** Uvicorn

---

## API Endpoint

### `GET /api/classify?name={name}`

Classifies a given name using the Genderize API and returns a processed response.

#### Success Response (`200 OK`)

```json
{
  "status": "success",
  "data": {
    "name": "john",
    "gender": "male",
    "probability": 0.99,
    "sample_size": 1234,
    "is_confident": true,
    "processed_at": "2026-04-01T12:00:00Z"
  }
}
```

#### Error Responses

| Status | Condition |
|--------|-----------|
| `400`  | Missing or empty `name` query parameter |
| `422`  | `name` is not a valid string |
| `502`  | Upstream Genderize API failure or timeout |
| `500`  | Internal server error |

All errors follow this structure:

```json
{
  "status": "error",
  "message": "<error message>"
}
```

#### Edge Case

If Genderize returns `gender: null` or `count: 0`, the API responds with:

```json
{
  "status": "error",
  "message": "No prediction available for the provided name"
}
```

---

## Processing Logic

| Field          | Source / Rule |
|----------------|-------------|
| `name`         | Extracted from Genderize response |
| `gender`       | Extracted from Genderize response |
| `probability`  | Extracted from Genderize response |
| `sample_size`  | Renamed from Genderize `count` |
| `is_confident` | `true` when `probability >= 0.7` **AND** `sample_size >= 100` |
| `processed_at` | Generated per request — UTC, ISO 8601 |

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
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

---

## Deployment

This project is deployment-ready for platforms like **Vercel**, **Railway**, **Heroku**, or **AWS**.

A `Procfile` is included for Heroku/Railway-style deployments.

---

## CORS

`Access-Control-Allow-Origin: *` is enabled to allow cross-origin requests from the grading script.

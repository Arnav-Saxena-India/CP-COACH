# Adaptive Competitive Programming Coach - Backend

A FastAPI-based backend that provides problem recommendations for competitive programmers based on their Codeforces rating and selected topics.

## Features

- Fetch user rating from Codeforces API
- Store user profiles in SQLite database
- Recommend problems based on rating-based heuristic
- Filter problems by topic/tag
- Track solved problems

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: SQLite (local dev) / PostgreSQL (production)
- **HTTP Client**: Requests

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application entry point
│   ├── database.py      # Database configuration
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic validation schemas
│   ├── recommender.py   # Problem recommendation logic
│   └── routes.py        # API endpoints
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

Start the development server:

```bash
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`.

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### GET /user/{handle}

Fetch user rating from Codeforces and store/update in database.

**Example:**
```bash
curl http://localhost:8000/user/tourist
```

**Response:**
```json
{
  "id": 1,
  "handle": "tourist",
  "rating": 3849,
  "created_at": "2025-12-27T12:00:00",
  "last_problem_solved": false
}
```

### GET /recommend

Get problem recommendations based on user rating and topic.

**Query Parameters:**
- `handle` (required): Codeforces username
- `topic` (required): Topic/tag to filter problems

**Example:**
```bash
curl "http://localhost:8000/recommend?handle=tourist&topic=dp"
```

**Response:**
```json
{
  "problems": [
    {
      "id": 1,
      "name": "Boredom",
      "rating": 1500,
      "tags": "dp",
      "url": "https://codeforces.com/problemset/problem/455/A"
    }
  ],
  "target_rating": 3949,
  "message": null
}
```

### POST /solve/{problem_id}

Mark a problem as solved by the user.

**Query Parameters:**
- `handle` (required): Codeforces username

**Example:**
```bash
curl -X POST "http://localhost:8000/solve/1?handle=tourist"
```

### GET /problems

List all available problems, optionally filtered by topic.

**Query Parameters:**
- `topic` (optional): Topic/tag to filter problems

**Example:**
```bash
curl "http://localhost:8000/problems?topic=graphs"
```

## Recommendation Heuristic

The recommendation algorithm uses a simple rating-based heuristic:

1. If the user solved their last recommended problem:
   - `target_rating = user_rating + 100`
2. Otherwise:
   - `target_rating = user_rating - 50`

Problems are filtered by:
- Matching the selected topic (tag)
- Rating within ±150 of the target rating
- Not already solved by the user

The top 3 matching problems are returned.

## Database

The application uses SQLite for local development. The database file (`cp_coach.db`) is created automatically on first run.

### Models

- **User**: Stores Codeforces handle, rating, and solved status
- **Problem**: Stores problem metadata (name, rating, tags, URL)
- **SolvedProblem**: Junction table tracking user-problem relationships

## Environment Variables

For production, you can configure the database URL:

```bash
# .env file
DATABASE_URL=postgresql://user:password@localhost/cp_coach
```

## License

MIT

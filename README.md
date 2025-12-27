# Adaptive Competitive Programming Coach

A full-stack web application that recommends competitive programming problems based on user's Codeforces rating and selected topics.

## Overview

This MVP application helps competitive programmers discover problems tailored to their skill level. It fetches user ratings from Codeforces, applies a simple heuristic to determine appropriate difficulty, and recommends problems matching the selected topic.

## Features

- **User Profile Fetching**: Retrieves user rating from Codeforces API
- **Topic-based Filtering**: Filter problems by topics (DP, Graphs, Binary Search, etc.)
- **Rating-based Recommendations**: Uses a heuristic to recommend problems at appropriate difficulty
- **Progress Tracking**: Mark problems as solved to improve future recommendations

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| External API | Codeforces API |

## Project Structure

```
PROJECT 1/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── database.py      # SQLAlchemy configuration
│   │   ├── models.py        # ORM models
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── recommender.py   # Recommendation logic
│   │   └── routes.py        # API endpoints
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Home page
│   │   ├── layout.tsx       # Root layout
│   │   ├── globals.css      # Global styles
│   │   └── recommend/
│   │       └── page.tsx     # Recommendations page
│   ├── components/
│   │   ├── TopicSelect.tsx  # Topic dropdown
│   │   └── ProblemCard.tsx  # Problem display card
│   ├── lib/
│   │   └── api.ts           # API client
│   ├── package.json
│   └── README.md
└── README.md                 # This file
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18.17+
- npm

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/user/{handle}` | Fetch user from Codeforces |
| GET | `/recommend?handle=...&topic=...` | Get recommendations |
| POST | `/solve/{problem_id}?handle=...` | Mark problem solved |
| GET | `/problems` | List all problems |
| GET | `/docs` | Swagger API documentation |

## Recommendation Heuristic

```
If user solved last problem:
    target_rating = user_rating + 100
Else:
    target_rating = user_rating - 50

Select problems:
- Matching selected topic
- Rating within ±150 of target_rating
- Not already solved
- Return top 3
```

## Sample Data

The application seeds 30 sample problems covering:
- Dynamic Programming
- Graphs (DFS, BFS, Dijkstra)
- Binary Search
- Greedy
- Math / Number Theory
- Strings
- Implementation

## Screenshots

### Home Page
- Enter Codeforces handle
- Select topic from dropdown
- Click "Get Recommendations"

### Recommendations Page
- View problem cards with ratings
- Click to open on Codeforces
- Mark problems as solved

## Development

### Backend API Docs

Visit http://localhost:8000/docs for interactive Swagger documentation.

### Environment Variables

**Backend** (optional):
```
DATABASE_URL=postgresql://user:password@localhost/cp_coach
```

**Frontend** `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Constraints (MVP)

- ❌ No authentication
- ❌ No machine learning
- ❌ No roadmap generation
- ❌ No browser extension
- ✅ Focus on correctness and clarity

## License

MIT

# Adaptive Competitive Programming Coach - Frontend

A Next.js 14 frontend for the CP Coach application. Provides a user interface for getting competitive programming problem recommendations based on Codeforces handle and selected topics.

## Features

- Enter Codeforces handle
- Select from various CP topics
- View personalized problem recommendations
- Mark problems as solved
- Direct links to problem pages

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Data Fetching**: Native Fetch API

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   ├── globals.css        # Global styles
│   └── recommend/
│       └── page.tsx       # Recommendations page
├── components/
│   ├── TopicSelect.tsx    # Topic dropdown component
│   └── ProblemCard.tsx    # Problem display card
├── lib/
│   └── api.ts             # API client functions
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── README.md
```

## Setup

### Prerequisites

- Node.js 18.17+
- npm or yarn
- Backend server running on http://localhost:8000

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. (Optional) Configure backend URL:
   Create a `.env.local` file:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

### Running the Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

### Building for Production

```bash
npm run build
npm start
```

## Pages

### Home Page (`/`)

The main page where users can:
- Enter their Codeforces handle
- Select a topic from the dropdown (DP, Graphs, Binary Search, etc.)
- Click "Get Recommendations" to see personalized problems

### Recommendations Page (`/recommend`)

Displays problem recommendations based on:
- User's Codeforces rating
- Selected topic
- Rating-based heuristic (±150 of target rating)

Features:
- Problem cards with name, rating, and tags
- Rating colors matching Codeforces color scheme
- Links to open problems on Codeforces
- Button to mark problems as solved

## Components

### TopicSelect

A dropdown component for selecting CP topics:
- Dynamic Programming
- Graphs
- Binary Search
- Greedy
- Math
- Strings
- And more...

### ProblemCard

Displays a single problem with:
- Problem name
- Rating with color coding
- Tags
- Link to open on Codeforces
- Mark as solved button

## API Integration

The frontend communicates with the backend via the `lib/api.ts` module:

- `getUser(handle)` - Fetch user profile from Codeforces
- `getRecommendations(handle, topic)` - Get problem recommendations
- `markProblemSolved(problemId, handle)` - Mark a problem as solved
- `getProblems(topic?)` - List all available problems

## Styling

Uses Tailwind CSS with a minimal, clean design:
- White background
- Clear typography
- Simple borders and shadows
- No animations (as per requirements)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## License

MIT

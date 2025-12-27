How the Recommendation Engine Works
This project is not a random problem picker.
It implements a rule-based adaptive coaching system inspired by how human competitive programming mentors guide students.

The goal is to recommend the next best problem based on:

the user’s current rating,

the topic they want to practice,

and their recent performance.

1️⃣ User Performance Awareness
For each user, the system tracks their most recent problem attempt.

If the last attempt was Accepted (AC) → difficulty increases

If the last attempt was Wrong Answer (WA) → difficulty slightly decreases

If the user has no history → difficulty stays at current rating

This avoids both:

giving problems that are too easy, and

overwhelming the user with problems that are too hard.

2️⃣ Target Difficulty Calculation
A target rating is computed using a simple, transparent heuristic:

AC → target = user_rating + 100

WA → target = user_rating - 50

No history → target = user_rating

The target rating is always clamped to a safe range to prevent extreme jumps.

This keeps the user in the learning zone—challenged, but not stuck.

3️⃣ Topic-Sensitive Filtering
Users explicitly choose a topic (e.g. dp, graphs, binary search).

Only problems that:

match the selected topic, and

fall within a difficulty window (±150 rating points)

are considered.

This ensures focused practice, not random exposure.

4️⃣ Solve-History Awareness
Problems the user has already solved are excluded from recommendations.

This prevents:

repetition,

wasted effort,

and artificial inflation of progress.

5️⃣ Ranking Strategy
All remaining candidate problems are ranked by:

distance = |problem_rating − target_rating|
Problems closest to the target difficulty are prioritized.

This keeps progression smooth and incremental, similar to how experienced CP coaches design practice sets.

6️⃣ Explainable Recommendations (“Why this problem?”)
Every recommended problem includes a human-readable explanation, for example:

“Recommended because its rating (1580) closely matches your target difficulty (1600).”

This makes the system:

transparent,

trustworthy,

and educational.

Users understand why a problem was chosen, not just what to solve.

7️⃣ Safe Fallback Behavior
If no problems exist within the target difficulty range:

the system falls back to the easiest unsolved problems in the selected topic,

and clearly communicates this decision.

This guarantees that the user is never blocked.

8️⃣ Design Philosophy
No black-box ML — decisions are deterministic and debuggable

Extensible architecture — skill graphs, learning velocity, and roadmaps can be added without rewriting core logic

User-centric — optimized for learning, not just metrics

Example Walkthrough
User

Rating: 1500

Topic: Dynamic Programming

Last verdict: AC

System

Target difficulty → 1600

Filters DP problems in range 1450–1750

Excludes solved problems

Ranks by closeness to 1600

Returns top 3 with explanations

Why This Matters
Most CP platforms provide problem lists.

This system provides guidance.

It behaves like a personal CP coach, not a static database.

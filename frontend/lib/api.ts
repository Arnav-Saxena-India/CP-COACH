/**
 * API client for communicating with the CP Coach backend.
 * Uses native Fetch API as specified in requirements.
 */

// Backend API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://cp-coach-backend.onrender.com';

/**
 * User profile response from the backend
 */
export interface User {
    id: number;
    handle: string;
    rating: number;
    created_at: string;
    last_problem_solved: boolean;
}

/**
 * Problem data structure
 */
export interface Problem {
    id: number;
    name: string;
    rating: number;
    tags: string;
    url: string;
}

/**
 * Recommendation response from the backend
 */
export interface RecommendationResponse {
    problems: Problem[];
    target_rating: number;
    message: string | null;
}

/**
 * API error structure
 */
export interface ApiError {
    detail: string;
}

/**
 * Fetch user profile from Codeforces via backend.
 * Creates or updates user in the database.
 * 
 * @param handle - Codeforces username
 * @returns User profile data
 * @throws Error if request fails
 */
export async function getUser(handle: string): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/user/${encodeURIComponent(handle)}`);

    if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.detail || 'Failed to fetch user profile');
    }

    return response.json();
}

/**
 * Get problem recommendations for a user.
 * 
 * @param handle - Codeforces username
 * @param topic - Topic/tag to filter problems
 * @returns Recommendation response with problems and target rating
 * @throws Error if request fails
 */
export async function getRecommendations(
    handle: string,
    topic: string
): Promise<RecommendationResponse> {
    const params = new URLSearchParams({
        handle: handle,
        topic: topic,
    });

    const response = await fetch(`${API_BASE_URL}/recommend?${params}`);

    if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.detail || 'Failed to get recommendations');
    }

    return response.json();
}

/**
 * Mark a problem as solved by the user.
 * 
 * @param problemId - ID of the problem to mark as solved
 * @param handle - Codeforces username
 * @returns Success message
 * @throws Error if request fails
 */
export async function markProblemSolved(
    problemId: number,
    handle: string
): Promise<{ message: string }> {
    const response = await fetch(
        `${API_BASE_URL}/solve/${problemId}?handle=${encodeURIComponent(handle)}`,
        { method: 'POST' }
    );

    if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.detail || 'Failed to mark problem as solved');
    }

    return response.json();
}

/**
 * Get all available problems, optionally filtered by topic.
 * 
 * @param topic - Optional topic/tag to filter problems
 * @returns Array of problems
 * @throws Error if request fails
 */
export async function getProblems(topic?: string): Promise<Problem[]> {
    const url = topic
        ? `${API_BASE_URL}/problems?topic=${encodeURIComponent(topic)}`
        : `${API_BASE_URL}/problems`;

    const response = await fetch(url);

    if (!response.ok) {
        const error: ApiError = await response.json();
        throw new Error(error.detail || 'Failed to fetch problems');
    }

    return response.json();
}

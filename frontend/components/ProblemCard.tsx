'use client';

import { Problem } from '@/lib/api';

/**
 * ProblemCard component for displaying a single problem.
 * Shows problem name, rating, tags, and links to Codeforces.
 */

interface ProblemCardProps {
    problem: Problem;
    onSolve?: (problemId: number) => void;
}

/**
 * Get rating color based on Codeforces rating scale
 */
function getRatingColor(rating: number): string {
    if (rating < 1200) return 'text-gray-600';      // Newbie
    if (rating < 1400) return 'text-green-600';     // Pupil
    if (rating < 1600) return 'text-cyan-600';      // Specialist
    if (rating < 1900) return 'text-blue-600';      // Expert
    if (rating < 2100) return 'text-violet-600';    // Candidate Master
    if (rating < 2400) return 'text-orange-500';    // Master
    return 'text-red-600';                           // Grandmaster+
}

/**
 * Parse comma-separated tags string into array
 */
function parseTags(tags: string): string[] {
    return tags.split(',').map(tag => tag.trim()).filter(Boolean);
}

export default function ProblemCard({ problem, onSolve }: ProblemCardProps) {
    const ratingColor = getRatingColor(problem.rating);
    const tagList = parseTags(problem.tags);

    return (
        <div className="card hover:shadow-md transition-shadow">
            {/* Problem header */}
            <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-semibold text-gray-900">
                    {problem.name}
                </h3>
                <span className={`font-bold ${ratingColor}`}>
                    {problem.rating}
                </span>
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-2 mb-4">
                {tagList.map((tag, index) => (
                    <span
                        key={index}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
                    >
                        {tag}
                    </span>
                ))}
            </div>

            {/* Actions */}
            <div className="flex gap-3">
                <a
                    href={problem.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary text-sm"
                >
                    Open Problem
                </a>
                {onSolve && (
                    <button
                        onClick={() => onSolve(problem.id)}
                        className="btn-secondary text-sm"
                    >
                        Mark Solved
                    </button>
                )}
            </div>
        </div>
    );
}

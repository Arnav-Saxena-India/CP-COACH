'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import ProblemCard from '@/components/ProblemCard';
import { getRecommendations, markProblemSolved, Problem, RecommendationResponse } from '@/lib/api';

/**
 * Recommendation page component.
 * Displays problem recommendations based on user handle and selected topic.
 */
export default function RecommendPage() {
    const router = useRouter();
    const searchParams = useSearchParams();

    const handle = searchParams.get('handle') || '';
    const topic = searchParams.get('topic') || '';

    // State
    const [data, setData] = useState<RecommendationResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    /**
     * Fetch recommendations on component mount
     */
    useEffect(() => {
        if (!handle || !topic) {
            router.push('/');
            return;
        }

        const fetchRecommendations = async () => {
            try {
                const response = await getRecommendations(handle, topic);
                setData(response);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load recommendations');
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [handle, topic, router]);

    /**
     * Handle marking a problem as solved
     */
    const handleSolve = async (problemId: number) => {
        try {
            await markProblemSolved(problemId, handle);
            // Refresh recommendations after marking solved
            const response = await getRecommendations(handle, topic);
            setData(response);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to mark problem as solved');
        }
    };

    // Loading state
    if (loading) {
        return (
            <div className="container-main">
                <div className="flex items-center justify-center py-20">
                    <div className="spinner w-8 h-8" />
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="container-main">
                <div className="max-w-md mx-auto card text-center">
                    <h2 className="text-xl font-semibold text-gray-900 mb-2">Error</h2>
                    <p className="text-red-600 mb-4">{error}</p>
                    <Link href="/" className="btn-primary inline-block">
                        Go Back
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="container-main">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">
                        Recommendations
                    </h1>
                    <p className="text-gray-600 mt-1">
                        For <span className="font-medium">{handle}</span> •
                        Topic: <span className="font-medium capitalize">{topic}</span> •
                        Target Rating: <span className="font-medium">{data?.target_rating}</span>
                    </p>
                </div>
                <Link href="/" className="btn-secondary">
                    ← Back
                </Link>
            </div>

            {/* Message if no problems found */}
            {data?.message && (
                <div className="card bg-yellow-50 border-yellow-200 mb-6">
                    <p className="text-yellow-800">{data.message}</p>
                </div>
            )}

            {/* Problems list */}
            {data?.problems && data.problems.length > 0 ? (
                <div className="space-y-4">
                    {data.problems.map((problem) => (
                        <ProblemCard
                            key={problem.id}
                            problem={problem}
                            onSolve={handleSolve}
                        />
                    ))}
                </div>
            ) : (
                <div className="card text-center py-10">
                    <p className="text-gray-600">
                        No problems found matching your criteria.
                    </p>
                    <p className="text-gray-500 text-sm mt-2">
                        Try selecting a different topic or check back later.
                    </p>
                </div>
            )}

            {/* Legend */}
            <div className="mt-8 text-sm text-gray-500">
                <p className="font-medium mb-2">Rating Colors:</p>
                <div className="flex flex-wrap gap-4">
                    <span className="text-gray-600">● Newbie (&lt;1200)</span>
                    <span className="text-green-600">● Pupil (1200-1399)</span>
                    <span className="text-cyan-600">● Specialist (1400-1599)</span>
                    <span className="text-blue-600">● Expert (1600-1899)</span>
                    <span className="text-violet-600">● Candidate Master (1900-2099)</span>
                    <span className="text-orange-500">● Master (2100-2399)</span>
                    <span className="text-red-600">● Grandmaster (2400+)</span>
                </div>
            </div>
        </div>
    );
}

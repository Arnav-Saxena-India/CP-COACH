'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import TopicSelect from '@/components/TopicSelect';
import { getUser } from '@/lib/api';

/**
 * Home page component.
 * Provides a form for entering Codeforces handle and selecting a topic.
 */
export default function HomePage() {
    const router = useRouter();

    // Form state
    const [handle, setHandle] = useState('');
    const [topic, setTopic] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    /**
     * Handle form submission.
     * Validates input, fetches user profile, and navigates to recommendations page.
     */
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // Validate inputs
        if (!handle.trim()) {
            setError('Please enter your Codeforces handle');
            return;
        }
        if (!topic) {
            setError('Please select a topic');
            return;
        }

        setLoading(true);

        try {
            // Fetch user profile from backend (validates handle with Codeforces)
            await getUser(handle.trim());

            // Navigate to recommendations page with query params
            const params = new URLSearchParams({
                handle: handle.trim(),
                topic: topic,
            });
            router.push(`/recommend?${params}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container-main">
            {/* Header */}
            <div className="text-center mb-10">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">
                    CP Coach
                </h1>
                <p className="text-gray-600">
                    Get personalized competitive programming problem recommendations
                </p>
            </div>

            {/* Main form card */}
            <div className="max-w-md mx-auto card">
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Handle input */}
                    <div>
                        <label
                            htmlFor="handle"
                            className="block text-sm font-medium text-gray-700 mb-2"
                        >
                            Codeforces Handle
                        </label>
                        <input
                            type="text"
                            id="handle"
                            value={handle}
                            onChange={(e) => setHandle(e.target.value)}
                            placeholder="Enter your handle (e.g., tourist)"
                            disabled={loading}
                            className="disabled:bg-gray-100 disabled:cursor-not-allowed"
                        />
                    </div>

                    {/* Topic selector */}
                    <TopicSelect
                        value={topic}
                        onChange={setTopic}
                        disabled={loading}
                    />

                    {/* Error message */}
                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}

                    {/* Submit button */}
                    <button
                        type="submit"
                        disabled={loading}
                        className="btn-primary w-full flex items-center justify-center gap-2"
                    >
                        {loading && <span className="spinner" />}
                        {loading ? 'Loading...' : 'Get Recommendations'}
                    </button>
                </form>
            </div>

            {/* Info section */}
            <div className="max-w-md mx-auto mt-8 text-center text-sm text-gray-500">
                <p>
                    Enter your Codeforces handle and select a topic to get problem
                    recommendations tailored to your current rating.
                </p>
            </div>
        </div>
    );
}

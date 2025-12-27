'use client';

/**
 * TopicSelect component for selecting competitive programming topics.
 * Provides a dropdown with common CP topics as options.
 */

interface TopicSelectProps {
    value: string;
    onChange: (value: string) => void;
    disabled?: boolean;
}

// Available topics for competitive programming problems
const TOPICS = [
    { value: 'dp', label: 'Dynamic Programming' },
    { value: 'graphs', label: 'Graphs' },
    { value: 'binary search', label: 'Binary Search' },
    { value: 'greedy', label: 'Greedy' },
    { value: 'math', label: 'Math' },
    { value: 'strings', label: 'Strings' },
    { value: 'implementation', label: 'Implementation' },
    { value: 'dfs', label: 'DFS' },
    { value: 'bfs', label: 'BFS' },
    { value: 'sorting', label: 'Sorting' },
    { value: 'number theory', label: 'Number Theory' },
    { value: 'two pointers', label: 'Two Pointers' },
];

export default function TopicSelect({ value, onChange, disabled }: TopicSelectProps) {
    return (
        <div className="w-full">
            <label
                htmlFor="topic-select"
                className="block text-sm font-medium text-gray-700 mb-2"
            >
                Select Topic
            </label>
            <select
                id="topic-select"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                disabled={disabled}
                className="w-full px-4 py-2 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
                <option value="">-- Select a topic --</option>
                {TOPICS.map((topic) => (
                    <option key={topic.value} value={topic.value}>
                        {topic.label}
                    </option>
                ))}
            </select>
        </div>
    );
}

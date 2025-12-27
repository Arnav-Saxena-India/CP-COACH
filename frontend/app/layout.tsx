import type { Metadata } from 'next';
import './globals.css';

/**
 * Application metadata for SEO
 */
export const metadata: Metadata = {
    title: 'CP Coach - Competitive Programming Problem Recommender',
    description: 'Get personalized competitive programming problem recommendations based on your Codeforces rating and preferred topics.',
};

/**
 * Root layout component that wraps all pages.
 * Provides consistent structure and global styles.
 */
export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body>
                <main className="min-h-screen bg-white">
                    {children}
                </main>
            </body>
        </html>
    );
}

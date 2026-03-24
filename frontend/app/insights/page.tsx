'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    Clock,
    BookOpen,
    Target,
    Brain,
    TrendingUp,
    AlertTriangle
} from 'lucide-react';
import { DashboardLayout } from '@/components/DashboardLayout';
import { GlowCard, StatCard, ProgressBar } from '@/components/ui/GlowCard';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useMode } from '@/contexts/ModeContext';
import { AssignmentUpload } from '@/components/dashboard/AssignmentUpload';
import { useRouter } from 'next/navigation';
import { SideHustleInsights } from '@/components/dashboard/SideHustleInsights';
import { API_BASE_URL } from '@/lib/api';

export default function InsightsPage() {
    const { user, mode, isLoading, isOnboarded } = useMode();
    const router = useRouter();

    // Stats State
    const [stats, setStats] = useState<any>({
        weak_areas: [],
        performance_graph: [],
        accuracy_rate: 0,
        exam_readiness: 0,
        agent_decisions: [],
        study_hours: "0h",
        syllabus_completion: 0
    });

    useEffect(() => {
        if (!isLoading && !isOnboarded) {
            router.push('/onboarding');
        }
    }, [isOnboarded, isLoading, router]);

    // Fetch data function
    const fetchDashboardData = async () => {
        if (!user?.uid) return;

        try {
            // Fetch Stats
            const statsRes = await fetch(`${API_BASE_URL}/stats/academic/${user.uid}`);
            if (statsRes.ok) {
                const data = await statsRes.json();
                setStats(data);
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        }
    };

    // Fetch data on mount
    useEffect(() => {
        fetchDashboardData();
    }, [user?.uid]);

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-background">
                <div className="animate-pulse text-lg text-muted-foreground">Loading...</div>
            </div>
        );
    }

    // If in Side Hustle mode, maybe show a different message or redirect?
    // For now, we'll just show the content, assuming the user navigated here intentionally.

    return (
        <DashboardLayout
            title={mode === 'side-hustle' ? "Side Hustle Metrics" : "Deep Insights"}
            subtitle={mode === 'side-hustle' ? "Track your practical skill building progress" : "Detailed performance metrics and AI analysis."}
        >
            {mode === 'side-hustle' ? (
                <SideHustleInsights />
            ) : (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className="space-y-8"
                >
                    {/* Stats Row */}
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
                        <StatCard
                            label="Study Hours Today"
                            value={stats.study_hours}
                            icon={<Clock className="h-5 w-5 text-primary" />}
                            delay={0}
                        />
                        <StatCard
                            label="Syllabus Complete"
                            value={`${stats.syllabus_completion}%`}
                            icon={<BookOpen className="h-5 w-5 text-primary" />}
                            delay={0.1}
                        />
                        <StatCard
                            label="Exam Readiness"
                            value={`${stats.exam_readiness}%`}
                            icon={<Target className="h-5 w-5 text-primary" />}
                            delay={0.2}
                        />
                        <StatCard
                            label="Accuracy Rate"
                            value={`${stats.accuracy_rate}%`}
                            icon={<Brain className="h-5 w-5 text-primary" />}
                            delay={0.3}
                        />
                    </div>

                    {/* Performance & AI Decisions */}
                    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                        {/* Performance Tracker */}
                        <GlowCard delay={0.4}>
                            <div className="mb-4 flex items-center gap-2">
                                <TrendingUp className="h-5 w-5 text-primary" />
                                <h2 className="font-heading text-xl font-bold">Academic Performance</h2>
                            </div>
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={stats.performance_graph}>
                                        <defs>
                                            <linearGradient id="colorMarks" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                                        <XAxis dataKey="name" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                                        <YAxis className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                                        <Tooltip
                                            contentStyle={{
                                                backgroundColor: 'hsl(var(--card))',
                                                border: '1px solid hsl(var(--border))',
                                                borderRadius: 'var(--radius)'
                                            }}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="marks"
                                            stroke="hsl(var(--primary))"
                                            fillOpacity={1}
                                            fill="url(#colorMarks)"
                                            strokeWidth={2}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="mt-4 flex items-center justify-center gap-6">
                                <div className="flex items-center gap-2">
                                    <div className="h-3 w-3 rounded-full bg-primary" />
                                    <span className="text-sm text-muted-foreground">Marks Trend</span>
                                </div>
                            </div>
                        </GlowCard>

                        {/* AI Agent Decisions */}
                        <GlowCard delay={0.5}>
                            <div className="mb-4 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className="relative">
                                        <Brain className="h-5 w-5 text-primary" />
                                        <span className="absolute -right-1 -top-1 flex h-2 w-2">
                                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                                            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                                        </span>
                                    </div>
                                    <h2 className="font-heading text-xl font-bold">AI Agent Decisions</h2>
                                </div>
                                <span className="text-xs text-muted-foreground">Live updates</span>
                            </div>
                            <div className="space-y-4">
                                {stats.agent_decisions.map((decision: any, index: number) => (
                                    <motion.div
                                        key={decision.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.5 + index * 0.1 }}
                                        className="rounded-lg border border-border bg-mode-accent-soft p-4"
                                    >
                                        <p className="text-sm">{decision.message}</p>
                                        <p className="mt-2 text-xs text-muted-foreground">{decision.time}</p>
                                    </motion.div>
                                ))}
                            </div>
                        </GlowCard>
                    </div>

                    {/* Reminders & Weak Areas Row */}
                    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                        <GlowCard className="h-[400px]">
                            <AssignmentUpload />
                        </GlowCard>

                        {/* Weak Areas */}
                        <GlowCard delay={0.3}>
                            <div className="mb-4 flex items-center gap-2">
                                <AlertTriangle className="h-5 w-5 text-destructive" />
                                <h2 className="font-heading text-xl font-bold">Weak Areas</h2>
                            </div>
                            <div className="space-y-4">
                                {stats.weak_areas.map((area: any, index: number) => (
                                    <motion.div
                                        key={index}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ delay: 0.4 + index * 0.1 }}
                                    >
                                        <div className="mb-1 flex items-center justify-between">
                                            <p className="font-medium">{area.topic}</p>
                                            <span className="text-xs text-muted-foreground">{area.confidence}% confidence</span>
                                        </div>
                                        <ProgressBar value={area.confidence} label="" showPercentage={false} />
                                    </motion.div>
                                ))}
                                {stats.weak_areas.length === 0 && (
                                    <p className="text-center text-zinc-500 text-sm py-4">No weak areas identified yet. Keep it up!</p>
                                )}
                            </div>
                        </GlowCard>
                    </div>
                </motion.div>
            )}
        </DashboardLayout>
    );
}

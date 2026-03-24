'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
    Clock,
    BookOpen,
    Target,
    Brain,
    TrendingUp,
    AlertTriangle,
    TrendingDown,
    Minus,
    Sparkles,
    RefreshCw,
} from 'lucide-react';
import { DashboardLayout } from '@/components/DashboardLayout';
import { GlowCard, StatCard, ProgressBar } from '@/components/ui/GlowCard';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useMode } from '@/contexts/ModeContext';
import { AssignmentUpload } from '@/components/dashboard/AssignmentUpload';
import { useRouter } from 'next/navigation';
import { SideHustleInsights } from '@/components/dashboard/SideHustleInsights';
import { API_BASE_URL } from '@/lib/api';
import { cn } from '@/lib/utils';

const TABS = ['Overview', 'Detail', 'How to Improve'] as const;
type Tab = typeof TABS[number];

function TrendBadge({ trend }: { trend: string }) {
    if (trend === 'worsening') return (
        <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-600">
            <TrendingDown className="h-3 w-3" /> Worsening
        </span>
    );
    if (trend === 'improving') return (
        <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-600">
            <TrendingUp className="h-3 w-3" /> Improving
        </span>
    );
    return (
        <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-500">
            <Minus className="h-3 w-3" /> Stable
        </span>
    );
}

export default function InsightsPage() {
    const { user, mode, isLoading, isOnboarded } = useMode();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<Tab>('Overview');
    const [aiSummary, setAiSummary] = useState<string | null>(null);
    const [isLoadingSummary, setIsLoadingSummary] = useState(false);

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

    const fetchDashboardData = async () => {
        if (!user?.uid) return;
        try {
            const statsRes = await fetch(`${API_BASE_URL}/stats/academic/${user.uid}`);
            if (statsRes.ok) {
                const data = await statsRes.json();
                setStats(data);
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        }
    };

    const fetchAISummary = async () => {
        if (!user?.uid) return;
        setIsLoadingSummary(true);
        try {
            const res = await fetch(`${API_BASE_URL}/stats/weak-area-summary/${user.uid}`);
            if (res.ok) {
                const data = await res.json();
                setAiSummary(data.summary);
            }
        } catch (e) {
            console.error('Failed to fetch AI summary:', e);
        } finally {
            setIsLoadingSummary(false);
        }
    };

    useEffect(() => {
        fetchDashboardData();
    }, [user?.uid]);

    useEffect(() => {
        if (activeTab === 'How to Improve' && !aiSummary && !isLoadingSummary) {
            fetchAISummary();
        }
    }, [activeTab]);

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-background">
                <div className="animate-pulse text-lg text-muted-foreground">Loading...</div>
            </div>
        );
    }

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
                        <StatCard label="Study Hours Today" value={stats.study_hours} icon={<Clock className="h-5 w-5 text-primary" />} delay={0} />
                        <StatCard label="Syllabus Complete" value={`${stats.syllabus_completion}%`} icon={<BookOpen className="h-5 w-5 text-primary" />} delay={0.1} />
                        <StatCard label="Exam Readiness" value={`${stats.exam_readiness}%`} icon={<Target className="h-5 w-5 text-primary" />} delay={0.2} />
                        <StatCard label="Accuracy Rate" value={`${stats.accuracy_rate}%`} icon={<Brain className="h-5 w-5 text-primary" />} delay={0.3} />
                    </div>

                    {/* Performance & AI Decisions */}
                    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
                                        <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 'var(--radius)' }} />
                                        <Area type="monotone" dataKey="marks" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorMarks)" strokeWidth={2} />
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

                        {/* Tabbed Weak Areas Card */}
                        <GlowCard delay={0.3} className="flex flex-col min-h-[400px]">
                            {/* Card Header */}
                            <div className="mb-4 flex items-center gap-2 shrink-0">
                                <AlertTriangle className="h-5 w-5 text-destructive" />
                                <h2 className="font-heading text-xl font-bold">Weak Areas</h2>
                                {stats.weak_areas.length > 0 && (
                                    <span className="text-[10px] font-black bg-destructive/10 text-destructive px-2 py-0.5 rounded-full">
                                        {stats.weak_areas.length}
                                    </span>
                                )}
                            </div>

                            {/* Tabs */}
                            <div className="flex gap-1 p-1 bg-zinc-100 rounded-xl mb-4 shrink-0">
                                {TABS.map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab)}
                                        className={cn(
                                            'flex-1 py-1.5 text-xs font-bold rounded-lg transition-all duration-200',
                                            activeTab === tab
                                                ? 'bg-primary shadow-sm text-zinc-900 dark:text-white'
                                                : 'text-zinc-500'
                                        )}
                                    >
                                        {tab}
                                    </button>
                                ))}
                            </div>

                            {/* Tab Content */}
                            <div className="flex-1 overflow-y-auto">
                                <AnimatePresence mode="wait">

                                    {/* OVERVIEW TAB */}
                                    {activeTab === 'Overview' && (
                                        <motion.div key="overview" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="space-y-4">
                                            {stats.weak_areas.length === 0 ? (
                                                <div className="flex flex-col items-center justify-center py-10 text-center">
                                                    <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-3">
                                                        <span className="text-xl">🎉</span>
                                                    </div>
                                                    <p className="text-sm font-medium text-muted-foreground">No weak areas identified yet. Complete more assessments!</p>
                                                </div>
                                            ) : stats.weak_areas.slice(0, 7).map((area: any, index: number) => (
                                                <motion.div 
                                                    key={index} 
                                                    initial={{ opacity: 0 }} 
                                                    animate={{ opacity: 1 }} 
                                                    transition={{ delay: index * 0.05 }}
                                                    className="p-3 rounded-xl bg-card border border-border shadow-sm transition-all hover:bg-muted/50"
                                                >
                                                    <div className="mb-2 flex items-center justify-between gap-2">
                                                        <p className="font-bold text-sm text-foreground truncate">{area.topic}</p>
                                                        <div className="flex items-center gap-2 shrink-0">
                                                            <TrendBadge trend={area.trend} />
                                                            <span className="text-xs font-bold text-muted-foreground">{area.confidence}%</span>
                                                        </div>
                                                    </div>
                                                    <ProgressBar value={area.confidence} label="" showPercentage={false} />
                                                </motion.div>
                                            ))}
                                        </motion.div>
                                    )}

                                    {/* DETAIL TAB */}
                                    {activeTab === 'Detail' && (
                                        <motion.div key="detail" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="space-y-4">
                                            {stats.weak_areas.length === 0 ? (
                                                <div className="flex flex-col items-center justify-center py-10 text-center">
                                                    <p className="text-sm font-medium text-muted-foreground">No data yet. Take some assessments first!</p>
                                                </div>
                                            ) : stats.weak_areas.map((area: any, index: number) => (
                                                <motion.div
                                                    key={index}
                                                    initial={{ opacity: 0, x: -4 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    transition={{ delay: index * 0.04 }}
                                                    className="rounded-2xl border border-border bg-card p-5 shadow-sm transition-all hover:shadow-md"
                                                >
                                                    {/* Topic Header */}
                                                    <div className="flex items-start justify-between gap-3 mb-3">
                                                        <div className="flex items-center gap-2">
                                                            <div className="h-2 w-2 rounded-full bg-destructive shrink-0 mt-1" />
                                                            <p className="font-extrabold text-[15px] text-foreground">{area.topic}</p>
                                                        </div>
                                                        <div className="flex items-center gap-2 shrink-0">
                                                            <TrendBadge trend={area.trend} />
                                                            <span className="text-[11px] font-bold text-muted-foreground">{area.count}×</span>
                                                        </div>
                                                    </div>
                                                    {/* Wrong Questions List */}
                                                    {area.wrong_questions && area.wrong_questions.length > 0 ? (
                                                        <div className="space-y-2.5">
                                                            {area.wrong_questions.map((wq: any, qi: number) => (
                                                                <div key={qi} className="rounded-xl bg-muted/50 border border-border p-3">
                                                                    <p className="text-xs font-semibold text-foreground leading-snug mb-1.5">{wq.question}</p>
                                                                    <div className="flex items-center gap-1.5">
                                                                        <span className="text-[10px] bg-primary/10 text-primary font-bold px-1.5 py-0.5 rounded-md">✓ Correct</span>
                                                                        <span className="text-[11px] text-foreground font-medium">{wq.correct}</span>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <p className="text-xs text-muted-foreground italic">Complete a new assessment to see specific questions.</p>
                                                    )}
                                                </motion.div>
                                            ))}
                                        </motion.div>
                                    )}

                                    {/* HOW TO IMPROVE TAB */}
                                    {activeTab === 'How to Improve' && (
                                        <motion.div key="improve" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="space-y-4">
                                            <div className="flex justify-end">
                                                <button
                                                    onClick={fetchAISummary}
                                                    disabled={isLoadingSummary}
                                                    className="flex items-center gap-1.5 text-xs font-bold text-primary hover:text-primary/80 disabled:opacity-50 transition-opacity"
                                                >
                                                    <RefreshCw className={cn("h-3.5 w-3.5", isLoadingSummary && "animate-spin")} />
                                                    Regenerate
                                                </button>
                                            </div>

                                            {isLoadingSummary ? (
                                                <div className="flex flex-col items-center justify-center py-12 gap-4">
                                                    <div className="relative">
                                                        <div className="h-12 w-12 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
                                                        <Sparkles className="absolute inset-0 m-auto h-5 w-5 text-primary animate-pulse" />
                                                    </div>
                                                    <p className="text-sm text-muted-foreground font-medium">Generating your personalised plan...</p>
                                                </div>
                                            ) : aiSummary ? (
                                                <div className="prose prose-sm dark:prose-invert max-w-none text-foreground leading-relaxed">
                                                    <ReactMarkdown
                                                        components={{
                                                            h2: ({ node, ...props }) => <h2 className="text-base font-extrabold text-zinc-900  mt-4 mb-2" {...props} />,
                                                            ul: ({ node, ...props }) => <ul className="space-y-1.5 list-disc pl-5 text-sm" {...props} />,
                                                            ol: ({ node, ...props }) => <ol className="space-y-1.5 list-decimal pl-5 text-sm" {...props} />,
                                                            li: ({ node, ...props }) => <li className="text-zinc-700 " {...props} />,
                                                            strong: ({ node, ...props }) => <strong className="text-zinc-900  font-bold" {...props} />,
                                                            p: ({ node, ...props }) => <p className="text-sm text-zinc-600  mb-2" {...props} />,
                                                        }}
                                                    >
                                                        {aiSummary}
                                                    </ReactMarkdown>
                                                </div>
                                            ) : (
                                                <p className="text-center text-zinc-500 text-sm py-8">No weak areas to analyse yet.</p>
                                            )}
                                        </motion.div>
                                    )}

                                </AnimatePresence>
                            </div>
                        </GlowCard>
                    </div>
                </motion.div>
            )}
        </DashboardLayout>
    );
}

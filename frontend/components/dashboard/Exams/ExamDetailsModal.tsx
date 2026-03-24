import { motion } from 'framer-motion';
import { X, Calendar, CheckCircle2, Circle, BookOpen, PlayCircle, Sparkles, Youtube, ExternalLink, Brain } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMode } from '@/contexts/ModeContext';
import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { API_BASE_URL } from '@/lib/api';

interface SyllabusItem {
    name: string;
    completed: boolean;
}

interface ExamDetailsModalProps {
    isOpen: boolean;
    onClose: () => void;
    exam: any; // Using any for simplicity as it matches the fetched structure
    onUpdate: () => void;
}

import { AssessmentModal } from './AssessmentModal';
import { YouTubeModal } from '@/components/dashboard/SideHustle/YouTubeModal';

export function ExamDetailsModal({ isOpen, onClose, exam, onUpdate }: ExamDetailsModalProps) {
    const { user } = useMode();
    const [activeTopicIdx, setActiveTopicIdx] = useState<number | null>(null);
    const [selectedVideoTopic, setSelectedVideoTopic] = useState<string | null>(null);
    const [selectedVideoSubject, setSelectedVideoSubject] = useState<string>("General");
    const [showAssessment, setShowAssessment] = useState(false);

    const [localSyllabus, setLocalSyllabus] = useState<any[]>([]);

    useEffect(() => {
        if (exam?.syllabus) {
            setLocalSyllabus(exam.syllabus);
        }
    }, [exam]);

    if (!isOpen || !exam) return null;

    const handleToggleTopic = async (index: number, currentStatus: boolean) => {
        // Optimistic Update
        const newStatus = !currentStatus;
        setLocalSyllabus(prev => prev.map((item, i) => i === index ? { ...item, completed: newStatus } : item));

        try {
            const response = await fetch(`${API_BASE_URL}/exams/${user?.uid}/${exam.id}/toggle`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic_index: index,
                    completed: newStatus
                })
            });

            if (!response.ok) throw new Error('Failed to update topic');

            // Notify parent to refresh in background
            onUpdate();

        } catch (error) {
            console.error("Error toggling topic:", error);
            toast.error("Failed to update progress");
            // Revert on error
            setLocalSyllabus(prev => prev.map((item, i) => i === index ? { ...item, completed: currentStatus } : item));
        }
    };

    const handleGetHelp = async (topic: string, index: number) => {
        setSelectedVideoTopic(topic);
        setSelectedVideoSubject(exam.subject || "General");
    };

    const totalTopics = localSyllabus.length;
    const completedTopics = localSyllabus.filter(t => t.completed).length;
    const progress = totalTopics > 0 ? Math.round((completedTopics / totalTopics) * 100) : 0;
    const readiness = exam.readiness_score ? Math.round(exam.readiness_score) : 0;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/50 backdrop-blur-sm p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white overflow-hidden shadow-2xl flex flex-col max-h-[90vh]"
            >
                {/* Header */}
                <div className="bg-zinc-50 p-6 border-b border-zinc-200 flex items-start justify-between shrink-0">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <span className="px-2 py-1 rounded bg-primary/20 text-primary text-[10px] font-bold uppercase tracking-wider">
                                {exam.subject}
                            </span>
                            {readiness > 0 && (
                                <span className={cn(
                                    "px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider",
                                    readiness >= 70 ? "bg-green-500/20 text-green-500" : "bg-yellow-500/20 text-yellow-500"
                                )}>
                                    Readiness: {readiness}%
                                </span>
                            )}
                        </div>
                        <h2 className="text-2xl font-bold text-zinc-900 mb-1">{exam.title}</h2>
                        <div className="flex items-center gap-2 text-zinc-500 text-sm">
                            <Calendar className="h-4 w-4" />
                            <span>{new Date(exam.date).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
                        </div>
                    </div>
                    <button onClick={onClose} className="rounded-lg p-2 hover:bg-zinc-100 text-zinc-400 hover:text-zinc-900">
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* content */}
                <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">

                    {/* Progress Section */}
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-zinc-500">Syllabus Completion</span>
                                <span className="text-zinc-900 font-bold">{progress}%</span>
                            </div>
                            <div className="h-3 w-full bg-zinc-100 rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${progress}%` }}
                                    className={cn(
                                        "h-full rounded-full transition-all duration-500",
                                        progress >= 100 ? "bg-green-500" : "bg-primary"
                                    )}
                                />
                            </div>
                        </div>

                        {/* Assessment Button */}
                        <Button
                            className="w-full gap-2 font-bold relative overflow-hidden group"
                            onClick={() => setShowAssessment(true)}
                            disabled={progress < 10} // Unlock after some progress
                        >
                            <div className="absolute inset-0 bg-gradient-to-r from-primary/0 via-white/10 to-primary/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                            <Brain className="h-4 w-4" />
                            Review Materials & AI Assessment
                        </Button>
                        {progress < 10 && (
                            <p className="text-[10px] text-center text-zinc-400">
                                Complete 10% of syllabus to unlock assessment
                            </p>
                        )}
                        <p className="text-xs text-zinc-500 text-center mt-1">
                            {completedTopics} of {totalTopics} topics covered
                        </p>
                    </div>

                    {/* Topics List */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider flex items-center gap-2">
                            <BookOpen className="h-4 w-4 text-primary" />
                            Topics Checklist
                        </h3>

                        <div className="space-y-2">
                            {localSyllabus && localSyllabus.map((topic: any, idx: number) => (
                                <div key={idx} className="space-y-2">
                                    <div
                                        className={cn(
                                            "flex items-center justify-between p-3 rounded-xl border transition-all group",
                                            topic.completed
                                                ? "bg-primary/5 border-primary/20"
                                                : "bg-zinc-50 border-zinc-200 hover:border-zinc-300"
                                        )}
                                    >
                                        <div
                                            className="flex items-center gap-3 cursor-pointer flex-1"
                                            onClick={() => handleToggleTopic(idx, topic.completed)}
                                        >
                                            <div className={cn(
                                                "h-5 w-5 rounded-full flex items-center justify-center transition-colors",
                                                topic.completed ? "text-primary" : "text-zinc-300 group-hover:text-zinc-400"
                                            )}>
                                                {topic.completed ? <CheckCircle2 className="h-5 w-5" /> : <Circle className="h-5 w-5" />}
                                            </div>
                                            <span className={cn(
                                                "text-sm font-medium transition-colors select-none",
                                                topic.completed ? "text-zinc-500 line-through opacity-70" : "text-zinc-700"
                                            )}>
                                                {topic.name}
                                            </span>
                                        </div>

                                        {!topic.completed && (
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => handleGetHelp(topic.name, idx)}
                                                className="h-7 w-7 p-0 rounded-full hover:bg-primary/20 text-zinc-500 hover:text-primary"
                                                title="Get AI Recommendations"
                                            >
                                                <PlayCircle className="h-4 w-4" />
                                            </Button>
                                        )}
                                    </div>


                                </div>
                            ))}

                            {(!localSyllabus || localSyllabus.length === 0) && (
                                <p className="text-center text-zinc-500 text-sm py-4 italic">No topics listed.</p>
                            )}
                        </div>
                    </div>

                </div>
            </motion.div>

            <AssessmentModal
                isOpen={showAssessment}
                onClose={() => setShowAssessment(false)}
                exam={exam}
                onUpdate={onUpdate}
            />

            <YouTubeModal
                isOpen={!!selectedVideoTopic}
                onClose={() => setSelectedVideoTopic(null)}
                topic={selectedVideoTopic || ""}
                subject={selectedVideoSubject}
            />
        </div>
    );
}

'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Calendar, BookOpen, Plus, Sparkles, GraduationCap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useMode } from '@/contexts/ModeContext';
import { toast } from 'sonner';
import { API_BASE_URL } from '@/lib/api';

interface AddExamModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export function AddExamModal({ isOpen, onClose, onSuccess }: AddExamModalProps) {
    const { user, userProfile } = useMode();
    const [isLoading, setIsLoading] = useState(false);

    const [formData, setFormData] = useState({
        subject: '',
        title: '',
        date: '',
        syllabus: '',
    });

    const subjects = userProfile?.academicSubjects || [];

    const handleSubmit = async () => {
        if (!formData.subject || !formData.date || !formData.title) {
            toast.error("Please fill in all required fields");
            return;
        }

        setIsLoading(true);
        try {
            // Parse syllabus topics (split by commas or newlines)
            const syllabusList = formData.syllabus
                .split(/[\n,]/)
                .map(s => s.trim())
                .filter(s => s.length > 0)
                .map(s => ({ name: s, completed: false }));

            const response = await fetch(`${API_BASE_URL}/exams/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    uid: user?.uid,
                    subject: formData.subject,
                    title: formData.title,
                    date: formData.date,
                    syllabus: syllabusList
                })
            });

            if (!response.ok) throw new Error('Failed to create exam');

            toast.success('Exam added successfully! 📅');
            onSuccess();
            onClose();

            // Reset form
            setFormData({
                subject: '',
                title: '',
                date: '',
                syllabus: '',
            });

        } catch (error) {
            console.error('Error creating exam:', error);
            toast.error('Failed to add exam');
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-100 flex items-center justify-center bg-white/50 backdrop-blur-sm p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl max-h-[90vh] z-100 overflow-y-auto"
            >
                <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                            <GraduationCap className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-foreground">Add Upcoming Exam</h2>
                            <p className="text-xs text-muted-foreground">Track your preparation and deadlines</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="rounded-lg p-2 hover:bg-muted text-muted-foreground hover:text-foreground">
                        <X className="h-5 w-5" />
                    </button>
                </div>

                <div className="space-y-4">

                    <div className="grid grid-cols-2 gap-4">
                        {/* Subject Select */}
                        <div className="space-y-2">
                            <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Subject</Label>
                            <Select
                                value={formData.subject}
                                onValueChange={(val) => setFormData({ ...formData, subject: val })}
                            >
                                <SelectTrigger className="bg-muted border-border text-foreground">
                                    <SelectValue placeholder="Select Subject" />
                                </SelectTrigger>
                                <SelectContent className="bg-card border-border overflow-hidden">
                                    {subjects.map(sub => (
                                        <SelectItem key={sub} value={sub} className="text-foreground focus:bg-primary focus:text-white cursor-pointer">{sub}</SelectItem>
                                    ))}
                                    {subjects.length === 0 && (
                                        <SelectItem value="General" className="text-foreground focus:bg-primary focus:text-white cursor-pointer">General</SelectItem>
                                    )}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Exam Date */}
                        <div className="space-y-2">
                            <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Exam Date</Label>
                            <Input
                                type="date"
                                value={formData.date}
                                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                                className="bg-muted border-border text-foreground focus:border-primary appearance-none"
                            />
                        </div>
                    </div>

                    {/* Exam Title */}
                    <div className="space-y-2">
                        <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Exam Title / Description</Label>
                        <Input
                            placeholder="e.g. Mid-Term, Finals, Unit Test 1"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            className="bg-muted border-border text-foreground focus:border-primary"
                        />
                    </div>

                    {/* Syllabus */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Syllabus Topics</Label>
                            <span className="text-[10px] text-muted-foreground">Separate by comma or newline</span>
                        </div>
                        <Textarea
                            placeholder="List the main topics... e.g. Algebra, Calculus, Trigonometry"
                            value={formData.syllabus}
                            onChange={(e) => setFormData({ ...formData, syllabus: e.target.value })}
                            className="resize-none bg-muted border-border text-foreground focus:border-primary h-32 text-sm"
                        />
                    </div>
                </div>

                <div className="mt-8">
                    <Button
                        onClick={handleSubmit}
                        disabled={isLoading}
                        className="w-full h-12 text-base font-bold bg-primary hover:bg-primary/90 text-white rounded-xl shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] transition-all active:scale-[0.98]"
                    >
                        {isLoading ? 'Adding Exam...' : 'Add to Schedule'}
                    </Button>
                </div>
            </motion.div>
        </div>
    );
}

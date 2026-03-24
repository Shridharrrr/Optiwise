'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Upload, Check, AlertCircle, Loader2, Trophy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useDropzone } from 'react-dropzone';
import confetti from 'canvas-confetti';
import { API_BASE_URL } from '@/lib/api';

interface ProjectSubmissionModalProps {
    isOpen: boolean;
    onClose: () => void;
    project: any;
    onSuccess: (result: any) => void;
}

export function ProjectSubmissionModal({ isOpen, onClose, project, onSuccess }: ProjectSubmissionModalProps) {
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any | null>(null);

    const onDrop = (acceptedFiles: File[]) => {
        const file = acceptedFiles[0];
        if (file) {
            setFile(file);
            const reader = new FileReader();
            reader.onloadend = () => {
                setPreview(reader.result as string);
            };
            reader.readAsDataURL(file);
        }
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'image/*': [] },
        maxFiles: 1
    });

    const handleSubmit = async () => {
        if (!file || !preview || !project) return;

        setLoading(true);
        try {
            // Retrieve UID from localStorage or context if available, 
            // but cleaner to pass it in. For now assuming we can get it from project context 
            // or parent component should handle the actual fetch call?
            // To keep it simple, we'll assume parent passes a submit handler OR we fetch here.
            // We'll fetch here, but need UID. Let's assume passed in project object has uid or we get from context.
            // Actually, simplest is to use the fetch here and assume we have the UID from a parent or context.
            // Let's rely on the parent SideHustleDashboard passing the user ID via props or we use context here.

            // Wait, I can't easily access context here without importing useMode.
            // Let's import useMode.

            const response = await fetch(`${API_BASE_URL}/projects/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    uid: project.uid, // We need to ensure project object has UID attached by parent
                    project_id: project.id,
                    image: preview
                })
            });

            if (!response.ok) throw new Error("Submission failed");

            const data = await response.json();
            setResult(data);

            if (data.passed) {
                confetti({
                    particleCount: 150,
                    spread: 60,
                    origin: { y: 0.7 }
                });
                setTimeout(() => {
                    onSuccess(data);
                }, 2000); // Wait a bit to show result before closing/refreshing
            } else {
                toast.error("Project didn't pass verification.");
            }

        } catch (error) {
            console.error(error);
            toast.error("Failed to submit project");
        } finally {
            setLoading(false);
        }
    };

    // Reset state on close
    const handleClose = () => {
        setFile(null);
        setPreview(null);
        setResult(null);
        setLoading(false);
        onClose();
    }

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={handleClose}
                    className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                />

                <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 20 }}
                    className="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl relative z-10 overflow-hidden flex flex-col max-h-[90vh]"
                >
                    {/* Header */}
                    <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
                        <div>
                            <h2 className="text-xl font-bold text-white">Submit Project</h2>
                            <p className="text-zinc-400 text-sm">{project?.title}</p>
                        </div>
                        <button onClick={handleClose} className="p-2 hover:bg-zinc-800 rounded-full text-zinc-400">
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-6 flex-1 overflow-y-auto">
                        {!result ? (
                            <div className="space-y-6">
                                <div
                                    {...getRootProps()}
                                    className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${isDragActive ? 'border-primary bg-primary/5' : 'border-zinc-700 hover:border-zinc-600 hover:bg-zinc-800/50'
                                        }`}
                                >
                                    <input {...getInputProps()} />
                                    {preview ? (
                                        <div className="relative aspect-video w-full rounded-lg overflow-hidden border border-zinc-700">
                                            <img src={preview} alt="Preview" className="w-full h-full object-cover" />
                                            <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 hover:opacity-100 transition-opacity">
                                                <p className="text-white text-sm font-medium">Click to change</p>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="flex flex-col items-center gap-3 py-4">
                                            <div className="w-12 h-12 rounded-full bg-zinc-800 flex items-center justify-center">
                                                <Upload className="w-6 h-6 text-zinc-400" />
                                            </div>
                                            <div>
                                                <p className="font-medium text-zinc-200">Click to upload screenshot</p>
                                                <p className="text-zinc-500 text-sm">or drag and drop SVG, PNG, JPG</p>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 flex gap-3">
                                    <AlertCircle className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
                                    <div className="text-sm">
                                        <p className="text-blue-200 font-medium mb-1">AI Grading Criteria</p>
                                        <ul className="text-blue-300 list-disc list-inside space-y-1">
                                            <li>Visual completeness of the UI</li>
                                            <li>Adherence to project description</li>
                                            <li>Evidence of features implemented</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center py-4 space-y-6">
                                {result.passed ? (
                                    <div className="space-y-4">
                                        <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto border-2 border-green-500/50">
                                            <Trophy className="h-10 w-10 text-green-500" />
                                        </div>
                                        <div>
                                            <h3 className="text-2xl font-bold text-white mb-2">Excellent Work!</h3>
                                            <p className="text-zinc-400">You've successfully completed this project.</p>
                                        </div>

                                        <div className="grid grid-cols-2 gap-4 max-w-xs mx-auto">
                                            <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700">
                                                <p className="text-zinc-500 text-xs uppercase font-bold tracking-wider">Grade</p>
                                                <p className="text-2xl font-bold text-emerald-400">{result.grade}/100</p>
                                            </div>
                                            <div className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-700">
                                                <p className="text-zinc-500 text-xs uppercase font-bold tracking-wider">XP Earned</p>
                                                <p className="text-2xl font-bold text-yellow-500">+{result.xp_awarded}</p>
                                            </div>
                                        </div>

                                        <div className="bg-zinc-800/30 p-4 rounded-lg text-left">
                                            <p className="text-sm text-zinc-300 italic">"{result.feedback}"</p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto border-2 border-red-500/50">
                                            <X className="h-10 w-10 text-red-500" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-white mb-2">Needs Improvement</h3>
                                            <p className="text-zinc-400 text-sm">The AI grader found some issues.</p>
                                        </div>

                                        <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-lg text-left">
                                            <p className="text-sm text-red-200">"{result.feedback}"</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t border-zinc-800 bg-zinc-900/50 flex justify-end gap-3">
                        {!result ? (
                            <>
                                <Button variant="ghost" onClick={handleClose}>Cancel</Button>
                                <Button
                                    onClick={handleSubmit}
                                    disabled={!file || loading}
                                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                                >
                                    {loading ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Analyzing...
                                        </>
                                    ) : (
                                        <>
                                            <Check className="mr-2 h-4 w-4" />
                                            Submit Logic
                                        </>
                                    )}
                                </Button>
                            </>
                        ) : (
                            <Button onClick={result.passed ? handleClose : () => setResult(null)} className="w-full">
                                {result.passed ? "Continue" : "Try Again"}
                            </Button>
                        )}
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}

'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Youtube, ExternalLink, Loader2, PlayCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { API_BASE_URL } from '@/lib/api';

interface VideoResource {
    id: string;
    title: string;
    thumbnail: string;
    duration: string;
    channel: string;
    link: string;
    viewCount: string;
}

interface YouTubeModalProps {
    isOpen: boolean;
    onClose: () => void;
    topic: string;
    subject: string;
}

export function YouTubeModal({ isOpen, onClose, topic, subject }: YouTubeModalProps) {
    const [videos, setVideos] = useState<VideoResource[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (isOpen && topic && subject) {
            fetchVideos();
        } else {
            setVideos([]);
            setLoading(true);
        }
    }, [isOpen, topic, subject]);

    const fetchVideos = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE_URL}/learning/recommend`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic, subject })
            });

            if (!res.ok) throw new Error("Failed to fetch videos");

            const data = await res.json();
            setVideos(data);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load video recommendations");
        } finally {
            setLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
                    />

                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="w-full max-w-4xl bg-card border border-border rounded-2xl shadow-2xl overflow-hidden relative z-10 max-h-[85vh] flex flex-col"
                    >
                        {/* Header */}
                        <div className="p-6 border-b border-border flex justify-between items-center bg-card/50">
                            <div>
                                <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                                    <Youtube className="h-6 w-6 text-red-600" />
                                    Recommended Videos
                                </h2>
                                <p className="text-muted-foreground text-sm mt-1">
                                    Top picks for learning about <span className="text-primary font-medium">{topic}</span>
                                </p>
                            </div>
                            <button
                                onClick={onClose}
                                className="p-2 hover:bg-accent rounded-full transition-colors text-muted-foreground hover:text-foreground"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto p-6 bg-background">
                            {loading ? (
                                <div className="flex flex-col items-center justify-center h-64 gap-4">
                                    <Loader2 className="h-10 w-10 text-primary animate-spin" />
                                    <p className="text-muted-foreground">Curating best videos for you...</p>
                                </div>
                            ) : videos.length > 0 ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {videos.map((video) => (
                                        <a
                                            key={video.id}
                                            href={video.link}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="group relative bg-card border border-border rounded-xl overflow-hidden hover:border-primary/50 transition-all hover:shadow-xl hover:shadow-primary/5 cursor-pointer block"
                                        >
                                            <div className="aspect-video w-full relative overflow-hidden">
                                                <img
                                                    src={video.thumbnail}
                                                    alt={video.title}
                                                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105 opacity-90 group-hover:opacity-100"
                                                />
                                                <div className="absolute inset-0 bg-black/40 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                                                    <div className="h-12 w-12 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center border border-white/40 text-white opacity-0 group-hover:opacity-100 transform scale-75 group-hover:scale-100 transition-all duration-300">
                                                        <PlayCircle className="h-6 w-6 fill-white text-transparent" />
                                                    </div>
                                                </div>
                                                <div className="absolute bottom-2 right-2 bg-black/80 text-white text-[10px] font-bold px-1.5 py-0.5 rounded text-xs">
                                                    {video.duration}
                                                </div>
                                            </div>

                                            <div className="p-4 space-y-2">
                                                <h3 className="font-semibold text-card-foreground line-clamp-2 leading-tight group-hover:text-primary transition-colors">
                                                    {video.title}
                                                </h3>

                                                <div className="flex items-center justify-between text-xs text-muted-foreground mt-3 border-t border-border pt-3">
                                                    <span className="flex items-center gap-1.5 hover:text-foreground transition-colors">
                                                        <span className="font-medium truncate max-w-[120px]">{video.channel}</span>
                                                    </span>
                                                    <span className="bg-secondary px-2 py-0.5 rounded-full font-mono text-[10px] text-secondary-foreground">
                                                        {video.viewCount} views
                                                    </span>
                                                </div>
                                            </div>
                                        </a>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-64 text-center">
                                    <p className="text-muted-foreground mb-2">No videos found for this topic.</p>
                                    <button
                                        onClick={fetchVideos}
                                        className="text-primary hover:underline text-sm"
                                    >
                                        Try Again
                                    </button>
                                </div>
                            )}
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}

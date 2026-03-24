'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Bot, ArrowRight, GraduationCap, Rocket, Zap, BookOpen, Code2, Target } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { signInWithPopup, GoogleAuthProvider } from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { toast } from 'sonner';
import { API_BASE_URL } from '@/lib/api';

export default function LoginPage() {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const handleGoogleSignIn = async () => {
        setIsLoading(true);
        try {
            const provider = new GoogleAuthProvider();
            const result = await signInWithPopup(auth, provider);
            const idToken = await result.user.getIdToken();

            const response = await fetch(`${API_BASE_URL}/auth/google/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id_token: idToken }),
            });

            if (!response.ok) throw new Error('Authentication failed');
            const userData = await response.json();
            const profileResponse = await fetch(`${API_BASE_URL}/profile/${userData.uid}`);

            if (profileResponse.ok) {
                router.push('/dashboard');
            } else {
                router.push('/onboarding');
            }

            toast.success('Signed in successfully!');
        } catch (error: any) {
            console.error('Sign in error:', error);
            toast.error(error.message || 'Failed to sign in');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full lg:grid lg:grid-cols-2">
            {/* Left Side - Visual Showcase */}
            <div className="hidden lg:flex relative flex-col justify-between bg-zinc-950 p-12 text-white overflow-hidden">
                {/* Background Decor */}
                <div className="absolute inset-0 bg-[radial-gradient(#333_1px,transparent_1px)] [background-size:16px_16px] opacity-20" />
                <div className="absolute top-0 right-0 h-[500px] w-[500px] bg-primary/20 blur-[100px] rounded-full translate-x-1/2 -translate-y-1/2" />
                <div className="absolute bottom-0 left-0 h-[500px] w-[500px] bg-[#a855f7]/20 blur-[100px] rounded-full -translate-x-1/2 translate-y-1/2" />

                {/* Branding */}
                <div className="relative z-10 flex items-center gap-2 font-bold text-xl">
                    <Bot className="w-8 h-8 text-primary" />
                    <span>Optiwise</span>
                </div>

                {/* Central Visual */}
                <div className="relative z-10 flex flex-col items-center justify-center flex-1 gap-12">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="relative"
                    >
                        {/* Orbiting Icons */}
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                            className="absolute inset-0 rounded-full border border-white/10 w-[400px] h-[400px] -m-24 opacity-50"
                        >
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-3 p-3 bg-zinc-900 rounded-xl border border-zinc-800 shadow-xl">
                                <GraduationCap className="w-6 h-6 text-primary" />
                            </div>
                            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-3 p-3 bg-zinc-900 rounded-xl border border-zinc-800 shadow-xl">
                                <Rocket className="w-6 h-6 text-[#a855f7]" />
                            </div>
                            <div className="absolute top-1/2 left-0 -translate-x-3 -translate-y-1/2 p-3 bg-zinc-900 rounded-xl border border-zinc-800 shadow-xl">
                                <Code2 className="w-6 h-6 text-blue-400" />
                            </div>
                            <div className="absolute top-1/2 right-0 translate-x-3 -translate-y-1/2 p-3 bg-zinc-900 rounded-xl border border-zinc-800 shadow-xl">
                                <Target className="w-6 h-6 text-pink-500" />
                            </div>
                        </motion.div>

                        <div className="text-center space-y-4 max-w-md relative z-10">
                            <h2 className="text-4xl font-extrabold tracking-tight tight-heading">
                                The Best of <br />
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-[#a855f7]">
                                    Both Worlds.
                                </span>
                            </h2>
                            <p className="text-zinc-400 leading-relaxed">
                                Join thousands of students seamlessly switching between acing exams and building their dream career.
                            </p>
                        </div>
                    </motion.div>
                </div>

                {/* Footer */}
                <div className="relative z-10 text-sm text-zinc-500">
                    © 2025 Optiwise
                </div>
            </div>

            {/* Right Side - Login Form */}
            <div className="flex items-center justify-center bg-background p-8 lg:p-16">
                <div className="w-full max-w-md space-y-10">
                    <div className="text-center space-y-4 lg:text-left">
                        <h1 className="text-4xl font-extrabold tracking-tight tight-heading">Welcome back</h1>
                        <p className="text-lg text-muted-foreground">
                            Sign in to your account to continue your journey
                        </p>
                    </div>

                    <div className="grid gap-4">
                        <Button
                            variant="outline"
                            size="lg"
                            className="w-full relative h-12 border-primary/20 hover:bg-primary/5 hover:text-primary transition-colors"
                            onClick={handleGoogleSignIn}
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <span className="absolute left-4 top-1/2 -translate-y-1/2 flex h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                            ) : (
                                <svg className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5" viewBox="0 0 24 24">
                                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                                </svg>
                            )}
                            Continue with Google
                        </Button>
                    </div>

                    <p className="px-8 text-center text-base text-muted-foreground">
                        <Button
                            variant="link"
                            className="hover:text-primary p-0 h-auto font-normal text-base"
                            onClick={() => router.push('/')}
                        >
                            <ArrowRight className="w-4 h-4 mr-1 rotate-180" /> Back to Home
                        </Button>
                    </p>
                </div>
            </div>
        </div>
    );
}

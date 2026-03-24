'use client';

import { AnimatePresence } from 'framer-motion';
import { DashboardLayout } from '@/components/DashboardLayout';
import { AcademicDashboard } from '@/components/dashboard/AcademicDashboard';
import { SideHustleDashboard } from '@/components/dashboard/SideHustleDashboard';
import { useMode } from '@/contexts/ModeContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Dashboard() {
  const { mode, userProfile, isOnboarded, isLoading } = useMode();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isOnboarded) {
      router.push('/onboarding');
    }
  }, [isOnboarded, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="animate-pulse text-lg text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!isOnboarded) {
    return null;
  }

  return (
    <DashboardLayout
      title={mode === 'academic' ? '🎓 Academic Dashboard' : '🚀 Side Hustle Dashboard'}
      subtitle={`Welcome back, ${userProfile?.name || 'Student'}! Here's your AI-optimized learning plan.`}
    >
      <AnimatePresence mode="wait">
        {mode === 'academic' ? (
          <AcademicDashboard />
        ) : (
          <SideHustleDashboard />
        )}
      </AnimatePresence>
    </DashboardLayout>
  );
}
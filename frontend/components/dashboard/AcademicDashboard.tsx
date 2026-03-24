'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Calendar,
  Settings,
} from 'lucide-react';
import { GlowCard } from '@/components/ui/GlowCard';
import { UpcomingDeadlines } from '@/components/UpcomingDeadlines';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useMode } from '@/contexts/ModeContext';
import { PlannerSettings, PlannerSettingsData } from './StudyPlanner/PlannerSettings';
import { PlannerCalendar, DaySchedule } from './StudyPlanner/PlannerCalendar';
import { API_BASE_URL } from '@/lib/api';

export function AcademicDashboard() {
  const { user, refreshTrigger } = useMode();

  // Planner State
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [scheduleData, setScheduleData] = useState<DaySchedule[] | null>(null);
  const [plannerView, setPlannerView] = useState<'daily' | 'weekly'>('daily');
  const [isGenerating, setIsGenerating] = useState(false);

  // Fetch data function
  const fetchDashboardData = async () => {
    if (!user?.uid) return;

    try {
      // Fetch Plan
      const planRes = await fetch(`${API_BASE_URL}/planner/latest/${user.uid}`);
      if (planRes.ok) {
        const data = await planRes.json();
        if (data.schedule && data.schedule.length > 0) {
          setScheduleData(data.schedule);
          // if (data.schedule.length > 1) setPlannerView('weekly');
        }
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  // Fetch data on mount and when refresh triggered
  useEffect(() => {
    fetchDashboardData();
  }, [user?.uid, refreshTrigger]);

  const handleGenerateSchedule = async (settings: PlannerSettingsData) => {
    setIsGenerating(true);
    try {
      const response = await fetch(`${API_BASE_URL}/planner/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uid: user?.uid,
          ...settings
        })
      });

      if (!response.ok) throw new Error('Failed to generate schedule');

      const data = await response.json();
      setScheduleData(data.schedule);
      setPlannerView(settings.view_mode);
      setIsSettingsOpen(false);
      toast.success('AI Schedule Generated Successfully!');
      fetchDashboardData();
    } catch (error) {
      console.error('Planner Error:', error);
      toast.error('Failed to generate schedule. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <motion.div
      key="academic"
      initial={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
      animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
      exit={{ opacity: 0, scale: 1.05, filter: 'blur(10px)', transition: { duration: 0.4, ease: "easeIn" } }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-6"
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[55fr_45fr]">
        {/* Advanced AI Study Planner */}
        <div className="">
          <GlowCard className="h-[560px] relative overflow-hidden flex flex-col">
            <div className="absolute top-0 right-0 p-4 z-10">
              <Button
                onClick={() => setIsSettingsOpen(true)}
                variant="outline"
                size="sm"
                className="gap-2 bg-white/5 border-white/10 hover:bg-white/10 hover:scale-105 text-xs cursor-pointer hover:text-black"
              >
                <Settings className="h-3.5 w-3.5" />
                Configure
              </Button>
            </div>

            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <Calendar className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="font-heading text-xl font-bold">AI Study Schedule</h2>
                <p className="text-xs text-zinc-500">
                  {scheduleData ? ` Optimized for ${plannerView} view` : 'Auto-generated based on your constraints'}
                </p>
              </div>
            </div>

            <div className="flex-1 min-h-0">
              <PlannerCalendar scheduleData={scheduleData} viewMode={plannerView} />
            </div>
          </GlowCard>
        </div>

        {/* Upcoming Deadlines Panel */}
        <div className="">
          <UpcomingDeadlines onRefreshStats={fetchDashboardData} />
        </div>
      </div>

      {/* Planner Settings Modal */}
      <PlannerSettings
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onGenerate={handleGenerateSchedule}
        isLoading={isGenerating}
      />
    </motion.div>
  );
}

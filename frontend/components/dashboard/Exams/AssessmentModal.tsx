"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  Brain,
  Trophy,
  TrendingUp,
  ChevronLeft,
  XCircle,
  Check,
  Target
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";
import { useMode } from "@/contexts/ModeContext";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/lib/api";

interface Question {
  id: string;
  question: string;
  options: string[];
  correct_answer?: number;
  topic_tag: string;
}

interface AssessmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  exam: any;
  onUpdate: () => void;
}

export function AssessmentModal({
  isOpen,
  onClose,
  exam,
  onUpdate,
}: AssessmentModalProps) {
  const { user } = useMode();
  const [step, setStep] = useState<"intro" | "quiz" | "result" | "analysis">("intro");
  const [isGenerating, setIsGenerating] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQIdx, setCurrentQIdx] = useState(0);
  const [answers, setAnswers] = useState<{ [key: string]: number }>({});
  const [result, setResult] = useState<any>(null);
  const [timeLeft, setTimeLeft] = useState(180);

  useEffect(() => {
    if (isOpen) {
      setStep("intro");
      setAnswers({});
      setResult(null);
      setTimeLeft(180);
    }
  }, [isOpen]);

  useEffect(() => {
    if (step === "quiz" && timeLeft > 0) {
      const timer = setInterval(() => setTimeLeft((prev) => prev - 1), 1000);
      return () => clearInterval(timer);
    } else if (timeLeft === 0 && step === "quiz") {
      handleSubmit();
      toast.info("Time's up! Submitting answers...");
    }
  }, [timeLeft, step]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleStart = async () => {
    setIsGenerating(true);
    try {
      const syllabusNames = exam.syllabus
        ? exam.syllabus.map((s: any) => s.name)
        : [];

      const res = await fetch(`${API_BASE_URL}/assessment/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: exam.subject,
          topics: syllabusNames,
          set_number: 1,
        }),
      });

      if (!res.ok) throw new Error("Failed to generate questions");

      const data = await res.json();
      setQuestions(data);
      setStep("quiz");
      setCurrentQIdx(0);
    } catch (error) {
      console.error(error);
      toast.error("Failed to start assessment");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleOptionSelect = (optionIdx: number) => {
    const currentQ = questions[currentQIdx];
    setAnswers((prev) => ({ ...prev, [currentQ.id]: optionIdx }));
  };

  const handleNext = () => {
    if (currentQIdx < questions.length - 1) {
      setCurrentQIdx((prev) => prev + 1);
    } else {
      handleSubmit();
    }
  };

  const handleSubmit = async () => {
    try {
      const formattedAnswers = Object.entries(answers).map(
        ([qid, selected]) => ({
          question_id: qid,
          selected: selected,
        }),
      );

      const res = await fetch(`${API_BASE_URL}/assessment/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          uid: user?.uid,
          exam_id: exam.id,
          set_number: 1,
          answers: formattedAnswers,
          questions: questions,
        }),
      });

      if (!res.ok) throw new Error("Submission failed");

      const data = await res.json();
      setResult(data);
      setStep("result");
      onUpdate();
    } catch (error) {
      toast.error("Failed to submit results");
    }
  };

  const handleFinish = () => {
    setStep("intro");
    onClose();
  };

  if (!isOpen || !exam) return null;

  return (
    <div className="fixed inset-0 z-[999] flex items-center justify-center bg-white/80 backdrop-blur-md p-4 sm:p-6 transition-all">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
        className="w-full sm:w-[650px] h-[600px] bg-white rounded-3xl overflow-hidden shadow-[0_32px_64px_-16px_rgba(0,0,0,0.3)] flex flex-col max-h-[90vh] border border-white/20 relative"
      >
        {/* Progress Bar Header for Quiz */}
        {step === "quiz" && questions.length > 0 && (
          <div className="absolute top-0 left-0 right-0 h-1 bg-zinc-100 z-50">
            <motion.div
              className="h-full bg-gradient-to-r from-primary to-[#a855f7]"
              initial={{ width: 0 }}
              animate={{ width: `${((currentQIdx + 1) / questions.length) * 100}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            />
          </div>
        )}

        {/* Header */}
        <div className="px-5 py-4 flex justify-between items-center bg-white/50 backdrop-blur-xl border-b border-zinc-100 z-40 sticky top-0">
          <div className="flex items-center gap-3">
            {step === "analysis" ? (
              <button onClick={() => setStep("result")} className="p-1 hover:bg-zinc-100 rounded-full transition-colors group">
                <ChevronLeft className="h-5 w-5 text-zinc-500 group-hover:text-zinc-900" />
              </button>
            ) : (
              <div className="p-1.5 bg-primary/10 rounded-lg">
                <Brain className="h-4 w-4 text-primary" />
              </div>
            )}
            <h2 className="font-extrabold text-base text-zinc-900 tracking-tight">
              {step === "analysis" ? "Detailed Analysis" : "Assessment Engine"}
            </h2>
          </div>

          {step === "quiz" && (
            <div className="flex items-center gap-2">
              <div className={cn(
                "px-2.5 py-1 rounded-lg font-mono text-xs font-bold border shadow-xs transition-colors",
                timeLeft < 30
                  ? "bg-red-50 text-red-600 border-red-200 animate-pulse"
                  : "bg-white text-zinc-600 border-zinc-200",
              )}
              >
                {formatTime(timeLeft)}
              </div>
            </div>
          )}

          {step !== "quiz" && (
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-zinc-100 rounded-full transition-colors"
            >
              <X className="h-4 w-4 text-zinc-400" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto custom-scrollbar relative">
          <AnimatePresence mode="wait">

            {/* INTRO STEP */}
            {step === "intro" && (
              <motion.div
                key="intro"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center p-8 md:p-10 text-center"
              >
                <div className="relative mb-6">
                  <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full" />
                  <div className="h-24 w-24 bg-white border border-zinc-100 shadow-lg rounded-full flex items-center justify-center relative z-10 mx-auto">
                    <Trophy className="h-10 w-10 text-primary" />
                  </div>
                </div>

                <h3 className="text-2xl font-extrabold text-zinc-900 mb-2 tracking-tight">
                  Ready to test your knowledge?
                </h3>
                <p className="text-zinc-500 max-w-sm mx-auto mb-6 text-sm">
                  Sharpen your skills with 10 questions intelligently generated from your syllabus:{" "}
                  <span className="text-zinc-800 font-bold block mt-1">
                    {exam.subject}
                  </span>
                </p>

                <div className="grid grid-cols-3 gap-2 w-full max-w-[360px] mx-auto mb-8">
                  <div className="bg-zinc-50 border border-zinc-100 p-3 rounded-2xl flex flex-col items-center">
                    <Target className="w-4 h-4 text-primary mb-1.5" />
                    <span className="text-[11px] font-bold text-zinc-900">10 MCQs</span>
                    <span className="text-[9px] text-zinc-500 uppercase font-semibold">Questions</span>
                  </div>
                  <div className="bg-zinc-50 border border-zinc-100 p-3 rounded-2xl flex flex-col items-center">
                    <TrendingUp className="w-4 h-4 text-emerald-500 mb-1.5" />
                    <span className="text-[11px] font-bold text-zinc-900">Adaptive</span>
                    <span className="text-[9px] text-zinc-500 uppercase font-semibold">Difficulty</span>
                  </div>
                  <div className="bg-zinc-50 border border-zinc-100 p-3 rounded-2xl flex flex-col items-center">
                    <CheckCircle className="w-4 h-4 text-blue-500 mb-1.5" />
                    <span className="text-[11px] font-bold text-zinc-900">Readiness</span>
                    <span className="text-[9px] text-zinc-500 uppercase font-semibold">Tracking</span>
                  </div>
                </div>

                <Button
                  size="lg"
                  onClick={handleStart}
                  className="w-full max-w-[280px] h-12 rounded-xl font-bold text-base shadow-md hover:shadow-primary/20 hover:-translate-y-0.5 transition-all"
                  disabled={isGenerating}
                >
                  {isGenerating ? (
                    <div className="flex items-center gap-2">
                      <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Igniting Engine...
                    </div>
                  ) : (
                    "Start Assessment"
                  )}
                </Button>
              </motion.div>
            )}

            {/* QUIZ STEP */}
            {step === "quiz" && questions.length > 0 && (
              <motion.div
                key="quiz"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="p-6 md:p-8 space-y-6 min-h-[350px] flex flex-col"
              >
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-black text-primary bg-primary/10 px-2.5 py-1 rounded-full uppercase tracking-widest">
                      Question {currentQIdx + 1} of {questions.length}
                    </span>
                    <span className="text-[11px] font-semibold px-2.5 py-1 bg-zinc-100 rounded-full text-zinc-500 border border-zinc-200">
                      {questions[currentQIdx].topic_tag}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-zinc-900 leading-snug">
                    {questions[currentQIdx].question}
                  </h3>
                </div>

                <div className="space-y-2.5 flex-1 mt-4">
                  {questions[currentQIdx].options.map((option, idx) => {
                    const isSelected = answers[questions[currentQIdx].id] === idx;
                    return (
                      <div
                        key={idx}
                        onClick={() => handleOptionSelect(idx)}
                        className={cn(
                          "p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 flex items-center gap-3 group hover:-translate-y-px",
                          isSelected
                            ? "bg-primary/5 border-primary shadow-[0_4px_15px_rgba(var(--primary-rgb),0.1)]"
                            : "bg-white border-zinc-100 hover:border-zinc-300 hover:shadow-xs text-zinc-600",
                        )}
                      >
                        <div
                          className={cn(
                            "h-7 w-7 rounded-full border-2 flex items-center justify-center text-[13px] font-bold transition-all shrink-0",
                            isSelected
                              ? "border-primary bg-primary text-white"
                              : "border-zinc-200 text-zinc-400 group-hover:border-zinc-400",
                          )}
                        >
                          {String.fromCharCode(65 + idx)}
                        </div>
                        <span
                          className={cn(
                            "text-sm",
                            isSelected ? "text-zinc-900 font-bold" : "font-medium"
                          )}
                        >
                          {option}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <div className="flex justify-end pt-4 mt-auto">
                  <Button
                    size="lg"
                    onClick={handleNext}
                    disabled={answers[questions[currentQIdx].id] === undefined}
                    className="gap-2 h-12 px-6 rounded-xl font-bold text-sm shadow-md hover:-translate-y-px transition-all"
                  >
                    {currentQIdx === questions.length - 1
                      ? "End & Submit"
                      : "Next Question"}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </motion.div>
            )}

            {/* RESULT STEP */}
            {step === "result" && result && (
              <motion.div
                key="result"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-6 md:p-8 flex flex-col gap-8"
              >
                <div className="flex flex-col items-center gap-6 text-center">
                  {/* Top: Score Ring */}
                  <div className="relative shrink-0 perspective-1000">
                    <div className={cn(
                      "absolute inset-0 rounded-full blur-[30px] opacity-25",
                      result.accuracy >= 70 ? "bg-emerald-500" : result.accuracy >= 40 ? "bg-yellow-500" : "bg-red-500"
                    )} />

                    <div className="relative h-40 w-40 bg-white rounded-full shadow-lg flex items-center justify-center p-1.5 border border-zinc-50">
                      <svg className="h-full w-full rotate-[-90deg]" viewBox="0 0 160 160">
                        <circle
                          cx="80"
                          cy="80"
                          r="68"
                          stroke="currentColor"
                          strokeWidth="12"
                          fill="transparent"
                          className="text-zinc-100"
                        />
                        <motion.circle
                          cx="80"
                          cy="80"
                          r="68"
                          stroke="currentColor"
                          strokeWidth="12"
                          fill="transparent"
                          className={cn(
                            result.accuracy >= 70 ? "text-emerald-500" : result.accuracy >= 40 ? "text-yellow-500" : "text-red-500"
                          )}
                          strokeLinecap="round"
                          strokeDasharray={427}
                          initial={{ strokeDashoffset: 427 }}
                          animate={{ strokeDashoffset: 427 - (427 * result.accuracy) / 100 }}
                          transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
                        />
                      </svg>

                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <motion.span
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.8, type: "spring" }}
                          className="text-3xl font-extrabold text-zinc-900 tracking-tight"
                        >
                          {Math.round(result.accuracy)}%
                        </motion.span>
                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest mt-1">
                          Accuracy
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Bottom: Stats & Message */}
                  <div className="w-full space-y-5 flex flex-col items-center">
                    <div>
                      <h3 className="text-2xl font-extrabold text-zinc-900 tracking-tight">
                        {result.accuracy >= 90 ? "Outstanding Work!" :
                          result.accuracy >= 70 ? "Great Job!" :
                            result.accuracy >= 50 ? "Solid Effort!" : "Keep Practicing!"}
                      </h3>
                      <p className="text-sm text-zinc-500 mt-1 font-medium max-w-sm mx-auto">
                        {result.accuracy >= 70
                          ? "You've mastered these concepts nicely."
                          : "Identify your weak spots to improve your readiness."}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3 w-full max-w-xs mx-auto">
                      <div className="bg-zinc-50/80 p-4 rounded-2xl border border-zinc-100 flex flex-col items-center shadow-sm transition-shadow">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <CheckCircle className="h-4 w-4 text-emerald-500" />
                          <span className="text-[10px] text-zinc-500 uppercase font-black tracking-widest">Correct</span>
                        </div>
                        <span className="text-2xl font-extrabold text-zinc-900">{result.score}<span className="text-base text-zinc-400">/{result.total}</span></span>
                      </div>

                      <div className="bg-zinc-50/80 p-4 rounded-2xl border border-zinc-100 flex flex-col items-center shadow-sm transition-shadow">
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <TrendingUp className="h-4 w-4 text-blue-500" />
                          <span className="text-[10px] text-zinc-500 uppercase font-black tracking-widest">Readiness</span>
                        </div>
                        <span className="text-2xl font-extrabold text-zinc-900">{Math.round(result.readiness)}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Weak Areas */}
                <div className="w-full">
                  {result.weak_areas && result.weak_areas.length > 0 ? (
                    <div className="bg-red-50/50 border border-red-100/60 rounded-2xl p-4 shadow-sm">
                      <h4 className="text-xs font-extrabold text-red-700 mb-2.5 flex items-center gap-1.5 tracking-tight">
                        <AlertCircle className="h-3.5 w-3.5" />
                        Recommended Focus Areas
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {result.weak_areas.map((topic: string, i: number) => (
                          <span
                            key={i}
                            className="px-2.5 py-1 bg-white border border-red-200 text-red-600 text-[11px] font-bold rounded-full shadow-xs"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-emerald-50/50 border border-emerald-100/60 rounded-2xl p-5 flex flex-col items-center justify-center gap-1.5 shadow-sm">
                      <Trophy className="h-6 w-6 text-emerald-500 mb-0.5" />
                      <span className="text-emerald-800 text-xs font-extrabold">No weak areas detected!</span>
                      <span className="text-emerald-600/80 text-[11px] font-medium">You dominated this assessment.</span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-3 justify-end pt-3 border-t border-zinc-100">
                  <Button
                    variant="outline"
                    size="lg"
                    onClick={() => setStep("analysis")}
                    className="h-12 px-5 rounded-xl font-bold border-zinc-200 text-zinc-700 hover:bg-zinc-50"
                  >
                    View Detailed Analysis
                  </Button>
                  <Button
                    size="lg"
                    onClick={handleFinish}
                    className="h-12 px-6 rounded-xl font-bold bg-zinc-900 text-white hover:bg-zinc-800 shadow-lg hover:-translate-y-px transition-all"
                  >
                    Continue Journey
                  </Button>
                </div>
              </motion.div>
            )}

            {/* DETAILED ANALYSIS STEP */}
            {step === "analysis" && (
              <motion.div
                key="analysis"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="p-5 md:p-6 space-y-6"
              >
                <div className="space-y-4">
                  {questions.map((q, idx) => {
                    const userSelected = answers[q.id];
                    const isCorrect = userSelected === q.correct_answer;

                    return (
                      <div key={q.id} className="bg-white border text-zinc-900 border-zinc-200 rounded-2xl p-5 shadow-sm">
                        <div className="flex justify-between items-start mb-4">
                          <h4 className="text-base font-bold leading-snug">
                            <span className="text-zinc-400 mr-1.5">{idx + 1}.</span>
                            {q.question}
                          </h4>
                          <div className="shrink-0 ml-3">
                            {isCorrect ? (
                              <div className="bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider flex items-center gap-1">
                                <Check className="w-3 h-3" /> Correct
                              </div>
                            ) : (
                              <div className="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider flex items-center gap-1">
                                <XCircle className="w-3 h-3" /> Incorrect
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="space-y-2">
                          {q.options.map((opt, optIdx) => {
                            const isUserPick = userSelected === optIdx;
                            const isActualCorrect = q.correct_answer === optIdx;

                            let optionClass = "bg-zinc-50 border-zinc-100 text-zinc-600";
                            let icon = null;

                            if (isActualCorrect) {
                              optionClass = "bg-emerald-50 border-emerald-200 text-emerald-900 ring-1 ring-emerald-500/20";
                              icon = <CheckCircle className="w-4 h-4 text-emerald-500" />;
                            } else if (isUserPick && !isActualCorrect) {
                              optionClass = "bg-red-50 border-red-200 text-red-900 ring-1 ring-red-500/20";
                              icon = <XCircle className="w-4 h-4 text-red-500" />;
                            }

                            return (
                              <div key={optIdx} className={cn("p-3 rounded-xl border flex items-center justify-between transition-all", optionClass)}>
                                <div className="flex items-center gap-3">
                                  <div className="h-5 w-5 rounded-full border border-current opacity-40 flex items-center justify-center text-[11px] font-bold shrink-0">
                                    {String.fromCharCode(65 + optIdx)}
                                  </div>
                                  <span className={cn("text-[13px]", isActualCorrect || isUserPick ? "font-bold" : "font-medium")}>
                                    {opt}
                                  </span>
                                </div>
                                {icon && <div className="shrink-0">{icon}</div>}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="flex justify-end pt-5 border-t border-zinc-100 mt-6">
                  <Button
                    size="lg"
                    onClick={handleFinish}
                    className="h-12 px-6 rounded-xl font-bold bg-zinc-900 text-white hover:bg-zinc-800 shadow-md hover:-translate-y-px transition-all"
                  >
                    Finish Review
                  </Button>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}

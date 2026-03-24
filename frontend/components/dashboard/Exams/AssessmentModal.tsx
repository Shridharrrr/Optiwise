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
  correct_answer?: number; // Hidden from user until result? Actually backend sends it but we shouldn't peek.
  // Wait, backend sent it for grading? No, backend sends it to client for simple state, or we should hide it.
  // For security, usually hidden, but for hackathon client-side is fine or we trust the client to send it back.
  // My backend 'submit' takes 'questions' list BACK to verify.
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
  const [step, setStep] = useState<"intro" | "quiz" | "result">("intro");
  const [isGenerating, setIsGenerating] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQIdx, setCurrentQIdx] = useState(0);
  const [answers, setAnswers] = useState<{ [key: string]: number }>({}); // question_id -> selected_index
  const [result, setResult] = useState<any>(null);
  const [setNumber, setSetNumber] = useState(1); // 1, 2, 3
  const [timeLeft, setTimeLeft] = useState(180); // 3 minutes

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep("intro");
      setAnswers({});
      setResult(null);
      setTimeLeft(180);
      // Determine set number based on exam data if we had it, for now starts at 1
      // In a real app we'd fetch "current_set" from exam details.
    }
  }, [isOpen]);

  // Timer Logic
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
          set_number: 1, // Standardize to 1
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
          set_number: 1, // Standardize
          answers: formattedAnswers,
          questions: questions,
        }),
      });

      if (!res.ok) throw new Error("Submission failed");

      const data = await res.json();
      setResult(data);
      setStep("result");
      onUpdate(); // Refresh parent stats
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
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-white backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-2xl bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="p-4 border-b border-zinc-200 flex justify-between items-center bg-zinc-50">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-accent" />
            <h2 className="font-bold text-zinc-900">Assessment</h2>
          </div>

          {step === "quiz" && (
            <div
              className={cn(
                "px-3 py-1 rounded-full font-mono text-sm font-bold border",
                timeLeft < 30
                  ? "bg-red-500/10 text-red-600 border-red-200 animate-pulse"
                  : "bg-zinc-100 text-zinc-600 border-zinc-200",
              )}
            >
              {formatTime(timeLeft)}
            </div>
          )}

          <button
            onClick={onClose}
            className="p-1 hover:bg-zinc-100 rounded-full transition-colors"
          >
            <X className="h-5 w-5 text-zinc-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8 relative">
          <AnimatePresence mode="wait">
            {/* INTRO STEP */}
            {step === "intro" && (
              <motion.div
                key="intro"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-center space-y-6"
              >
                <div className="h-24 w-24 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Trophy className="h-12 w-12 text-accent" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-zinc-900 mb-2">
                    Ready to test your knowledge?
                  </h3>
                  <p className="text-zinc-500 max-w-md mx-auto">
                    This set contains 10 questions based on your syllabus:{" "}
                    <br />
                    <span className="text-zinc-800 italic font-medium">
                      {exam.subject}
                    </span>
                  </p>
                </div>
                <div className="bg-zinc-50 border border-zinc-100 p-4 rounded-lg max-w-md mx-auto text-sm text-zinc-500">
                  <p>• 10 Multiple Choice Questions</p>
                  <p>• Adapts to difficulty levels</p>
                  <p>• Updates your Exam Readiness Score</p>
                </div>
                <Button
                  size="lg"
                  onClick={handleStart}
                  className="w-full max-w-xs font-bold text-base"
                  disabled={isGenerating}
                >
                  {isGenerating
                    ? "Generating Questions..."
                    : "Start Assessment"}
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
                className="space-y-8"
              >
                {/* Progress Bar */}
                <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent transition-all duration-300"
                    style={{
                      width: `${((currentQIdx + 1) / questions.length) * 100}%`,
                    }}
                  />
                </div>

                <div className="space-y-4">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">
                      Question {currentQIdx + 1} of {questions.length}
                    </span>
                    <span className="text-xs px-2 py-1 bg-zinc-100 rounded text-zinc-500 border border-zinc-200">
                      {questions[currentQIdx].topic_tag}
                    </span>
                  </div>
                  <h3 className="text-xl font-medium text-zinc-900 leading-relaxed">
                    {questions[currentQIdx].question}
                  </h3>
                </div>

                <div className="space-y-3">
                  {questions[currentQIdx].options.map((option, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleOptionSelect(idx)}
                      className={cn(
                        "p-4 rounded-xl border cursor-pointer transition-all hover:bg-zinc-50 flex items-center gap-3",
                        answers[questions[currentQIdx].id] === idx
                          ? "bg-accent/10 border-accent/50 ring-1 ring-accent/50"
                          : "bg-white border-zinc-200 text-zinc-500",
                      )}
                    >
                      <div
                        className={cn(
                          "h-6 w-6 rounded-full border flex items-center justify-center text-xs font-bold transition-colors",
                          answers[questions[currentQIdx].id] === idx
                            ? "border-accent text-accent"
                            : "border-zinc-300 text-zinc-400",
                        )}
                      >
                        {String.fromCharCode(65 + idx)}
                      </div>
                      <span
                        className={
                          answers[questions[currentQIdx].id] === idx
                            ? "text-zinc-900 font-medium"
                            : "text-zinc-600"
                        }
                      >
                        {option}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="flex justify-end pt-4">
                  <Button
                    onClick={handleNext}
                    disabled={answers[questions[currentQIdx].id] === undefined}
                    className="gap-2"
                  >
                    {currentQIdx === questions.length - 1
                      ? "Finish & Submit"
                      : "Next Question"}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </motion.div>
            )}

            {/* RESULT STEP */}
            {/* RESULT STEP */}
            {/* RESULT STEP */}
            {step === "result" && result && (
              <motion.div
                key="result"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col gap-6 py-2"
              >
                <div className="flex flex-col md:flex-row items-center gap-8">
                  {/* Left: Score Ring */}
                  <div className="relative shrink-0">
                    {/* Outer Glow */}
                    <div className={cn(
                      "absolute inset-0 rounded-full blur-xl opacity-20",
                      result.accuracy >= 70 ? "bg-green-500" : result.accuracy >= 40 ? "bg-yellow-500" : "bg-red-500"
                    )} />

                    {/* Progress Ring */}
                    <div className="relative h-40 w-40">
                      <svg className="h-full w-full rotate-[-90deg]">
                        {/* Background Circle */}
                        <circle
                          cx="80"
                          cy="80"
                          r="70"
                          stroke="currentColor"
                          strokeWidth="10"
                          fill="transparent"
                          className="text-zinc-100"
                        />
                        {/* Progress Circle */}
                        <motion.circle
                          cx="80"
                          cy="80"
                          r="70"
                          stroke="currentColor"
                          strokeWidth="10"
                          fill="transparent"
                          className={cn(
                            result.accuracy >= 70 ? "text-green-500" : result.accuracy >= 40 ? "text-yellow-500" : "text-red-500"
                          )}
                          strokeLinecap="round"
                          strokeDasharray={440} // 2 * pi * 70
                          initial={{ strokeDashoffset: 440 }}
                          animate={{ strokeDashoffset: 440 - (440 * result.accuracy) / 100 }}
                          transition={{ duration: 1.5, ease: "easeOut" }}
                        />
                      </svg>

                      {/* Inner Text */}
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <motion.span
                          initial={{ opacity: 0, y: 5 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.5 }}
                          className="text-3xl font-heading font-extrabold text-zinc-900"
                        >
                          {Math.round(result.accuracy)}%
                        </motion.span>
                        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
                          Accuracy
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Stats & Message */}
                  <div className="flex-1 space-y-4 text-center md:text-left">
                    <div>
                      <h3 className="text-xl font-bold text-zinc-900">
                        {result.accuracy >= 90 ? "Outstanding!" :
                          result.accuracy >= 70 ? "Great Job!" :
                            result.accuracy >= 50 ? "Good Effort!" : "Keep Practicing"}
                      </h3>
                      <p className="text-sm text-zinc-500">
                        {result.accuracy >= 70
                          ? "You've mastered these concepts nicely."
                          : "Identify your weak spots to improve."}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-100 flex flex-col items-center md:items-start">
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span className="text-[10px] text-zinc-500 uppercase font-bold">Correct</span>
                        </div>
                        <span className="text-xl font-bold text-zinc-900">{result.score}/{result.total}</span>
                      </div>

                      <div className="bg-zinc-50 p-3 rounded-lg border border-zinc-100 flex flex-col items-center md:items-start">
                        <div className="flex items-center gap-2 mb-1">
                          <TrendingUp className="h-4 w-4 text-blue-500" />
                          <span className="text-[10px] text-zinc-500 uppercase font-bold">Readiness</span>
                        </div>
                        <span className="text-xl font-bold text-zinc-900">{Math.round(result.readiness)}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Weak Areas - Full width but compact */}
                <div className="w-full">
                  {result.weak_areas && result.weak_areas.length > 0 ? (
                    <div className="bg-red-50/50 border border-red-100 rounded-lg p-3">
                      <h4 className="text-xs font-bold text-red-600 mb-2 flex items-center gap-2">
                        <AlertCircle className="h-3 w-3" />
                        Focus Areas
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {result.weak_areas.slice(0, 5).map((topic: string, i: number) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-white border border-red-100 text-red-500 text-[10px] font-medium rounded-full"
                          >
                            {topic}
                          </span>
                        ))}
                        {result.weak_areas.length > 5 && (
                          <span className="px-2 py-0.5 text-zinc-400 text-[10px] font-medium">+{result.weak_areas.length - 5} more</span>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-green-50/50 border border-green-100 rounded-lg p-3 flex items-center justify-center gap-2 text-green-700 text-xs font-medium">
                      <Trophy className="h-3 w-3" />
                      No weak areas detected!
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-3 justify-end pt-2 border-t border-zinc-100">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="text-zinc-500 hover:text-zinc-900"
                  >
                    Close
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleFinish}
                    className="bg-primary text-white hover:bg-primary/90"
                  >
                    Continue Journey
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

"use client";

import { useState } from "react";

import { generateLessonAPI, generateParentReportAPI, generateStudyPlanAPI } from "./api";
import { LESSON_TOPICS, QUESTION_BANK, SAMPLE_PLAN, SUBJECTS } from "./constants";
import { PlaceholderPanel } from "./ShellComponents";

export function DashboardPanel({ learner, masteryData, onStartLesson, onStartDiag }) {
  const overallMastery = Math.round(Object.values(masteryData).reduce((a, v) => a + v, 0) / Object.values(masteryData).length);
  return (
    <PlaceholderPanel title={`🏠 Welcome, ${learner.nickname}!`} description="Phase 0 focuses on architecture cleanup. This dashboard stays intentionally simple while functionality is separated into modules.">
      <p style={{ marginBottom: 12 }}>Overall mastery: <strong>{overallMastery}%</strong></p>
      <div className="btn-row">
        <button className="btn-primary" onClick={onStartLesson}>Start lesson</button>
        <button className="btn-secondary" onClick={onStartDiag}>Open diagnostic</button>
      </div>
    </PlaceholderPanel>
  );
}

export function DiagnosticPanel({ learner, onComplete, onBack }) {
  const [subject, setSubject] = useState(null);
  const questions = subject ? (QUESTION_BANK[subject]?.[learner.grade] || QUESTION_BANK[subject]?.[3] || []) : [];
  return (
    <PlaceholderPanel title="🧪 Diagnostic Assessment" description="Phase 0 extracts diagnostic data and UI boundaries out of the single-file component.">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {SUBJECTS.map((s) => (
          <button key={s.code} className="btn-secondary" onClick={() => setSubject(s.code)}>{s.label}</button>
        ))}
      </div>
      <p style={{ marginBottom: 16, color: "var(--muted)" }}>Selected question set: {questions.length} items</p>
      <div className="btn-row">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <button className="btn-primary" disabled={!subject} onClick={() => onComplete(subject, 60)}>Use sample completion</button>
      </div>
    </PlaceholderPanel>
  );
}

export function LessonPanel({ learner, onComplete, onBack }) {
  const [subject, setSubject] = useState(null);
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [lessonTitle, setLessonTitle] = useState("");
  const [error, setError] = useState("");

  async function generate() {
    setLoading(true);
    setError("");
    try {
      const lesson = await generateLessonAPI({
        grade: learner.grade,
        subjectCode: subject,
        subjectLabel: SUBJECTS.find((s) => s.code === subject)?.label,
        topic,
        homeLanguage: learner.language,
      });
      setLessonTitle(lesson.title || topic);
    } catch (e) {
      setError(e.message || "Lesson generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PlaceholderPanel title="📖 Lessons" description="Phase 0 moves API logic and content configuration out of the monolithic component while preserving backend-only lesson generation.">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {SUBJECTS.map((s) => (
          <button key={s.code} className="btn-secondary" onClick={() => { setSubject(s.code); setTopic(""); }}>{s.label}</button>
        ))}
      </div>
      {subject && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
          {(LESSON_TOPICS[subject] || []).map((entry) => (
            <button key={entry} className="btn-secondary" onClick={() => setTopic(entry)}>{entry}</button>
          ))}
        </div>
      )}
      {lessonTitle && <p style={{ marginBottom: 12 }}>Generated lesson: <strong>{lessonTitle}</strong></p>}
      {error && <p style={{ marginBottom: 12, color: "var(--red)" }}>{error}</p>}
      <div className="btn-row">
        <button className="back-btn" onClick={onBack}>← Back</button>
        <button className="btn-primary" disabled={!subject || !topic || loading} onClick={generate}>{loading ? "Generating..." : "Generate lesson"}</button>
        <button className="btn-secondary" onClick={() => onComplete(35)}>Award sample XP</button>
      </div>
    </PlaceholderPanel>
  );
}

export function StudyPlanPanel({ learner }) {
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);

  async function generatePlan() {
    setLoading(true);
    try {
      const data = await generateStudyPlanAPI({ grade: learner.grade });
      setPlan(data);
    } catch {
      setPlan({ week_focus: "Fractions & Multiplication", days: SAMPLE_PLAN });
    } finally {
      setLoading(false);
    }
  }

  return (
    <PlaceholderPanel title="📅 Study Plan" description="Study plan logic now has its own surface area and uses shared API helpers.">
      <p style={{ marginBottom: 12 }}>Current focus: <strong>{plan?.week_focus || "Not generated yet"}</strong></p>
      <div className="btn-row">
        <button className="btn-primary" onClick={generatePlan} disabled={loading}>{loading ? "Generating..." : "Generate study plan"}</button>
      </div>
    </PlaceholderPanel>
  );
}

export function BadgesPanel() {
  return (
    <PlaceholderPanel title="🏆 Badges" description="Badge presentation is being separated from the application shell.">
      <p>Badge inventory remains available for the next extraction pass.</p>
    </PlaceholderPanel>
  );
}

export function ParentPortalPanel({ learner }) {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState("");

  async function generateReport() {
    setLoading(true);
    try {
      const report = await generateParentReportAPI({
        grade: learner.grade,
        streakDays: learner.streak || 1,
        totalXp: learner.xp || 0,
      });
      setSummary(report.summary || "Report generated.");
    } catch {
      setSummary("Parent reporting remains in phased hardening.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PlaceholderPanel title="👨‍👩‍👧 Parent Portal" description="Parent-facing workflows stay behind backend APIs while the frontend is decomposed.">
      <p style={{ marginBottom: 12 }}>{summary || "No report generated yet."}</p>
      <button className="btn-primary" onClick={generateReport} disabled={loading}>{loading ? "Generating..." : "Generate parent report"}</button>
    </PlaceholderPanel>
  );
}

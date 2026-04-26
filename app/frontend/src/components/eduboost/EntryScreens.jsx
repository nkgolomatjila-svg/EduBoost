"use client";

import React from "react";
import { AVATARS, GRADES } from "./constants";

export function Stars() {
  const seededValue = (index, multiplier, offset = 0) => {
    const raw = Math.sin(index * multiplier + offset) * 10000;
    return raw - Math.floor(raw);
  };

  const stars = Array.from({ length: 50 }, (_, i) => ({
    id: i,
    x: seededValue(i, 12.9898, 78.233) * 100,
    y: seededValue(i, 39.3468, 11.135) * 100,
    size: seededValue(i, 73.156, 7.77) * 2.5 + 0.5,
    dur: `${(seededValue(i, 31.4159, 3.14) * 3 + 2).toFixed(1)}s`,
    opacity: (seededValue(i, 27.1828, 4.669) * 0.4 + 0.1).toFixed(2),
    delay: `${(seededValue(i, 19.775, 2.22) * 4).toFixed(1)}s`,
  }));

  return <div className="stars-bg">{stars.map((s) => <div key={s.id} className="star" style={{ left: `${s.x}%`, top: `${s.y}%`, width: `${s.size}px`, height: `${s.size}px`, "--d": s.dur, "--o": s.opacity, animationDelay: s.delay }} />)}</div>;
}

export function Landing({ onStart, onParent }) {
  return <div className="screen landing"><Stars /><div style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 400 }}><div className="logo-ring">🦁</div><h1>EduBoost SA</h1><p className="tagline">AI-powered learning for South African learners Grade R to Grade 7</p><div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}><button className="btn-primary" onClick={onStart} style={{ width: "100%", maxWidth: 280 }}>🚀 Start Learning!</button><button className="btn-secondary" onClick={onParent} style={{ width: "100%", maxWidth: 280 }}>👨‍👩‍👧 Parent / Guardian Portal</button></div></div></div>;
}

export function Onboarding({ onComplete }) {
  const [step, setStep] = React.useState(0);
  const [grade, setGrade] = React.useState(null);
  const [avatar, setAvatar] = React.useState(null);
  const [nickname, setNickname] = React.useState("");
  const [language, setLanguage] = React.useState("English");
  const languages = ["English", "isiZulu", "Afrikaans", "isiXhosa", "Sesotho", "Setswana"];
  const canNext = [grade !== null, avatar !== null, nickname.trim().length >= 2, true];

  return <div className="screen" style={{ background: "var(--bg)" }}><Stars /><div className="onboarding" style={{ position: "relative", zIndex: 1 }}><div className="step-indicator">{Array.from({ length: 4 }, (_, i) => <div key={i} className={`step-dot ${i < step ? "done" : i === step ? "active" : ""}`} />)}</div>{step === 0 && <><h2 className="onboard-title">👋 Sawubona! Which grade are you in?</h2><p className="onboard-sub">Tap your grade to get started</p><div className="grade-grid">{GRADES.map((g) => <div key={g.id} className={`grade-card ${grade === g.id ? "selected" : ""}`} onClick={() => setGrade(g.id)}><span className="emoji">{g.emoji}</span><div className="grade-name">{g.label}</div><div className="grade-age">{g.age}</div></div>)}</div></>}{step === 1 && <><h2 className="onboard-title">🎨 Pick your avatar!</h2><p className="onboard-sub">This will be your learning buddy</p><div className="avatar-grid">{AVATARS.map((a, i) => <button key={i} className={`avatar-btn ${avatar === i ? "selected" : ""}`} onClick={() => setAvatar(i)}>{a}</button>)}</div></>}{step === 2 && <><h2 className="onboard-title">✏️ What should we call you?</h2><p className="onboard-sub">Use a nickname — no real names needed!</p><input className="name-input" placeholder="e.g. StarLearner, MathWiz..." value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={20} /><div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8 }}>{languages.map((lang) => <button key={lang} onClick={() => setLanguage(lang)} style={{ background: language === lang ? "rgba(255,215,0,0.1)" : "var(--surface)", border: `2px solid ${language === lang ? "var(--gold)" : "var(--border)"}`, borderRadius: 10, padding: "10px 6px", cursor: "pointer", color: "var(--text)", fontFamily: "Nunito", fontWeight: 700, fontSize: "0.82rem" }}>{lang}</button>)}</div></>}{step === 3 && <><h2 className="onboard-title">🔒 Safety First!</h2><div className="consent-form"><div className="popia-badge">🛡️ Guardian-validated consent still needs backend enforcement</div><p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: 16, lineHeight: 1.7 }}>This learner onboarding flow is still transitional. It explains intended safeguards, but it does not replace a real backend-enforced guardian consent workflow.</p></div></>}
  <div className="btn-row" style={{ marginTop: "auto", paddingTop: 24 }}>{step > 0 && <button className="back-btn" onClick={() => setStep((s) => s - 1)}>← Back</button>}<button className="btn-primary" style={{ flex: 1, opacity: canNext[step] ? 1 : 0.4 }} disabled={!canNext[step]} onClick={() => (step < 3 ? setStep((s) => s + 1) : onComplete({ grade, avatar, nickname, language }))}>{step === 3 ? "🎉 Let's Go!" : "Next →"}</button></div></div></div>;
}

export function ParentGateway({ onBack }) {
  return <div className="screen" style={{ background: "var(--bg)" }}><Stars /><div className="onboarding" style={{ position: "relative", zIndex: 1 }}><button className="back-btn" style={{ marginBottom: 24 }} onClick={onBack}>← Back</button><h2 className="onboard-title">👨‍👩‍👧 Parent / Guardian Portal</h2><div className="popia-badge">🛡️ Backend-enforced consent is required</div><div className="consent-form"><h3 style={{ fontFamily: "'Baloo 2',cursive", fontSize: "1.3rem", marginBottom: 12 }}>Parent access is not self-activated here</h3><p style={{ fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.7 }}>Use the API-backed parent and auth endpoints when wiring the real guardian experience.</p></div><button className="btn-secondary" style={{ marginTop: 24, width: "100%" }} onClick={onBack}>Return to learner app</button></div></div>;
}

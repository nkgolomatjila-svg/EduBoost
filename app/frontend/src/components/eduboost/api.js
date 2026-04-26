function uuidv4() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function getLearnerPseudonymId() {
  if (typeof window === "undefined") return uuidv4();
  let id = window.localStorage.getItem("eb_learner_pseudonym_id");
  if (!id) {
    id = uuidv4();
    window.localStorage.setItem("eb_learner_pseudonym_id", id);
  }
  return id;
}

async function callAPI(endpoint, body) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const res = await fetch(`${apiUrl}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail = `API error: ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail?.reason || err.detail?.error || err.detail || detail;
    } catch {
      // ignore JSON parsing errors
    }
    throw new Error(detail);
  }

  return res.json();
}

export async function generateLessonAPI({ grade, subjectCode, subjectLabel, topic, homeLanguage, masteryPrior }) {
  const data = await callAPI("/lessons/generate", {
    learner_id: getLearnerPseudonymId(),
    subject_code: subjectCode,
    subject_label: subjectLabel,
    topic,
    grade,
    home_language: homeLanguage || "English",
    learning_style_primary: "visual",
    mastery_prior: typeof masteryPrior === "number" ? masteryPrior : 0.5,
    has_gap: false,
  });
  return data.lesson;
}

export async function generateStudyPlanAPI({ grade, knowledgeGaps = [], subjectsMastery = {} }) {
  const data = await callAPI("/study-plans/generate", {
    learner_id: getLearnerPseudonymId(),
    grade,
    knowledge_gaps: knowledgeGaps,
    subjects_mastery: subjectsMastery,
  });
  return data.plan;
}

export async function generateParentReportAPI({ grade, streakDays, totalXp, subjectsMastery = {}, gaps = [] }) {
  const data = await callAPI("/parent/report/generate", {
    learner_id: getLearnerPseudonymId(),
    grade,
    streak_days: streakDays || 0,
    total_xp: totalXp || 0,
    subjects_mastery: subjectsMastery,
    gaps,
  });
  return data.report;
}

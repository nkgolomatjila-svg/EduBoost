"use client";

import { useState } from "react";

import { Landing, Onboarding, ParentGateway } from "./eduboost/EntryScreens";
import {
  BadgesPanel,
  DashboardPanel,
  DiagnosticPanel,
  LessonPanel,
  ParentPortalPanel,
  StudyPlanPanel,
} from "./eduboost/FeaturePanels";
import { BadgePopup, Sidebar } from "./eduboost/ShellComponents";

export default function EduBoostSA() {
  const [screen, setScreen] = useState("landing");
  const [learner, setLearner] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [masteryData, setMasteryData] = useState({
    MATH: 38,
    ENG: 62,
    LIFE: 75,
    NS: 55,
    SS: 48,
  });
  const [badge, setBadge] = useState(null);

  return (
    <>
      <div className="app">
        <div className="flag-bar" />
        {badge && <BadgePopup badge={badge} onDismiss={() => setBadge(null)} />}

        {screen === "landing" && (
          <Landing
            onStart={() => setScreen("onboarding")}
            onParent={() => setScreen("parent-gateway")}
          />
        )}

        {screen === "parent-gateway" && (
          <ParentGateway onBack={() => setScreen("landing")} />
        )}

        {screen === "onboarding" && (
          <Onboarding
            onComplete={(data) => {
              setLearner({ ...data, xp: 0, streak: 1 });
              setScreen("app");
              setActiveTab("dashboard");
            }}
          />
        )}

        {screen === "app" && learner && (
          <div className="main-layout">
            <Sidebar
              learner={learner}
              activeTab={activeTab}
              onTab={setActiveTab}
              onLogout={() => {
                setScreen("landing");
                setLearner(null);
              }}
            />
            <div className="main-content">
              {activeTab === "dashboard" && (
                <DashboardPanel
                  learner={learner}
                  masteryData={masteryData}
                  onStartLesson={() => setActiveTab("lesson")}
                  onStartDiag={() => setActiveTab("diagnostic")}
                />
              )}

              {activeTab === "diagnostic" && (
                <DiagnosticPanel
                  learner={learner}
                  onComplete={(subject, mastery) => {
                    setMasteryData((prev) => ({ ...prev, [subject]: mastery }));
                    setActiveTab("plan");
                  }}
                  onBack={() => setActiveTab("dashboard")}
                />
              )}

              {activeTab === "lesson" && (
                <LessonPanel
                  learner={learner}
                  onComplete={(xp) => {
                    setLearner((prev) => ({ ...prev, xp: (prev.xp || 0) + xp }));
                    setBadge("Lesson Complete! 🌟");
                    setActiveTab("dashboard");
                  }}
                  onBack={() => setActiveTab("dashboard")}
                />
              )}

              {activeTab === "plan" && <StudyPlanPanel learner={learner} />}
              {activeTab === "badges" && <BadgesPanel learner={learner} />}
              {activeTab === "parent" && <ParentPortalPanel learner={learner} />}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

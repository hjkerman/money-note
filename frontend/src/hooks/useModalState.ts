import { useState } from "react";
import { PrimaryTab, CurrentTab } from "../types";

export type StatsView = "card" | "cash";

export function useModalState() {
  const [activePrimaryTab, setActivePrimaryTab] = useState<PrimaryTab>("current");
  const [activeCurrentTab, setActiveCurrentTab] = useState<CurrentTab>("expenses");
  const [selectedHistoryMonth, setSelectedHistoryMonth] = useState("");
  const [showStats, setShowStats] = useState(false);
  const [statsView, setStatsView] = useState<StatsView>("card");
  const [showAuditLogs, setShowAuditLogs] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  return {
    activeCurrentTab,
    activePrimaryTab,
    selectedHistoryMonth,
    setActiveCurrentTab,
    setActivePrimaryTab,
    setSelectedHistoryMonth,
    setShowAuditLogs,
    setShowSettings,
    setShowStats,
    setStatsView,
    showAuditLogs,
    showSettings,
    showStats,
    statsView,
  };
}

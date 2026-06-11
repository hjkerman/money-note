import { useState } from "react";
import { PrimaryTab, CurrentTab } from "../types";
import { today } from "../utils";

export function useModalState() {
  const [activePrimaryTab, setActivePrimaryTab] = useState<PrimaryTab>("current");
  const [activeCurrentTab, setActiveCurrentTab] = useState<CurrentTab>("expenses");
  const [selectedHistoryMonth, setSelectedHistoryMonth] = useState(today.slice(0, 7));
  const [showStats, setShowStats] = useState(false);
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
    showAuditLogs,
    showSettings,
    showStats,
  };
}

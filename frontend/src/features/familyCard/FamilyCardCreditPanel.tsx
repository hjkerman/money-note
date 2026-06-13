import { JudgmentState, LedgerEntry, MonthlyPanel, Settings } from "../../api";
import { CreditUsagePanel } from "../../components/Insights";
import { parseSettingNumber, sumAmounts, sumPanelAmounts } from "../../utils";

export function FamilyCardCreditPanel({
  expenseEntries,
  judgment,
  panels,
  settings,
}: {
  expenseEntries: LedgerEntry[];
  judgment: JudgmentState | null;
  panels: MonthlyPanel[];
  settings: Settings;
}) {
  return (
    <CreditUsagePanel
      cardLimit={parseSettingNumber(settings, "card_limit", 5_800_000)}
      currentCardTotal={sumAmounts(expenseEntries)}
      family_cardTotal={sumPanelAmounts(panels.filter((panel) => panel.panel_type === "family_card"))}
      tone={judgment?.credit ?? null}
    />
  );
}

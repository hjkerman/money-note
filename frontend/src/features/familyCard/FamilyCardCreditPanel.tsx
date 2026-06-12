import { Installment, JudgmentState, LedgerEntry, MonthlyPanel, Settings } from "../../api";
import { CreditUsagePanel } from "../../components/Insights";
import { parseSettingNumber, sumAmounts, sumInstallmentMonthlyAmounts, sumPanelAmounts } from "../../utils";

export function FamilyCardCreditPanel({
  expenseEntries,
  installments,
  judgment,
  panels,
  settings,
}: {
  expenseEntries: LedgerEntry[];
  installments: Installment[];
  judgment: JudgmentState | null;
  panels: MonthlyPanel[];
  settings: Settings;
}) {
  return (
    <CreditUsagePanel
      cardLimit={parseSettingNumber(settings, "card_limit", 5_800_000)}
      currentCardTotal={sumAmounts(expenseEntries) + sumInstallmentMonthlyAmounts(installments)}
      family_cardTotal={sumPanelAmounts(panels.filter((panel) => panel.panel_type === "family_card"))}
      tone={judgment?.credit ?? null}
    />
  );
}

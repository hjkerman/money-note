import { JudgmentState, Settings, Summary } from "../../api";
import { CreditUsagePanel } from "../../components/Insights";
import { parseSettingNumber } from "../../utils";

export function FamilyCardCreditPanel({
  judgment,
  settings,
  summary,
}: {
  judgment: JudgmentState | null;
  settings: Settings;
  summary: Summary | null;
}) {
  return (
    <CreditUsagePanel
      cardLimit={parseSettingNumber(settings, "card_limit", 5_800_000)}
      currentCardTotal={summary?.card_total ?? 0}
      family_cardTotal={summary?.family_card_original_total ?? 0}
      tone={judgment?.credit ?? null}
    />
  );
}

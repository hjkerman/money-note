import { Dispatch, FormEvent, SetStateAction } from "react";
import { CardDiscountPolicy, CardPaymentRow, CardPaymentStatus, JudgmentState, Settings, Summary } from "../api";
import { CardPaymentPanel } from "./CardPaymentPanel";
import { parseSettingNumber, today } from "../utils";

type LateEntryForm = { date: string; usagePlace: string; usageItem: string; amount: string };

export function CardPaymentView({
  active,
  cardPayments,
  handleAutoAllocate,
  handleCardPaymentDiscountToggle,
  handleCardPaymentEventDelete,
  handleCardPaymentRowDelete,
  handleCardPaymentSubmit,
  handleDiscountPolicyChange,
  handleLateEntrySubmit,
  handleLiquidityResetAcknowledgement,
  handlePaymentSelection,
  handleTollDeferral,
  isBusy,
  judgment,
  lateEntryForm,
  paymentAllocations,
  paymentBudget,
  setLateEntryForm,
  setPaymentAllocations,
  setPaymentBudget,
  settings,
  summary,
}: {
  active: boolean;
  cardPayments: CardPaymentStatus | null;
  handleAutoAllocate: () => void;
  handleCardPaymentDiscountToggle: (row: CardPaymentRow, exclude: boolean) => void;
  handleCardPaymentEventDelete: (eventId: number) => void;
  handleCardPaymentRowDelete: (row: CardPaymentRow) => void;
  handleCardPaymentSubmit: () => void;
  handleDiscountPolicyChange: (scope: "owner" | "family", month: string, policy: CardDiscountPolicy) => void;
  handleLateEntrySubmit: (event: FormEvent) => Promise<void>;
  handleLiquidityResetAcknowledgement: () => void;
  handlePaymentSelection: (row: CardPaymentRow, selected: boolean) => void;
  handleTollDeferral: (row: CardPaymentRow, defer: boolean) => void;
  isBusy: boolean;
  judgment: JudgmentState | null;
  lateEntryForm: LateEntryForm;
  paymentAllocations: Record<string, string>;
  paymentBudget: string;
  setLateEntryForm: Dispatch<SetStateAction<LateEntryForm>>;
  setPaymentAllocations: Dispatch<SetStateAction<Record<string, string>>>;
  setPaymentBudget: Dispatch<SetStateAction<string>>;
  settings: Settings;
  summary: Summary | null;
}) {
  return (
    <section className={active ? "tab-panel active" : "tab-panel"}>
      <CardPaymentPanel
        status={cardPayments}
        fallbackLiquidity={parseSettingNumber(settings, "base_next_month_liquidity", 400_000)}
        availableLiquidity={summary?.liquidity_status ?? 0}
        onAcknowledgeLiquidityReset={() => handleLiquidityResetAcknowledgement()}
        allocations={paymentAllocations}
        setAllocations={setPaymentAllocations}
        paymentBudget={paymentBudget}
        setPaymentBudget={setPaymentBudget}
        onDiscountPolicyChange={(policy) =>
          handleDiscountPolicyChange("owner", cardPayments?.usage_month ?? today.slice(0, 7), policy)
        }
        onAutoAllocate={handleAutoAllocate}
        onDiscountToggle={(row, exclude) => handleCardPaymentDiscountToggle(row, exclude)}
        onSelect={handlePaymentSelection}
        onSubmit={() => handleCardPaymentSubmit()}
        onDeleteEvent={(eventId) => handleCardPaymentEventDelete(eventId)}
        onDeleteRow={(row) => handleCardPaymentRowDelete(row)}
        onTollDeferral={(row, defer) => handleTollDeferral(row, defer)}
        paymentTone={judgment?.payment ?? null}
        lateEntryForm={lateEntryForm}
        setLateEntryForm={setLateEntryForm}
        onLateEntrySubmit={handleLateEntrySubmit}
        isBusy={isBusy}
      />
    </section>
  );
}

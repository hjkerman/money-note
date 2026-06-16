import {
  CardDiscountPolicy,
  CashFlow,
  JudgmentState,
  LedgerEntry,
  MonthlyPanel,
  Settings,
  SpendingCategory,
} from "./api";
import { CurrentTab, PanelType, StatItem } from "./types";

export const panelMeta: Record<PanelType, { labelKey: string; fallback: string }> = {
  fixed: { labelKey: "panel_fixed_title", fallback: "현금성 고정지출" },
  frozen: { labelKey: "panel_frozen_title", fallback: "동결" },
  claim: { labelKey: "panel_claim_title", fallback: "청구" },
  family_card: { labelKey: "panel_family_card_title", fallback: "가족카드" },
};

export const today = new Date().toISOString().slice(0, 10);
export const DEFAULT_CARD_DISCOUNT_RATE = 0.012;
export const currentTabs: CurrentTab[] = ["expenses", "claim", "family_card"];
export const fallbackCategoryLabels: JudgmentState["category_labels"] = {
  essential: "안 썼으면 큰일 났을 돈",
  questionable: "꼭 써야 했을까...?",
  dignity: "최소한의 품위유지비",
  unclassified: "미분류",
};

export function panelLabel(labels: Record<string, string>, type: PanelType): string {
  const meta = panelMeta[type];
  return labels[meta.labelKey] ?? meta.fallback;
}

export function isAuthRequiredError(error: unknown): boolean {
  return error instanceof Error && error.message.includes("authentication required");
}

export function parseAmount(value: string): number | null {
  const normalized = value.replaceAll(",", "").trim();
  if (!normalized) return null;
  const amount = Number(normalized);
  return Number.isFinite(amount) && Number.isInteger(amount) ? amount : null;
}

export function formatIntegerSetting(value: string | undefined): string {
  if (!value) return "";
  const amount = Number(value);
  return Number.isFinite(amount) ? String(Math.round(amount)) : value;
}

export function focusFirstDataInput(form: HTMLFormElement): void {
  requestAnimationFrame(() => {
    const target = form.querySelector<HTMLInputElement>(
      'input:not([type="date"]):not([type="hidden"]):not(:disabled)',
    );
    target?.focus();
  });
}

export function formatUsageTitle(usagePlace: string, usageItem: string): string {
  if (usagePlace && usageItem) return `[${usagePlace}] ${usageItem}`;
  if (usagePlace) return `[${usagePlace}]`;
  return usageItem;
}

export function displayEntryTitle(entry: LedgerEntry): string {
  if (entry.title.startsWith("[이월]")) return entry.title;
  if (entry.usage_place || entry.usage_item) {
    return formatUsageTitle(entry.usage_place ?? "", entry.usage_item ?? "");
  }
  return entry.title;
}

export function categoryLabel(category: SpendingCategory | null, judgment?: JudgmentState | null): string {
  const key = category ?? "unclassified";
  return judgment?.category_labels[key] ?? fallbackCategoryLabels[key];
}

export function activeStatItems(
  entries: LedgerEntry[],
): StatItem[] {
  // 소비 통계는 회수 예정인 청구/가족카드를 빼고, 내가 실제로 사용한 원장 지출만 본다.
  return entries.map((entry) => ({
    amount_value: entry.amount_value,
    spending_category: entry.spending_category,
  }));
}

export function parseOptionalDay(value: string): number | null {
  const day = Number(value.trim());
  if (!Number.isInteger(day)) return null;
  if (day < 1 || day > 31) return null;
  return day;
}

export function nextSortOrder(rows: { sort_order: number }[]): number {
  return rows.reduce((max, row) => Math.max(max, row.sort_order), 0) + 1;
}

export function collectEntryMonths(entries: LedgerEntry[], fallbackMonth: string): string[] {
  const months = new Set(entries.map((entry) => entry.entry_date?.slice(0, 7)).filter(Boolean) as string[]);
  months.add(fallbackMonth);
  return [...months].sort((a, b) => b.localeCompare(a));
}

export function compareEntriesByDate(a: LedgerEntry, b: LedgerEntry): number {
  const dateCompare = (b.entry_date ?? "").localeCompare(a.entry_date ?? "");
  if (dateCompare !== 0) return dateCompare;
  return a.sort_order - b.sort_order || a.id - b.id;
}

export function detectCurrentMonth(entries: LedgerEntry[], fallbackMonth = today.slice(0, 7)): string {
  const dated = entries.find((entry) => entry.entry_date);
  return dated?.entry_date?.slice(0, 7) ?? fallbackMonth;
}

export function formatDateLabel(value: string): string | null {
  if (!value) return null;
  const [year, month, day] = value.split("-");
  return `${year}.${month}.${day}.`;
}

export function displayEntryDateLabel(entry: LedgerEntry): string {
  if (entry.entry_date) return formatDateLabel(entry.entry_date) ?? entry.entry_date;
  if (entry.entry_kind === "expense") return "날짜 없음";
  return entry.date_label ?? entry.group_label ?? "";
}

export function formatMonthLabel(value: string): string {
  const [year, month] = value.split("-");
  return `${year}년 ${Number(month)}월`;
}

export function previousMonthLastDay(value: string): string {
  const dateValue = new Date(`${value}T00:00:00`);
  dateValue.setDate(0);
  return [
    dateValue.getFullYear(),
    String(dateValue.getMonth() + 1).padStart(2, "0"),
    String(dateValue.getDate()).padStart(2, "0"),
  ].join("-");
}

export function previousMonthFirstDay(value: string): string {
  return previousMonthLastDay(value).slice(0, 8) + "01";
}

export function monthFirstDay(month: string): string {
  return `${month}-01`;
}

export function monthLastDay(month: string): string {
  const [year, monthValue] = month.split("-").map(Number);
  const lastDay = new Date(year, monthValue, 0).getDate();
  return `${month}-${String(lastDay).padStart(2, "0")}`;
}

export function sumAmounts(entries: LedgerEntry[]): number {
  return entries.reduce((total, entry) => total + (entry.amount_value ?? 0), 0);
}

export function defaultCardDiscount(amount: number | null | undefined): number {
  return Math.floor((amount ?? 0) * DEFAULT_CARD_DISCOUNT_RATE);
}

export const discountIneligibleWords = ["교통", "대중교통", "버스", "지하철", "통행", "통행료", "하이패스"];

export function discountIneligibleTitle(title: string | null | undefined): boolean {
  const text = (title ?? "").toLowerCase();
  return discountIneligibleWords.some((word) => text.includes(word.toLowerCase()));
}

export function effectiveEntryDiscount(
  entry: LedgerEntry,
  discounts?: Record<string, number> | null,
  policy: CardDiscountPolicy | null = null,
): number {
  if (!entry.payment_key || policy === "disabled" || discountIneligibleTitle(displayEntryTitle(entry))) return 0;
  if (discounts && Object.prototype.hasOwnProperty.call(discounts, entry.payment_key)) {
    return Math.max(0, discounts[entry.payment_key] ?? 0);
  }
  return defaultCardDiscount(entry.amount_value);
}

export function sumPanelAmounts(rows: MonthlyPanel[]): number {
  return rows.reduce((total, row) => total + (row.amount_value ?? 0), 0);
}

export function effectivePanelDiscount(row: MonthlyPanel, policy: CardDiscountPolicy | null = null): number {
  if (!["claim", "family_card"].includes(row.panel_type) || policy === "disabled" || discountIneligibleTitle(row.title)) return 0;
  if (row.discount_override) return Math.max(0, row.discount_amount ?? 0);
  return defaultCardDiscount(row.amount_value);
}

export function panelNetAmount(row: MonthlyPanel, policy: CardDiscountPolicy | null = null): number {
  return Math.max(0, (row.amount_value ?? 0) - effectivePanelDiscount(row, policy));
}

export function sumPanelNetAmounts(rows: MonthlyPanel[], policy: CardDiscountPolicy | null = null): number {
  return rows.reduce((total, row) => total + panelNetAmount(row, policy), 0);
}

export function sumCashFlows(rows: CashFlow[]): number {
  return rows.reduce((total, row) => total + row.amount_value, 0);
}

export function sumStatItems(rows: StatItem[]): number {
  return rows.reduce((total, row) => total + (row.amount_value ?? 0), 0);
}

export function sumPaymentAllocationInputs(values: Record<string, string>): number {
  return Object.values(values).reduce((total, value) => total + (parseAmount(value) ?? 0), 0);
}

export function daysBetween(from: string, to: string): number {
  const start = new Date(`${from}T00:00:00`).getTime();
  const end = new Date(`${to}T00:00:00`).getTime();
  return Math.round((end - start) / 86_400_000);
}

export function parseSettingNumber(settings: Settings, key: string, fallback: number): number {
  const parsed = Number(settings[key]);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function formatWon(value: number | null): string {
  return `${Math.round(value ?? 0).toLocaleString("ko-KR")}원`;
}

export function formatAuditTimestamp(value: string): string {
  const parsed = new Date(`${value.replace(" ", "T")}Z`);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("ko-KR", { hour12: false });
}

import { MonthlyPanel, SpendingCategory } from "./api";

export type PanelType = MonthlyPanel["panel_type"];
export type PrimaryTab = "current" | "payment" | "fixed" | "frozen" | "cash";
export type CurrentTab = "expenses" | "claim" | "family_card";
export type StatItem = {
  amount_value: number | null;
  spending_category: SpendingCategory | null;
};

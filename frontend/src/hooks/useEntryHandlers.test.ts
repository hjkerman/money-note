import { createElement, FormEvent, SetStateAction } from "react";
import { renderToString } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import { useEntryHandlers } from "./useEntryHandlers";

const api = vi.hoisted(() => ({ createEntry: vi.fn(), appendPlannedEntry: vi.fn() }));
vi.mock("../api", () => api);
vi.mock("../utils", async (original) => ({
  ...await original<typeof import("../utils")>(), focusFirstDataInput: vi.fn(),
}));
afterEach(() => vi.resetAllMocks());

function probe() {
  const expense = { date: "2026-11-05", usagePlace: "서점", usageItem: "책", spendingCategory: "", amount: "1000" };
  const planned = { dueDay: "5", usagePlace: "구독", usageItem: "요금", amount: "500" };
  let currentExpense = expense;
  let currentPlanned = planned;
  let handlers: ReturnType<typeof useEntryHandlers>;
  function Probe() {
    handlers = useEntryHandlers({
      entries: [], expenseForm: expense, plannedForm: planned,
      setExpenseForm: (action: SetStateAction<typeof expense>) => { currentExpense = typeof action === "function" ? action(currentExpense) : action; },
      setPlannedForm: (action: SetStateAction<typeof planned>) => { currentPlanned = typeof action === "function" ? action(currentPlanned) : action; },
      setStatus: vi.fn(),
      withRefresh: async (action) => { try { await action(); return true; } catch { return false; } },
    });
    return null;
  }
  renderToString(createElement(Probe));
  return {
    handlers: handlers!,
    edit: () => { currentExpense = { ...expense, usageItem: "새 draft" }; currentPlanned = { ...planned, amount: "999" }; },
    expense: () => currentExpense, planned: () => currentPlanned,
  };
}
const event = () => ({ preventDefault: vi.fn(), currentTarget: {} }) as unknown as FormEvent;

for (const kind of ["expense", "planned"] as const) {
  const request = () => kind === "expense" ? api.createEntry : api.appendPlannedEntry;
  const submit = (p: ReturnType<typeof probe>) => kind === "expense" ? p.handlers.handleExpenseSubmit(event()) : p.handlers.handlePlannedSubmit(event());
  it(`${kind}: delayed success preserves newer draft and blocks concurrent submission`, async () => {
    let finish!: (value: { book_section: string }) => void;
    request().mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const p = probe(); const first = submit(p);
    p.edit(); await submit(p);
    expect(request()).toHaveBeenCalledTimes(1);
    finish({ book_section: "current" }); await first;
    expect(p.expense().usageItem).toBe("새 draft");
    expect(p.planned().amount).toBe("999");
  });
  it(`${kind}: unchanged draft clears on success`, async () => {
    request().mockResolvedValue({ book_section: "current" });
    const p = probe(); await submit(p);
    expect(p[kind]().amount).toBe("");
  });
  it(`${kind}: failed request retains draft and permits explicit retry`, async () => {
    request().mockRejectedValueOnce(new Error("failed")).mockResolvedValueOnce({ book_section: "current" });
    const p = probe(); const original = p[kind](); await submit(p);
    expect(p[kind]()).toBe(original);
    await submit(p); expect(request()).toHaveBeenCalledTimes(2);
    expect(p[kind]().amount).toBe("");
  });
}

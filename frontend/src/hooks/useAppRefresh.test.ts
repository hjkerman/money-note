import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { expect, it, vi } from "vitest";
import { useAppRefresh } from "./useAppRefresh";

const snapshot = vi.hoisted(() => ({ loadLedgerSnapshot: vi.fn() }));
vi.mock("./useLedgerSnapshot", () => ({
  useLedgerSnapshot: () => ({ loadLedgerSnapshot: snapshot.loadLedgerSnapshot }),
}));

it("reports a failed mutation or failed follow-up refresh as incomplete", async () => {
  let refreshState: ReturnType<typeof useAppRefresh> | undefined;
  function Probe() {
    refreshState = useAppRefresh({
      setCashFlowForm: vi.fn(),
      setExpenseForm: vi.fn(),
      setLateEntryForm: vi.fn(),
      setPanelForm: vi.fn(),
    });
    return null;
  }
  renderToString(createElement(Probe));
  expect(await refreshState!.withRefresh(async () => { throw new Error("response lost"); })).toBe(false);
  expect(snapshot.loadLedgerSnapshot).not.toHaveBeenCalled();

  snapshot.loadLedgerSnapshot.mockRejectedValueOnce(new Error("fresh state unavailable"));
  expect(await refreshState!.withRefresh(async () => {})).toBe(false);
  expect(snapshot.loadLedgerSnapshot).toHaveBeenCalledTimes(1);
});

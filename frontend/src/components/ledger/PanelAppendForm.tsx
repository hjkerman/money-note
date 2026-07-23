import { FormEvent } from "react";

import { PanelType } from "../../types";

type PanelForm = {
  panel_type: PanelType;
  title: string;
  spentOn: string;
  amount: string;
  dueDay: string;
};

export function PanelAppendForm({
  isBusy,
  panelType,
  panelForm,
  setPanelForm,
  handlePanelSubmit,
}: {
  isBusy: boolean;
  panelType: PanelType;
  panelForm: PanelForm;
  setPanelForm: (value: PanelForm) => void;
  handlePanelSubmit: (event: FormEvent, panelType: PanelType) => Promise<void>;
}) {
  return (
    <form
      className={`panel-form panel-form-${panelType}`}
      onSubmit={(event) => void handlePanelSubmit(event, panelType)}
    >
      <input
        type="date"
        value={panelForm.spentOn}
        onChange={(event) =>
          setPanelForm({
            panel_type: panelType,
            title: panelForm.title,
            spentOn: event.target.value,
            amount: panelForm.amount,
            dueDay: panelForm.dueDay,
          })
        }
        className={panelType === "claim" || panelType === "family_card" ? "" : "hidden-input"}
        aria-hidden={panelType === "claim" || panelType === "family_card" ? undefined : true}
        tabIndex={panelType === "claim" || panelType === "family_card" ? undefined : -1}
      />
      <input
        value={panelForm.panel_type === panelType ? panelForm.title : ""}
        onChange={(event) =>
          setPanelForm({
            panel_type: panelType,
            title: event.target.value,
            spentOn: panelForm.spentOn,
            amount: panelForm.amount,
            dueDay: panelForm.dueDay,
          })
        }
        placeholder="세부내역"
      />
      <input
        type="number"
        min="0"
        step="1"
        value={panelForm.panel_type === panelType ? panelForm.amount : ""}
        onChange={(event) =>
          setPanelForm({
            panel_type: panelType,
            title: panelForm.title,
            spentOn: panelForm.spentOn,
            amount: event.target.value,
            dueDay: panelForm.dueDay,
          })
        }
        inputMode="numeric"
        placeholder="금액"
      />
      <button type="submit" disabled={isBusy}>
        추가
      </button>
    </form>
  );
}

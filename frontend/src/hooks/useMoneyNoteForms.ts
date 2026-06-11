import { useRef, useState } from "react";
import { PanelType } from "../types";
import { previousMonthLastDay, today } from "../utils";

export function useMoneyNoteForms() {
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [expenseForm, setExpenseForm] = useState({ date: today, usagePlace: "", usageItem: "", amount: "" });
  const [plannedForm, setPlannedForm] = useState({ dueDay: "", usagePlace: "", usageItem: "", amount: "" });
  const [cashFlowForm, setCashFlowForm] = useState({
    occurredOn: today,
    direction: "in",
    title: "",
    amount: "",
    isPrimaryIncome: false,
  });
  const [installmentForm, setInstallmentForm] = useState({
    title: "",
    principal: "",
    fee: "0",
    months: "",
  });
  const [panelForm, setPanelForm] = useState<{
    panel_type: PanelType;
    title: string;
    spentOn: string;
    amount: string;
    dueDay: string;
  }>({ panel_type: "fixed", title: "", spentOn: today, amount: "", dueDay: "" });
  const [passwordForm, setPasswordForm] = useState({ currentPassword: "", newPassword: "" });
  const [resetPassword, setResetPassword] = useState("");
  const [lateEntryForm, setLateEntryForm] = useState({
    date: previousMonthLastDay(today),
    usagePlace: "",
    usageItem: "",
    amount: "",
  });
  const csvBackupInputRef = useRef<HTMLInputElement | null>(null);

  return {
    cashFlowForm,
    csvBackupInputRef,
    expenseForm,
    installmentForm,
    lateEntryForm,
    loginForm,
    panelForm,
    passwordForm,
    plannedForm,
    resetPassword,
    setCashFlowForm,
    setExpenseForm,
    setInstallmentForm,
    setLateEntryForm,
    setLoginForm,
    setPanelForm,
    setPasswordForm,
    setPlannedForm,
    setResetPassword,
  };
}

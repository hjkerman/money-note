import { ReactNode } from "react";

export function AppShell({
  children,
  header,
  settings,
}: {
  children: ReactNode;
  header: ReactNode;
  settings?: ReactNode;
}) {
  return (
    <main className="app-shell">
      {header}
      {children}
      {settings}
    </main>
  );
}

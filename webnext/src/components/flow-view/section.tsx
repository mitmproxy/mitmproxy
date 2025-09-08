import type { PropsWithChildren } from "react";

export function Section(props: PropsWithChildren) {
  return <section {...props} />;
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-muted-foreground mb-2 text-lg font-semibold">
      {children}
    </h4>
  );
}

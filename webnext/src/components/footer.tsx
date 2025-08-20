import { ConnectionIndicator } from "@/components/connection-indicator";

export function Footer() {
  return (
    <div className="bg-muted/30 text-muted-foreground flex justify-end border-t px-4 py-1 text-xs">
      <ConnectionIndicator />
    </div>
  );
}

import { Circle } from "lucide-react";

export function Footer() {
  return (
    <div className="border-t px-4 py-1 bg-muted/30 text-xs text-muted-foreground flex justify-end">
      <div className="flex items-center gap-2">
        <Circle className="w-2 h-2 fill-green-500 text-green-500" />
        <span>Connected</span>
      </div>
    </div>
  );
}

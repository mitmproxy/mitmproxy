import { LuCircle } from "react-icons/lu";

export function Footer() {
  return (
    <div className="bg-muted/30 text-muted-foreground flex justify-end border-t px-4 py-1 text-xs">
      <div className="flex items-center gap-2">
        <LuCircle className="h-2 w-2 fill-green-500 text-green-500" />
        <span>Connected</span>
      </div>
    </div>
  );
}

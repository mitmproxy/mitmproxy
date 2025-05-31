import { LuPause, LuPlay, LuRotateCcw, LuSquare } from "react-icons/lu";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export function Header() {
  return (
    <div className="bg-muted/30 flex items-center justify-between border-b px-4 py-2">
      <div className="text-foreground text-lg font-bold">Mitmwebnext</div>

      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm">
            <LuPlay className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm">
            <LuPause className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm">
            <LuSquare className="h-4 w-4" />
          </Button>
          <Separator orientation="vertical" className="h-6" />
          <Button variant="ghost" size="sm">
            <LuRotateCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="flex items-center gap-2">
          <span>Command Palette</span>
          <kbd className="bg-muted text-muted-foreground flex h-5 items-center gap-1 rounded border px-1.5 text-[10px] font-medium">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>
      </div>
    </div>
  );
}

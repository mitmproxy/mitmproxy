import { ChevronDown, Globe, Monitor } from "lucide-react";

export function SideMenu() {
  return (
    <nav className="space-y-1">
      <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
        <Monitor className="w-4 h-4" />
        <span>Dashboard</span>
      </div>

      <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-md bg-accent text-accent-foreground font-medium">
        <Globe className="w-4 h-4" />
        <span>Proxy</span>
      </div>

      <div className="space-y-1">
        <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
          <ChevronDown className="w-4 h-4" />
          <span>Target</span>
        </div>
        <div className="ml-6 space-y-1">
          <div className="flex items-center gap-2 px-3 py-1 text-sm text-muted-foreground rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
            <span>Site map</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 text-sm text-muted-foreground rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
            <span>Scope</span>
          </div>
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
          <ChevronDown className="w-4 h-4" />
          <span>Tools</span>
        </div>
        <div className="ml-6 space-y-1">
          <div className="flex items-center gap-2 px-3 py-1 text-sm text-muted-foreground rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
            <span>Repeater</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 text-sm text-muted-foreground rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
            <span>Diff</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 text-sm text-muted-foreground rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer">
            <span>Addons</span>
          </div>
        </div>
      </div>
    </nav>
  );
}

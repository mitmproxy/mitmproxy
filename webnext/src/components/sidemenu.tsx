import { LuChevronDown, LuGlobe, LuMonitor } from "react-icons/lu";

export function SideMenu() {
  return (
    <nav className="space-y-1">
      <div className="hover:bg-accent hover:text-accent-foreground flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm">
        <LuMonitor className="h-4 w-4" />
        <span>Dashboard</span>
      </div>

      <div className="bg-accent text-accent-foreground flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium">
        <LuGlobe className="h-4 w-4" />
        <span>Proxy</span>
      </div>

      <div className="space-y-1">
        <div className="hover:bg-accent hover:text-accent-foreground flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm">
          <LuChevronDown className="h-4 w-4" />
          <span>Target</span>
        </div>
        <div className="ml-6 space-y-1">
          <div className="text-muted-foreground hover:bg-accent hover:text-accent-foreground flex cursor-pointer items-center gap-2 rounded-md px-3 py-1 text-sm">
            <span>Site map</span>
          </div>
          <div className="text-muted-foreground hover:bg-accent hover:text-accent-foreground flex cursor-pointer items-center gap-2 rounded-md px-3 py-1 text-sm">
            <span>Scope</span>
          </div>
        </div>
      </div>

      <div className="space-y-1">
        <div className="hover:bg-accent hover:text-accent-foreground flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm">
          <LuChevronDown className="h-4 w-4" />
          <span>Tools</span>
        </div>
        <div className="ml-6 space-y-1">
          <div className="text-muted-foreground hover:bg-accent hover:text-accent-foreground flex cursor-pointer items-center gap-2 rounded-md px-3 py-1 text-sm">
            <span>Repeater</span>
          </div>
          <div className="text-muted-foreground hover:bg-accent hover:text-accent-foreground flex cursor-pointer items-center gap-2 rounded-md px-3 py-1 text-sm">
            <span>Diff</span>
          </div>
          <div className="text-muted-foreground hover:bg-accent hover:text-accent-foreground flex cursor-pointer items-center gap-2 rounded-md px-3 py-1 text-sm">
            <span>Addons</span>
          </div>
        </div>
      </div>
    </nav>
  );
}

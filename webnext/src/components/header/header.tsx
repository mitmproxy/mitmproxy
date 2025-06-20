import { LuPlay, LuRotateCcw, LuSquare } from "react-icons/lu";
import { IoPlayForwardOutline } from "react-icons/io5";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme-toggle";
import { useEffect, useState } from "react";
import { FilterAutocomplete } from "./intercept-filter/autocomplete";
import { useFilterCommands } from "./intercept-filter/use-filter-commands";
import { FilterDescription } from "@/components/header/intercept-filter/description";
import { useAppDispatch } from "web/ducks";
import { isValidFilterSyntax } from "@/components/header/intercept-filter/utils";
import { update } from "web/ducks/options";
import { resumeAll } from "web/ducks/flows";

export function Header() {
  const [filter, setFilter] = useState("");
  const filterCommands = useFilterCommands();
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (filter && isValidFilterSyntax(filter)) {
      dispatch(update("intercept", filter));
    }
  }, [filter, dispatch]);

  return (
    <div className="bg-muted/30 border-b">
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex max-w-2xl flex-1 items-center gap-4">
          <FilterAutocomplete
            value={filter}
            commands={filterCommands}
            onChange={setFilter}
            placeholder="Intercept filter (type '~' for help)"
          />
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void dispatch(resumeAll())}
              >
                <IoPlayForwardOutline className="size-5" />
              </Button>
              <Button variant="ghost" size="sm">
                <LuPlay className="size-4" />
              </Button>
              {/*  <Button variant="ghost" size="sm">
              <LuPause className="size-4" />
            </Button> */}
              <Button variant="ghost" size="sm">
                <LuSquare className="size-4" />
              </Button>
              <Separator orientation="vertical" className="h-6" />
              <Button variant="ghost" size="sm">
                <LuRotateCcw className="size-4" />
              </Button>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button variant="ghost" size="sm" className="flex items-center gap-2">
            <span>Command Palette</span>
            <kbd className="bg-muted text-muted-foreground flex h-5 items-center gap-1 rounded border px-1.5 text-[10px] font-medium">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>
          <div className="text-foreground ml-10 text-lg font-bold">
            Mitmwebnext
          </div>
        </div>
      </div>

      {filter && <FilterDescription filter={filter} />}
    </div>
  );
}

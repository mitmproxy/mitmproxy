import {
  LuPause,
  LuPlay,
  LuRotateCcw,
  LuSettings,
  LuSquare,
} from "react-icons/lu";
import { IoPlayForwardOutline } from "react-icons/io5";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme-toggle";
import { useState } from "react";
import { FilterDescriptionBanner } from "@/components/filter/filter-description";
import { useAppDispatch, useAppSelector } from "web/ducks";
import { update } from "web/ducks/options";
import { resumeAll } from "web/ducks/flows";
import { DialogTrigger } from "@/components/ui/dialog";
import { FilterDialog } from "@/components/filter";
import { setFilter } from "web/ducks/ui/filter";
import { SearchInput } from "@/components/search";
import { OptionsDialog } from "@/components/options";

export function Header() {
  const [isInterceptFilterOpen, setIsInterceptFilterOpen] = useState(false);
  const interceptFilter = useAppSelector((state) => state.options.intercept);
  const searchFilter = useAppSelector((state) => state.ui.filter.search);
  const dispatch = useAppDispatch();

  const dispatchFilter = (type: "intercept" | "search", value: string) => {
    if (type === "intercept") {
      dispatch(update(type, value));
    } else if (type === "search") {
      dispatch(setFilter(value));
    }
  };

  return (
    <div className="bg-muted/30 border-b">
      <div className="flex items-center justify-between px-4 py-2">
        <div className="text-foreground text-lg font-bold">Mitmwebnext</div>
        <SearchInput
          value={searchFilter || ""}
          onChange={(value) => dispatchFilter("search", value)}
          placeholder="Search flows"
          className="w-xl pl-10"
          hideDescription
        />
        <div className="flex max-w-2xl flex-1 items-center gap-4">
          <FilterDialog
            open={isInterceptFilterOpen}
            onOpenChange={setIsInterceptFilterOpen}
            value={interceptFilter || ""}
            onApply={(value) => dispatchFilter("intercept", value)}
          >
            <DialogTrigger asChild>
              <Button variant="outline">
                <LuPause />
                Intercept filters
              </Button>
            </DialogTrigger>
          </FilterDialog>
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
        </div>
        <OptionsDialog>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm">
              <LuSettings />
              Settings
            </Button>
          </DialogTrigger>
        </OptionsDialog>
      </div>

      {(interceptFilter || searchFilter) && (
        <FilterDescriptionBanner
          interceptFilter={interceptFilter}
          searchFilter={searchFilter}
        />
      )}
    </div>
  );
}

import { FilterInput } from "./filter-input";
import { isValidFilterSyntax } from "./utils";
import { FilterBuilder } from "./filter-builder";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  type DialogProps,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@radix-ui/react-separator";
import { useEffect, useState, type PropsWithChildren } from "react";
import { LuCode, LuExternalLink, LuRotateCcw, LuZap } from "react-icons/lu";

export type FilterDialogProps = {
  onApply: (filter: string) => void;
  value: string;
} & PropsWithChildren<DialogProps>;

export function FilterDialog({
  value,
  children,
  onApply,
  ...props
}: FilterDialogProps) {
  const [mode, setMode] = useState<"easy" | "advanced">("easy");
  const [filter, setFilter] = useState(value);

  const syntaxValid = isValidFilterSyntax(filter);

  const applyFilter = () => {
    onApply(filter);
    props.onOpenChange?.(false);
  };

  const clearFilter = () => {
    setFilter("");
    onApply("");
  };

  const cancel = () => {
    setFilter(value); // reset to original value
    props.onOpenChange?.(false);
  };

  useEffect(() => {
    setFilter(value);
  }, [value]);

  return (
    <Dialog {...props}>
      {children}
      <DialogContent className="max-h-[90vh] max-w-6xl overflow-auto p-0">
        <DialogHeader className="px-6 pt-6 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="flex items-center gap-2">
                Filters
                <Badge variant="secondary" className="text-xs">
                  {mode === "easy" ? "Easy mode" : "Advanced mode"}
                </Badge>
              </DialogTitle>
              <DialogDescription className="mt-2">
                Filter expressions.
              </DialogDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <a
                href="https://docs.mitmproxy.org/stable/concepts/filters/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2"
              >
                <LuExternalLink className="size-4" />
                Documentation
              </a>
            </Button>
          </div>
        </DialogHeader>

        <Tabs
          value={mode}
          onValueChange={(value) => setMode(value as "easy" | "advanced")}
          className="min-h-[630px] px-6"
        >
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="easy" className="flex items-center gap-2">
              <LuZap className="size-4" />
              Easy mode
            </TabsTrigger>
            <TabsTrigger value="advanced" className="flex items-center gap-2">
              <LuCode className="size-4" />
              Advanced mode
            </TabsTrigger>
          </TabsList>

          <TabsContent value="easy" className="mt-6">
            <FilterBuilder value={filter} onChange={setFilter} />
          </TabsContent>

          <TabsContent value="advanced" className="mt-6">
            <FilterInput
              value={filter}
              onChange={setFilter}
              label="Enter filter expression:"
              placeholder="Intercept filter (type '~' for help)"
            />
          </TabsContent>
        </Tabs>

        <div className="px-6 pb-6">
          <Separator className="mb-4" />

          <div className="flex items-center justify-between">
            <div className="text-muted-foreground text-xs">
              <p>
                TIP: Use easy mode to build filters visually, then switch to
                advanced mode to fine-tune.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={clearFilter}
                className="mr-2"
              >
                <LuRotateCcw />
                Clear All
              </Button>
              <Button variant="outline" size="sm" onClick={cancel}>
                Cancel
              </Button>
              <Button size="sm" onClick={applyFilter} disabled={!syntaxValid}>
                Apply
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

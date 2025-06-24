"use client";

import { useState, useMemo, type PropsWithChildren } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { LuSettings, LuSearch, LuRotateCcw } from "react-icons/lu";
import { getSettingDisplayName } from "./utils";
import { OptionField } from "./options-field";
import { type Option, type OptionsState } from "web/ducks/_options_gen";
import { settingsCategories } from "./options-categories";
import { useAppDispatch, useAppSelector } from "web/ducks";
import { update as updateOptions } from "web/ducks/options";
import { DialogDescription } from "@radix-ui/react-dialog";
import { shallowEqual } from "react-redux";
import { MdMiscellaneousServices } from "react-icons/md";

export type OptionsDialogProps = PropsWithChildren;

export function OptionsDialog({ children }: OptionsDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const dispatch = useAppDispatch();
  const options = useAppSelector(
    (state) => Object.keys(state.options_meta),
    shallowEqual,
  ).sort() as Option[];

  const updateSetting = (key: keyof OptionsState, value: unknown) => {
    dispatch(updateOptions(key, value));
  };

  const resetToDefaults = () => {
    console.log("reset");
    // TODO: implement reset (requires changes to web)
  };

  const filteredCategories = useMemo(() => {
    let result = [...settingsCategories];

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();

      result = settingsCategories
        .map((category) => ({
          ...category,
          settings: category.options.filter(
            (setting) =>
              setting.toLowerCase().includes(query) ||
              getSettingDisplayName(setting).toLowerCase().includes(query),
          ),
        }))
        .filter((category) => category.settings.length > 0);
    }

    const unrecognizedOptions = options.filter(
      (option) =>
        !settingsCategories.some((category) =>
          category.options.includes(option),
        ),
    );
    if (unrecognizedOptions.length > 0) {
      result.push({
        id: "other",
        label: "Other",
        description: "Uncategorized options",
        icon: (
          <MdMiscellaneousServices className="text-gray-500 dark:text-gray-300" />
        ),
        options: unrecognizedOptions,
      });
    }

    return result;
  }, [options, searchQuery]);

  const totalMatchingSettings = filteredCategories.reduce(
    (total, category) => total + category.options.length,
    0,
  );

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {children}
      <DialogContent className="flex h-[90vh] max-w-6xl flex-col gap-0 p-0">
        <DialogHeader className="flex-shrink-0 p-6 pb-4">
          <DialogTitle className="flex items-center gap-2">
            <LuSettings className="size-5" />
            Options
          </DialogTitle>
          <DialogDescription className="hidden">
            Configure mitmproxy options.
          </DialogDescription>
          <div className="mt-4 flex items-center gap-4">
            <div className="relative flex-1">
              <LuSearch className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2 transform" />
              <Input
                placeholder="Search options..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            <Badge variant="secondary" className="w-[120px]">
              {totalMatchingSettings} option
              {totalMatchingSettings !== 1 ? "s" : ""} found
            </Badge>
          </div>
        </DialogHeader>

        <div className="flex h-full min-h-0 flex-1 overflow-hidden">
          {filteredCategories.length > 0 ? (
            <Tabs
              defaultValue={filteredCategories[0]?.id}
              className="flex h-full w-full flex-row"
            >
              <div className="bg-muted/30 w-64 border-t border-r">
                <div className="h-full overflow-y-auto">
                  <TabsList className="flex h-auto w-full flex-col space-y-1 bg-transparent p-2">
                    {filteredCategories.map((category) => (
                      <TabsTrigger
                        key={category.id}
                        value={category.id}
                        className="data-[state=active]:bg-accent data-[state=active]:text-accent-foreground w-full justify-start p-3 text-left"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-lg">{category.icon}</span>
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-medium">
                              {category.label}
                            </div>
                            <div className="text-muted-foreground text-xs">
                              {category.options.length} setting
                              {category.options.length !== 1 ? "s" : ""}
                            </div>
                          </div>
                        </div>
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </div>
              </div>

              <div className="flex-1">
                {filteredCategories.map((category) => (
                  <TabsContent
                    key={category.id}
                    value={category.id}
                    className="m-0 flex h-full flex-col"
                  >
                    <div className="flex-shrink-0 p-4 px-6">
                      <h3 className="flex items-center gap-2 text-lg font-semibold">
                        <span className="text-xl">{category.icon}</span>
                        {category.label}
                      </h3>
                      <p className="text-muted-foreground mt-1 text-sm">
                        {category.description}
                      </p>
                    </div>

                    <div className="flex-1 overflow-hidden px-6 pb-4">
                      <ScrollArea className="h-full">
                        <div className="space-y-4 pr-4">
                          {category.options.map((option) => (
                            <OptionField
                              key={option}
                              option={option}
                              onChange={(value) => updateSetting(option, value)}
                            />
                          ))}
                        </div>
                      </ScrollArea>
                    </div>
                  </TabsContent>
                ))}
              </div>
            </Tabs>
          ) : (
            <div className="flex h-full w-full items-center justify-center border-t">
              <div className="text-center">
                <LuSearch className="text-muted-foreground mx-auto mb-4 size-12" />
                <h3 className="mb-2 text-lg font-semibold">Nothing found</h3>
                <p className="text-muted-foreground text-sm">
                  Try adjusting your search query or{" "}
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="text-primary underline"
                  >
                    clear the search
                  </button>
                  .
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-shrink-0 justify-between border-t p-6">
          <Button variant="outline" onClick={resetToDefaults}>
            <LuRotateCcw />
            Reset to defaults
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setIsOpen(false);
            }}
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

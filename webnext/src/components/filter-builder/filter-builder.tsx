"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  LuTrash2,
  LuPlus,
  LuCheck,
  LuRotateCcw,
  LuArrowDown,
  LuCopy,
} from "react-icons/lu";
import type {
  FilterCondition,
  FilterGroup,
  FilterType,
  LogicalOperator,
} from "./types";
import { FILTER_DEFINITIONS, FILTER_CATEGORIES } from "./constants";
import { Checkbox } from "@/components/ui/checkbox";

export type FilterBuilderProps = {
  onCancel: () => void;
  onApply: (filter: string) => void;
};

export function FilterBuilder({ onApply, onCancel }: FilterBuilderProps) {
  const [groups, setGroups] = useState<FilterGroup[]>([
    {
      id: "1",
      conditions: [{ id: "1", type: "all" }],
      negate: false,
    },
  ]);

  const addGroup = () => {
    const newGroup: FilterGroup = {
      id: Date.now().toString(),
      conditions: [{ id: Date.now().toString(), type: "all" }],
      negate: false,
    };
    setGroups([...groups, newGroup]);
  };

  const removeGroup = (groupId: string) => {
    if (groups.length > 1) {
      setGroups(groups.filter((g) => g.id !== groupId));
    }
  };

  const addCondition = (groupId: string) => {
    setGroups(
      groups.map((group) =>
        group.id === groupId
          ? {
              ...group,
              conditions: [
                ...group.conditions,
                { id: Date.now().toString(), type: "all" },
              ],
            }
          : group,
      ),
    );
  };

  const removeCondition = (groupId: string, conditionId: string) => {
    setGroups(
      groups.map((group) =>
        group.id === groupId
          ? {
              ...group,
              conditions:
                group.conditions.length > 1
                  ? group.conditions.filter((c) => c.id !== conditionId)
                  : group.conditions,
            }
          : group,
      ),
    );
  };

  const updateCondition = (
    groupId: string,
    conditionId: string,
    updates: Partial<FilterCondition>,
  ) => {
    setGroups(
      groups.map((group) =>
        group.id === groupId
          ? {
              ...group,
              conditions: group.conditions.map((condition) =>
                condition.id === conditionId
                  ? { ...condition, ...updates }
                  : condition,
              ),
            }
          : group,
      ),
    );
  };

  const updateGroup = (groupId: string, updates: Partial<FilterGroup>) => {
    setGroups(
      groups.map((group) =>
        group.id === groupId ? { ...group, ...updates } : group,
      ),
    );
  };

  const generateFilterExpression = (): string => {
    const groupExpressions: string[] = [];

    groups.forEach((group, groupIndex) => {
      const conditionExpressions: string[] = [];

      group.conditions.forEach((condition, index) => {
        const def = FILTER_DEFINITIONS[condition.type];
        let expr = def.symbol;

        if (def.hasValue && condition.value) {
          const needsQuotes = /[\s|&!()~"]/.test(condition.value);
          const quotedValue = needsQuotes
            ? `"${condition.value.replace(/"/g, '\\"')}"`
            : condition.value;

          if (condition.type === "bareString") {
            expr = quotedValue;
          } else {
            expr += ` ${quotedValue}`;
          }
        }

        if (condition.negate) {
          expr = `!${expr}`;
        }

        conditionExpressions.push(expr);

        if (index < group.conditions.length - 1) {
          const operator = condition.nextOperator || "AND";
          const andOperator = " & ";
          const orOperator = " | ";
          conditionExpressions.push(
            operator === "AND" ? andOperator : orOperator,
          );
        }
      });

      let groupExpr = conditionExpressions.join("");

      if (group.conditions.length > 1 && (group.negate || groups.length > 1)) {
        groupExpr = `(${groupExpr})`;
      }

      if (group.negate) {
        groupExpr = `!${groupExpr}`;
      }

      groupExpressions.push(groupExpr);

      if (groupIndex < groups.length - 1) {
        const operator = group.nextOperator || "AND";
        const andOperator = " & ";
        const orOperator = " | ";
        groupExpressions.push(operator === "AND" ? andOperator : orOperator);
      }
    });

    return groupExpressions.join("");
  };

  const clearFilters = () => {
    setGroups([
      {
        id: "1",
        conditions: [{ id: "1", type: "all" }],
        negate: false,
      },
    ]);
  };

  return (
    <div className="space-y-6">
      <div className="space-y-6">
        {groups.map((group, groupIndex) => (
          <div key={group.id} className="space-y-4">
            <Card className="border-2 shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-3 text-lg">
                    <div className="bg-primary text-primary-foreground flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold">
                      {groupIndex + 1}
                    </div>
                    Filter Group {groupIndex + 1}
                  </CardTitle>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Checkbox
                        variant="destructive"
                        id={`negate-group-${group.id}`}
                        checked={group.negate || false}
                        onCheckedChange={(checked) => {
                          if (checked !== "indeterminate") {
                            updateGroup(group.id, {
                              negate: checked,
                            });
                          }
                        }}
                        className="accent-destructive size-4 rounded"
                      />
                      <Label
                        htmlFor={`negate-group-${group.id}`}
                        className="text-destructive text-sm font-medium"
                      >
                        NOT
                      </Label>
                    </div>
                    {groups.length > 1 && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => removeGroup(group.id)}
                        className="text-destructive hover:bg-destructive/10"
                      >
                        <LuTrash2 className="size-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  {group.conditions.map((condition, conditionIndex) => {
                    const filterDef = FILTER_DEFINITIONS[condition.type];

                    return (
                      <div key={condition.id} className="space-y-3">
                        <div className="bg-card flex items-center gap-3 rounded-lg border p-4 transition-shadow hover:shadow-sm">
                          <div className="flex items-center gap-2">
                            <Checkbox
                              variant="destructive"
                              id={`negate-${condition.id}`}
                              checked={condition.negate || false}
                              onCheckedChange={(checked) => {
                                if (checked !== "indeterminate") {
                                  updateCondition(group.id, condition.id, {
                                    negate: checked,
                                  });
                                }
                              }}
                              className="accent-destructive size-4 rounded"
                            />
                            <Label
                              htmlFor={`negate-${condition.id}`}
                              className="text-destructive min-w-[30px] text-xs font-medium"
                            >
                              NOT
                            </Label>
                          </div>

                          <Select
                            value={condition.type}
                            onValueChange={(value: FilterType) =>
                              updateCondition(group.id, condition.id, {
                                type: value,
                                value: "",
                              })
                            }
                          >
                            <SelectTrigger className="w-64">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="max-h-80">
                              {Object.entries(FILTER_CATEGORIES).map(
                                ([categoryName, categoryInfo]) => (
                                  <div key={categoryName}>
                                    <div className="text-muted-foreground bg-muted/50 px-2 py-1.5 text-xs font-semibold">
                                      <div className="flex items-center gap-2">
                                        <categoryInfo.icon className="h-3 w-3" />
                                        {categoryName}
                                      </div>
                                    </div>
                                    {categoryInfo.filters.map((filterKey) => {
                                      const def =
                                        FILTER_DEFINITIONS[
                                          filterKey as FilterType
                                        ];
                                      const FilterIcon = def.icon;
                                      return (
                                        <SelectItem
                                          key={filterKey}
                                          value={filterKey}
                                          className="pl-6"
                                        >
                                          <div className="flex items-center gap-2">
                                            <FilterIcon className="size-4" />
                                            <div>
                                              <div className="font-medium">
                                                {def.label}
                                              </div>
                                              <div className="text-muted-foreground text-xs">
                                                {def.description}
                                              </div>
                                            </div>
                                          </div>
                                        </SelectItem>
                                      );
                                    })}
                                  </div>
                                ),
                              )}
                            </SelectContent>
                          </Select>

                          {filterDef.hasValue && (
                            <Input
                              placeholder={`Enter ${filterDef.label.toLowerCase()}...`}
                              value={condition.value || ""}
                              onChange={(e) =>
                                updateCondition(group.id, condition.id, {
                                  value: e.target.value,
                                })
                              }
                              className="flex-1"
                            />
                          )}

                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              removeCondition(group.id, condition.id)
                            }
                            disabled={group.conditions.length === 1}
                            className="text-destructive hover:bg-destructive/10 ml-auto"
                          >
                            <LuTrash2 className="size-4" />
                          </Button>
                        </div>

                        {conditionIndex < group.conditions.length - 1 && (
                          <div className="flex justify-center">
                            <Select
                              value={condition.nextOperator || "AND"}
                              onValueChange={(value: LogicalOperator) =>
                                updateCondition(group.id, condition.id, {
                                  nextOperator: value,
                                })
                              }
                            >
                              <SelectTrigger className="bg-background h-8 w-20">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="AND">AND</SelectItem>
                                <SelectItem value="OR">OR</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  <Button
                    variant="outline"
                    onClick={() => addCondition(group.id)}
                    className="hover:bg-muted/50 w-full border-dashed"
                  >
                    <LuPlus className="mr-2 size-4" />
                    Add Condition
                  </Button>
                </div>
              </CardContent>
            </Card>

            {groupIndex < groups.length - 1 && (
              <div className="flex justify-center">
                <Select
                  value={group.nextOperator || "AND"}
                  onValueChange={(value: LogicalOperator) =>
                    updateGroup(group.id, { nextOperator: value })
                  }
                >
                  <SelectTrigger className="bg-background h-8 w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="AND">AND</SelectItem>
                    <SelectItem value="OR">OR</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        ))}
      </div>

      <Button
        variant="outline"
        onClick={addGroup}
        className="border-primary/30 hover:border-primary/50 hover:bg-primary/5 text-primary h-12 w-full border-dashed"
      >
        <LuPlus className="mr-2 h-5 w-5" />
        Add Filter Group
      </Button>

      <div className="text-muted-foreground flex items-center justify-center">
        <LuArrowDown className="size-10" />
      </div>

      <div className="space-y-4">
        <p className="font-semibold">Filter expression</p>

        <div className="bg-card relative rounded-lg border">
          <div className="p-4 pr-12 font-mono text-sm break-all">
            {generateFilterExpression() || "No filters configured"}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 right-2 size-8 p-0"
            onClick={() =>
              void navigator.clipboard.writeText(generateFilterExpression())
            }
          >
            <LuCopy className="size-4" />
          </Button>
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={clearFilters}>
          <LuRotateCcw className="mr-2 size-4" />
          Clear All
        </Button>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={() => onApply(generateFilterExpression())}>
            <LuCheck className="mr-2 size-4" />
            Apply Filter
          </Button>
        </div>
      </div>
    </div>
  );
}

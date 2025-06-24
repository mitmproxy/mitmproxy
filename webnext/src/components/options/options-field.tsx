"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LuX, LuPlus } from "react-icons/lu";
import { getSettingDisplayName } from "./utils";
import type { Option } from "web/ducks/_options_gen";
import { useAppSelector } from "web/ducks";

export type OptionFieldProps = {
  option: Option;
  onChange: (value: unknown) => void;
};

export function OptionField({ option, onChange }: OptionFieldProps) {
  const [newArrayItem, setNewArrayItem] = useState("");
  const meta = useAppSelector((state) => state.options_meta[option]);

  const fieldType = meta?.type || "string";
  const description = meta?.help;
  const choices = meta?.choices;
  const value = meta?.value;
  //const defaultValue = meta?.default;
  const displayName = getSettingDisplayName(option);

  const renderField = () => {
    if (choices) {
      return (
        <Select value={value as string} onValueChange={onChange}>
          <SelectTrigger className="max-w-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {choices.map((choice, i) => (
              <SelectItem key={i} value={choice?.toString() || ""}>
                {choice?.toString() || "None"}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }

    switch (fieldType) {
      case "sequence of str": {
        const arrayValue = value as string[];

        return (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {arrayValue.map((item, index) => (
                <Badge
                  // eslint-disable-next-line react-x/no-array-index-key
                  key={index}
                  variant="secondary"
                  className="flex items-center gap-1"
                >
                  {item}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="hover:bg-destructive hover:text-destructive-foreground size-4 p-0"
                    onClick={() => {
                      const newArray = arrayValue.filter((_, i) => i !== index);
                      onChange(newArray);
                    }}
                  >
                    <LuX className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                placeholder={`Add new ${displayName.toLowerCase()}`}
                value={newArrayItem}
                onChange={(e) => setNewArrayItem(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newArrayItem.trim()) {
                    onChange([...arrayValue, newArrayItem.trim()]);
                    setNewArrayItem("");
                  }
                }}
                className="max-w-xs"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  if (newArrayItem.trim()) {
                    onChange([...arrayValue, newArrayItem.trim()]);
                    setNewArrayItem("");
                  }
                }}
              >
                <LuPlus className="size-4" />
              </Button>
            </div>
          </div>
        );
      }

      case "bool":
        return (
          <div className="flex items-center space-x-2">
            <Switch
              id={option}
              checked={value as boolean}
              onCheckedChange={onChange}
            />
            <Label htmlFor={option} className="text-sm font-medium">
              {value ? "Enabled" : "Disabled"}
            </Label>
          </div>
        );

      case "int":
      case "optional int":
        return (
          <Input
            type="number"
            required={fieldType === "int"}
            placeholder="0"
            value={(value as number) ?? ""}
            onChange={(e) => onChange(Number.parseInt(e.target.value) || 0)}
            className="max-w-xs"
          />
        );

      case "str":
      case "optional str":
      default:
        return (
          <Input
            type="text"
            required={fieldType === "str"}
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value ?? "")}
            placeholder={`Enter ${displayName.toLowerCase()}`}
            className="max-w-md"
          />
        );
    }
  };

  return (
    <div className="bg-card space-y-2 rounded-lg border p-4">
      <div className="space-y-1">
        <Label htmlFor={option} className="text-sm font-medium">
          {displayName}
        </Label>
        <p className="text-muted-foreground text-xs">{description}</p>
      </div>
      {renderField()}
    </div>
  );
}

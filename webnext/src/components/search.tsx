import {
  FilterInput,
  type FilterInputProps,
} from "@/components/filter/filter-input";
import { isValidFilterSyntax } from "@/components/filter/utils";
import { useEffect, useState } from "react";
import { LuSearch } from "react-icons/lu";

export function SearchInput({
  onChange: onChangeProp,
  value: valueProp,
  ...props
}: FilterInputProps) {
  const [value, setValue] = useState(valueProp || "");

  const onChange = (value: string) => {
    setValue(value);

    if (isValidFilterSyntax(value) || value === "") {
      onChangeProp?.(value);
    }
  };

  // Sync local value state with valueProp changes.
  useEffect(() => {
    setValue(valueProp || "");
  }, [valueProp]);

  return (
    <div className="relative">
      <LuSearch className="text-muted-foreground absolute top-1/2 left-3 size-4 -translate-y-1/2 transform" />
      <FilterInput {...props} value={value} onChange={onChange} />
    </div>
  );
}

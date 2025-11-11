import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAppSelector } from "web/ducks/hooks";

export type ContentViewSelectorProps = {
  value: string;
  contentType?: string;
  onChange: (value: string) => void;
  className?: string;
};

export function ContentViewSelector({
  value,
  className,
  contentType,
  onChange,
}: ContentViewSelectorProps) {
  const contentViews = useAppSelector(
    (state) => state.backendState.contentViews || [],
  );

  return (
    <Select value={value.toLowerCase()} onValueChange={onChange}>
      <SelectTrigger className={className}>
        <SelectValue placeholder="Select a view" />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          <SelectLabel>Content views</SelectLabel>
          {contentViews.map((view) => (
            <SelectItem key={view} value={view.toLowerCase()}>
              {view.toLowerCase().replace("_", " ")}
              {view.toLowerCase() === "auto" && contentType
                ? ` (${contentType})`
                : ""}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}

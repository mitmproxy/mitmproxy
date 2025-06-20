import { parseFilterDescription } from "@/components/header/intercept-filter/utils";
import { Badge } from "@/components/ui/badge";
import { LuPause } from "react-icons/lu";

export type FilterDescriptionProps = {
  filter: string;
};

export function FilterDescription({ filter }: FilterDescriptionProps) {
  const description = parseFilterDescription(filter);
  const badges = description
    .split("and")
    .map((part) => part.trim())
    .filter(Boolean);

  return (
    <div className="bg-muted/50 text-muted-foreground border-t px-4 py-2">
      <div className="flex items-center gap-2 text-sm">
        <LuPause className="size-4" title="Intercepting" />
        <div className="flex flex-wrap items-center gap-2">
          {badges.map((badge, index) => (
            // eslint-disable-next-line react-x/no-array-index-key
            <Badge variant="outline" key={index}>
              {badge}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}

import { isValidFilterSyntax, parseFilterDescription } from "./utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  LuCircleAlert,
  LuCircleCheck,
  LuCopy,
  LuPause,
  LuSearch,
} from "react-icons/lu";

export type FilterDescriptionBannerProps = {
  interceptFilter?: string;
  searchFilter?: string;
  className?: string;
};

export function FilterDescriptionBanner({
  interceptFilter,
  searchFilter,
}: FilterDescriptionBannerProps) {
  return (
    <div className="bg-muted/50 text-muted-foreground space-y-2 border-t px-4 py-2">
      {searchFilter && (
        <div className="flex items-center gap-2 text-sm">
          <LuSearch className="size-4" title="Searching" />
          <div className="flex flex-wrap items-center gap-2">
            <FilterBadges filter={searchFilter} />
          </div>
        </div>
      )}
      {interceptFilter && (
        <div className="flex items-center gap-2 text-sm">
          <LuPause className="size-4" title="Intercepting" />
          <div className="flex flex-wrap items-center gap-2">
            <FilterBadges filter={interceptFilter} />
          </div>
        </div>
      )}
    </div>
  );
}

function FilterBadges({ filter }: { filter: string }) {
  const badges = parseFilterDescription(filter)
    .split("and")
    .map((part) => part.trim())
    .filter(Boolean);

  return badges.map((badge, index) => (
    // eslint-disable-next-line react-x/no-array-index-key
    <Badge variant="outline" key={index}>
      {badge}
    </Badge>
  ));
}

export type FilterDescriptionProps = {
  filter: string;
  className?: string;
};

export function FilterDescription({
  filter,
  className,
}: FilterDescriptionProps) {
  const description = parseFilterDescription(filter);
  const syntaxValid = isValidFilterSyntax(filter);

  return (
    <div className={cn("bg-muted/50 mt-6 rounded-lg p-4", className)}>
      <div className="mb-3 flex items-center gap-2">
        {syntaxValid ? (
          <LuCircleCheck className="h-4 w-4 text-green-600" />
        ) : (
          <LuCircleAlert className="h-4 w-4 text-red-600" />
        )}
        <span className="text-sm font-medium">
          {syntaxValid ? "Valid filter" : "Invalid syntax"}
        </span>
      </div>

      <div className="bg-muted relative rounded-md border p-3 pr-10 font-mono text-sm">
        <code className="text-foreground">{filter}</code>
        {filter && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 right-2 size-6 p-0"
            onClick={() => void navigator.clipboard.writeText(filter)}
          >
            <LuCopy className="size-3" />
          </Button>
        )}
      </div>

      {description && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">Will filter:</span>
          {description}
        </div>
      )}
    </div>
  );
}

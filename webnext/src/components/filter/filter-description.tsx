import { isValidFilterSyntax, parseFilterDescription } from "./utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LuCircleAlert, LuCircleCheck, LuCopy, LuPause } from "react-icons/lu";

export type FilterDescriptionProps = {
  filter: string;
  className?: string;
};

export function FilterDescriptionBanner({ filter }: FilterDescriptionProps) {
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

import { Badge } from "@/components/ui/badge";

export function MethodBadge({ method }: { method: string }) {
  return (
    <Badge
      variant="outline"
      className="px-2 py-1 font-mono text-xs font-medium uppercase"
    >
      {method}
    </Badge>
  );
}

import { cva, type VariantProps } from "class-variance-authority";
import { Badge } from "@/components/ui/badge";

export const statusVariants = cva("text-status-foreground", {
  variants: {
    status: {
      informational:
        "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300",
      successful:
        "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300",
      redirection:
        "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300",
      clientError:
        "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
      serverError:
        "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
    },
  },
  defaultVariants: {
    status: "serverError",
  },
});

export type StatusVariantProps = VariantProps<typeof statusVariants>;

export type StatusBadgeProps = { code: number };

export function StatusBadge({ code }: StatusBadgeProps) {
  return (
    <Badge className={statusVariants({ status: getStatusFromCode(code) })}>
      {code}
    </Badge>
  );
}

function getStatusFromCode(code: number): StatusVariantProps["status"] {
  if (code >= 100 && code < 200) return "informational";
  if (code >= 200 && code < 300) return "successful";
  if (code >= 300 && code < 400) return "redirection";
  if (code >= 400 && code < 500) return "clientError";
  if (code >= 500) return "serverError";
  return "serverError"; // fallback
}

import { cva, type VariantProps } from "class-variance-authority";
import { Badge } from "@/components/ui/badge";

export const statusVariants = cva("text-status-foreground", {
  variants: {
    status: {
      informational: "bg-status-informational",
      successful: "bg-status-successful",
      redirection: "bg-status-redirection",
      clientError: "bg-status-client-error",
      serverError: "bg-status-server-error",
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

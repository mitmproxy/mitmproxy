import { cva, type VariantProps } from "class-variance-authority";
import { Badge } from "@/components/ui/badge";

export const statusVariants = cva(null, {
  variants: {
    status: {
      informational: "bg-green-500",
      successful: "bg-green-800",
      redirection: "bg-blue-500",
      clientError: "bg-red-500",
      serverError: "bg-red-500",
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

import { cva, type VariantProps } from "class-variance-authority";
import type { PropsWithChildren } from "react";
import { LuCircle } from "react-icons/lu";

export const statusIndicatorVariants = cva("size-2", {
  variants: {
    variant: {
      success: "fill-success text-success",
      error: "fill-destructive text-destructive",
      warning: "fill-warning text-warning",
      info: "fill-info text-info",
    },
  },
});

export type StatusIndicatorProps = PropsWithChildren<
  VariantProps<typeof statusIndicatorVariants>
>;

export function StatusIndicator({ variant, children }: StatusIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      <LuCircle className={statusIndicatorVariants({ variant })} />
      {children && <span>{children}</span>}
    </div>
  );
}

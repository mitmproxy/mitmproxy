import type { OnKeyDownOptions } from "web/ducks/ui/keyboard";
import { useKeyboardNavigation } from "./use-keyboard-navigation";
import { useRef, type PropsWithChildren } from "react";

export function WithKeyboardNavigation({
  children,
  className,
  ...props
}: PropsWithChildren<{ className?: string } & OnKeyDownOptions>) {
  const ref = useRef<HTMLDivElement>(null);
  useKeyboardNavigation({ ref, ...props });

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

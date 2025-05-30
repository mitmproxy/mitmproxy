import type { Flow } from "web/flow";
import { TableRow } from "../ui/table";
import { cn } from "@/lib/utils";
import { useAppDispatch } from "web/ducks/hooks";
import { select, selectRange, selectToggle } from "web/ducks/flows";
import { memo, useCallback } from "react";

export type FlowRowProps = {
  flow: Flow;
  selected: boolean;
  highlighted: boolean;
} & React.ComponentProps<"tr">;

function FlowRow({
  flow,
  selected,
  highlighted: _,
  className,
  ...props
}: FlowRowProps) {
  const dispatch = useAppDispatch();
  const onClick = useCallback(
    (e: React.MouseEvent<HTMLTableRowElement>) => {
      // a bit of a hack to disable row selection for quickactions.
      let node = e.target as HTMLElement;
      while (node.parentNode) {
        if (node.classList.contains("col-quickactions")) return;
        node = node.parentNode as HTMLElement;
      }
      if (e.metaKey || e.ctrlKey) {
        dispatch(selectToggle(flow));
      } else if (e.shiftKey) {
        window.getSelection()?.empty();
        dispatch(selectRange(flow));
      } else {
        dispatch(select([flow]));
      }
    },
    [dispatch, flow],
  );

  // TODO: add higlighted, intercepted, etc. state colors

  return (
    <TableRow
      key={flow.id}
      {...props}
      className={cn(
        "cursor-pointer",
        selected ? "bg-accent/50" : "hover:bg-muted/50",
        className,
      )}
      onClick={onClick}
    />
  );
}

const FlowRowMemo = memo(FlowRow);

export { FlowRowMemo as FlowRow };

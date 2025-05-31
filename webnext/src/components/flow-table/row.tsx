import type { Flow } from "web/flow";
import { cn } from "@/lib/utils";
import { useAppDispatch, useAppSelector } from "web/ducks/hooks";
import {
  replay,
  resume,
  select,
  selectRange,
  selectToggle,
} from "web/ducks/flows";
import { memo, useCallback } from "react";
import { TableRow, type TableRowProps } from "@/components/ui/table";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuLabel,
  ContextMenuSeparator,
  ContextMenuShortcut,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { canReplay, mainPath } from "web/flow/utils";
import { LuClipboard, LuPlay, LuRotateCw } from "react-icons/lu";

export type FlowRowProps = {
  flow: Flow;
  selected: boolean;
  highlighted: boolean;
} & TableRowProps;

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
  const index = useAppSelector((state) => state.flows._listIndex.get(flow.id));

  // TODO: add higlighted, intercepted, etc. state colors

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
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
      </ContextMenuTrigger>
      <ContextMenuContent className="w-52">
        <ContextMenuLabel>Flow {(index ?? 0) + 1}</ContextMenuLabel>
        {/* Quick actions. */}
        {canReplay(flow) && (
          <ContextMenuItem onClick={() => void dispatch(replay([flow]))}>
            <LuRotateCw />
            Replay <ContextMenuShortcut>r</ContextMenuShortcut>
          </ContextMenuItem>
        )}
        {flow.intercepted && (
          <ContextMenuItem onClick={() => void dispatch(resume([flow]))}>
            <LuPlay />
            Resume
          </ContextMenuItem>
        )}
        <ContextMenuSeparator />

        {/* Actions that are only available to selected flow(s). */}
        {selected && (
          <>
            <ContextMenuItem
              onClick={() => void navigator.clipboard.writeText(mainPath(flow))}
            >
              <LuClipboard /> Copy {flow.type === "http" ? "URL" : "Path"}
            </ContextMenuItem>
          </>
        )}
      </ContextMenuContent>
    </ContextMenu>
  );
}

const FlowRowMemo = memo(FlowRow);

export { FlowRowMemo as FlowRow };

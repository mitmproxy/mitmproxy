import type { PropsWithChildren } from "react";
import { TableCell } from "../ui/table";
import { useAppDispatch, useAppSelector } from "web/ducks/hooks";
import type { Flow } from "web/flow";
import {
  canReplay,
  endTime,
  getMethod,
  getTotalSize,
  getVersion,
  mainPath,
  startTime,
} from "web/flow/utils";
import { Badge } from "../ui/badge";
import { formatSize, formatTimeDelta, formatTimeStamp } from "web/utils";
import { cn } from "@/lib/utils";
import { StatusBadge } from "../status-badge";
import { Button } from "../ui/button";
import * as flowActions from "web/ducks/flows";

type FlowColumnProps = {
  flow: Flow;
} & React.ComponentProps<"td">;

interface FlowColumn {
  (props: FlowColumnProps): JSX.Element;
  headerName: string;
  size?: number;
}

export const tls: FlowColumn = ({ flow, ...props }) => {
  const isTLS = flow.client_conn.tls_established;

  return (
    <Cell
      {...props}
      className={cn("border-l-4", { "border-l-green-500": isTLS })}
    />
  );
};
tls.headerName = "";
tls.size = 5;

export const index: FlowColumn = ({ flow, ...props }) => {
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const index = useAppSelector((state) => state.flows._listIndex.get(flow.id)!);

  return <Cell {...props}>{index + 1}</Cell>;
};
index.headerName = "#";

export const icon: FlowColumn = ({ flow: _, ...props }) => {
  // TODO: implement icons
  return <Cell {...props}>icon</Cell>;
};
icon.headerName = "";
icon.size = 20;

export const path: FlowColumn = ({ flow, ...props }) => {
  // TODO: implement flow.error
  // TODO: implement flow.marked

  return (
    <Cell
      className={cn("truncate", {
        "bg-red-500": flow.error,
      })}
      {...props}
    >
      {mainPath(flow)}
    </Cell>
  );
};
path.headerName = "Path";
path.size = 100;

export const method: FlowColumn = ({ flow, ...props }) => {
  return (
    <Cell {...props}>
      <Badge variant="outline" className="h-4 px-1 text-xs">
        {getMethod(flow)}
      </Badge>
    </Cell>
  );
};
method.headerName = "Method";
method.size = 50;

export const version: FlowColumn = ({ flow, ...props }) => {
  return <Cell {...props}>{getVersion(flow)}</Cell>;
};
version.headerName = "Version";

export const status: FlowColumn = ({ flow, ...props }) => {
  if (flow.type === "dns" && flow.response) {
    return (
      <Cell {...props}>
        <Badge>{flow.response.response_code}</Badge>
      </Cell>
    );
  }

  if (flow.type === "http" && flow.response) {
    return (
      <Cell {...props}>
        <StatusBadge code={flow.response.status_code} />
      </Cell>
    );
  }

  return <Cell {...props}></Cell>;
};
status.headerName = "Status";
status.size = 50;

export const size: FlowColumn = ({ flow, ...props }) => {
  return <Cell {...props}>{formatSize(getTotalSize(flow))}</Cell>;
};
size.headerName = "Size";
size.size = 80;

export const time: FlowColumn = ({ flow, ...props }) => {
  const start = startTime(flow);
  const end = endTime(flow);

  return (
    <Cell {...props}>
      {start && end ? formatTimeDelta(1000 * (end - start)) : "..."}
    </Cell>
  );
};
time.headerName = "Time";
time.size = 80;

export const timestamp: FlowColumn = ({ flow, ...props }) => {
  const time = startTime(flow);

  return <Cell {...props}>{time ? formatTimeStamp(time) : "..."}</Cell>;
};
timestamp.headerName = "Timestamp";
timestamp.size = 150;

export const quickactions: FlowColumn = ({ flow, ...props }) => {
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const dispatch = useAppDispatch();

  if (flow.intercepted) {
    return (
      <Cell {...props}>
        <Button
          size="sm"
          onClick={() => void dispatch(flowActions.resume([flow]))}
        >
          Resume
        </Button>
      </Cell>
    );
  }

  if (canReplay(flow)) {
    return (
      <Cell {...props}>
        <Button
          size="sm"
          onClick={() => void dispatch(flowActions.replay([flow]))}
        >
          Replay
        </Button>
      </Cell>
    );
  }

  return <Cell {...props} />;
};
quickactions.headerName = "Actions";

export const comment: FlowColumn = ({ flow, ...props }) => {
  const text = flow.comment;

  return <Cell {...props}>{text}</Cell>;
};
comment.headerName = "Comment";

export function getColumnStyle(column: FlowColumn): React.CSSProperties {
  return {
    maxWidth: column.size ? `${column.size}px` : undefined,
    //minWidth: column.size ? `${column.size}px` : undefined,
  };
}

function Cell({
  children,
  className,
  ...props
}: PropsWithChildren<{ className?: string }> & React.ComponentProps<"td">) {
  return (
    <TableCell
      {...props}
      className={cn("border-r px-2 py-1 text-xs", className)}
    >
      {children}
    </TableCell>
  );
}

import { Circle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { Badge } from "./ui/badge";

export type MockFlow = {
  id: number;
  url: string;
  origin: string;
  method: string;
  status: string;
  code: number;
  time: string;
  duration: string;
  requestSize: string;
  host: string;
  path: string;
};

export type FlowTableProps = {
  flows: MockFlow[];
  selectedRequest: MockFlow;
  setSelectedRequest: Dispatch<SetStateAction<MockFlow>>;
};

export function FlowTable({
  selectedRequest,
  flows,
  setSelectedRequest,
}: FlowTableProps) {
  const [columnWidths, setColumnWidths] = useState({
    id: 60,
    host: 250,
    path: 400,
    method: 100,
    status: 100,
    code: 80,
    time: 120,
    duration: 100,
    requestSize: 100,
  });

  const [resizing, setResizing] = useState<string | null>(null);
  const resizeStartX = useRef<number>(0);
  const resizeStartWidth = useRef<number>(0);

  const handleResizeMove = (e: MouseEvent) => {
    if (!resizing) return;

    const diff = e.clientX - resizeStartX.current;
    const newWidth = Math.max(50, resizeStartWidth.current + diff);

    setColumnWidths((prev) => ({
      ...prev,
      [resizing]: newWidth,
    }));
  };

  const handleResizeEnd = () => {
    setResizing(null);
    document.removeEventListener("mousemove", handleResizeMove);
    document.removeEventListener("mouseup", handleResizeEnd);
  };

  useEffect(() => {
    return () => {
      document.removeEventListener("mousemove", handleResizeMove);
      document.removeEventListener("mouseup", handleResizeEnd);
    };
  }, []);

  const handleResizeStart = (e: React.MouseEvent, column: string) => {
    e.preventDefault();
    setResizing(column);
    resizeStartX.current = e.clientX;
    resizeStartWidth.current =
      columnWidths[column as keyof typeof columnWidths];

    document.addEventListener("mousemove", handleResizeMove);
    document.addEventListener("mouseup", handleResizeEnd);
  };

  return (
    <Table className="text-xs">
      <TableHeader className="sticky top-0 bg-muted/50 z-10">
        <TableRow className="text-xs">
          <TableHead
            className="text-xs py-1 px-2 border-r relative"
            style={{ width: `${columnWidths.id}px` }}
          >
            #
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "id")}
            />
          </TableHead>
          <TableHead
            className="text-xs py-1 px-2 border-r relative"
            style={{ width: `${columnWidths.host}px` }}
          >
            Host
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "host")}
            />
          </TableHead>
          <TableHead
            className="text-xs py-1 px-2 border-r relative"
            style={{ width: `${columnWidths.path}px` }}
          >
            Path
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "path")}
            />
          </TableHead>
          <TableHead
            className="text-xs py-1 px-2 border-r relative"
            style={{ width: `${columnWidths.method}px` }}
          >
            Method
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "method")}
            />
          </TableHead>
          <TableHead
            className="text-xs py-1 px-2 border-r relative"
            style={{ width: `${columnWidths.status}px` }}
          >
            Status
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "status")}
            />
          </TableHead>
          <TableHead
            className="text-xs py-1 px-2 border-r relative"
            style={{ width: `${columnWidths.code}px` }}
          >
            Code
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "code")}
            />
          </TableHead>
          <TableHead
            className="text-xs py-1 px-2 border-r relative"
            style={{ width: `${columnWidths.time}px` }}
          >
            Time
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "time")}
            />
          </TableHead>
          <TableHead
            className="text-xs py-1 px-2 border-r relative"
            style={{ width: `${columnWidths.duration}px` }}
          >
            Duration
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "duration")}
            />
          </TableHead>
          <TableHead
            className="text-xs py-1 px-2 relative"
            style={{ width: `${columnWidths.requestSize}px` }}
          >
            Size
            <div
              className="absolute top-0 right-0 h-full w-2 cursor-col-resize hover:bg-primary hover:opacity-50"
              onMouseDown={(e) => handleResizeStart(e, "requestSize")}
            />
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {flows.map((flow) => (
          <TableRow
            key={flow.id}
            className={`cursor-pointer ${
              selectedRequest.id === flow.id
                ? "bg-accent/50"
                : "hover:bg-muted/50"
            }`}
            onClick={() => setSelectedRequest(flow)}
          >
            <TableCell
              className="text-xs py-1 px-2 border-r"
              style={{ width: `${columnWidths.id}px` }}
            >
              <div className="flex items-center gap-1">
                <Circle className="w-2 h-2 fill-green-500 text-green-500" />
                {flow.id}
              </div>
            </TableCell>
            <TableCell
              className="text-xs py-1 px-2 border-r font-mono text-blue-600 dark:text-blue-400"
              style={{ width: `${columnWidths.host}px` }}
            >
              <div className="truncate">{flow.host}</div>
            </TableCell>
            <TableCell
              className="text-xs py-1 px-2 border-r font-mono text-blue-600 dark:text-blue-400"
              style={{ width: `${columnWidths.path}px` }}
            >
              <div className="truncate">{flow.path}</div>
            </TableCell>
            <TableCell
              className="text-xs py-1 px-2 border-r"
              style={{ width: `${columnWidths.method}px` }}
            >
              <Badge variant="outline" className="text-xs h-4 px-1">
                {flow.method}
              </Badge>
            </TableCell>
            <TableCell
              className="text-xs py-1 px-2 border-r"
              style={{ width: `${columnWidths.status}px` }}
            >
              <div className="truncate">{flow.status}</div>
            </TableCell>
            <TableCell
              className="text-xs py-1 px-2 border-r text-green-600 dark:text-green-400"
              style={{ width: `${columnWidths.code}px` }}
            >
              {flow.code}
            </TableCell>
            <TableCell
              className="text-xs py-1 px-2 border-r font-mono"
              style={{ width: `${columnWidths.time}px` }}
            >
              {flow.time}
            </TableCell>
            <TableCell
              className="text-xs py-1 px-2 border-r"
              style={{ width: `${columnWidths.duration}px` }}
            >
              {flow.duration}
            </TableCell>
            <TableCell
              className="text-xs py-1 px-2"
              style={{ width: `${columnWidths.requestSize}px` }}
            >
              {flow.requestSize}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

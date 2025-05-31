import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export type KeyValuePair = [name: string, value: string];
export type KeyValuePairs = KeyValuePair[];

export type KvpTableProps = {
  pairs: KeyValuePairs;
} & React.ComponentProps<"table">;

/**
 * Key-Value Pair Table Component.
 */
export function KvpTable({ pairs, ...props }: KvpTableProps) {
  return (
    <Table {...props}>
      <TableHeader>
        <TableRow>
          <TableHead className="w-32 min-w-[8rem]">Key</TableHead>
          <TableHead className="min-w-0">Value</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {pairs.map(([key, value], index) => (
          // eslint-disable-next-line react-x/no-array-index-key
          <TableRow key={index}>
            <TableCell className="text-muted-foreground align-top text-xs font-medium whitespace-nowrap">
              {key}
            </TableCell>
            <TableCell className="w-full max-w-0 min-w-0 font-mono text-xs break-words whitespace-normal">
              {value}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

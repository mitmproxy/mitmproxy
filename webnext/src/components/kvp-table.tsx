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
  if (pairs.length === 0) {
    return <span className="text-muted-foreground text-xs">No data</span>;
  }

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
            <TableCell variant="muted">{key}</TableCell>
            <TableCell type="responsive">{value}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

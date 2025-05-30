import { useAppSelector } from "web/ducks/hooks";
import * as columns from "./flow-columns";

export function useDisplayColumns() {
  const displayColumnNames = useAppSelector(
    (state) => state.options.web_columns,
  );
  const displayColumns = displayColumnNames
    // eslint-disable-next-line @typescript-eslint/no-unsafe-return, @typescript-eslint/no-explicit-any
    .map((x) => (columns as any)[x])
    .filter((x) => x)
    .concat(columns.quickactions);
  // eslint-disable-next-line @typescript-eslint/no-unsafe-return
  return displayColumns;
}

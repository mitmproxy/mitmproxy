import type { FilterCommand } from "./types";
import { parseFilterCommands } from "./utils";
import { useEffect, useState } from "react";
import { fetchApi } from "web/utils";

export function useFilterCommands() {
  const [commands, setCommands] = useState<FilterCommand[]>([]);

  useEffect(() => {
    void fetchFilterHelp()
      .then((data) => {
        const parsedCommands = parseFilterCommands(data);
        setCommands(parsedCommands);
      })
      .catch(console.error);
  }, []);

  return commands;
}

export type FilterHelpResponse = { commands: string[][] };

async function fetchFilterHelp() {
  // TODO: this should be moved to redux (see similar todo in mitmweb as well)
  const response = await fetchApi("/filter-help");
  if (!response.ok) {
    throw new Error("Failed to fetch filter help");
  }
  const data = await response.json();
  return data as FilterHelpResponse;
}

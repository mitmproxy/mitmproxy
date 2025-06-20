import type { FilterHelpResponse } from "./use-filter-commands";
import type { FilterCommand } from "./types";
import Filter from "web/filt/filt";

export function isValidFilterSyntax(input: string): boolean {
  try {
    Filter.parse(input);
    return true;
  } catch {
    return false;
  }
}

export function parseFilterDescription(input: string): string {
  try {
    const parsed = Filter.parse(input);
    return (parsed as { desc: string }).desc;
  } catch (err) {
    return String(err);
  }
}

/**
 * Converts the raw filter command data from the API into a structured format.
 */
export function parseFilterCommands(data: {
  commands: FilterHelpResponse["commands"];
}): FilterCommand[] {
  return data.commands.map(([filter, description]) => {
    const requiresValue = filter.includes("regex") || filter.includes("int");
    const valueType = filter.includes("regex")
      ? "regex"
      : filter.includes("int")
        ? "int"
        : undefined;

    // Categorize filters
    let category = "Other";
    if (
      filter.startsWith("~b") ||
      filter.includes("body") ||
      filter.includes("Body")
    ) {
      category = "Content";
    } else if (
      filter.startsWith("~h") ||
      filter.startsWith("~t") ||
      filter.startsWith("~c") ||
      filter.startsWith("~m") ||
      filter.startsWith("~u") ||
      filter.startsWith("~d")
    ) {
      category = "HTTP";
    } else if (
      filter.startsWith("~http") ||
      filter.startsWith("~tcp") ||
      filter.startsWith("~udp") ||
      filter.startsWith("~dns") ||
      filter.startsWith("~websocket")
    ) {
      category = "Protocol";
    } else if (
      filter.startsWith("~q") ||
      filter.startsWith("~s") ||
      filter.startsWith("~e") ||
      filter.startsWith("~marked") ||
      filter.startsWith("~replay")
    ) {
      category = "State";
    } else if (filter.startsWith("~src") || filter.startsWith("~dst")) {
      category = "Network";
    } else if (
      filter.startsWith("~comment") ||
      filter.startsWith("~meta") ||
      filter.startsWith("~marker")
    ) {
      category = "Metadata";
    } else if (filter === "~a" || filter === "~all") {
      category = "Special";
    } else if (
      filter === "!" ||
      filter === "&" ||
      filter === "|" ||
      filter === "(...)"
    ) {
      category = "Logical";
    } else {
      category = "Other";
    }

    return {
      filter: filter.split(" ")[0], // Remove type info like "regex" or "int".
      description,
      category,
      requiresValue,
      valueType,
    };
  });
}

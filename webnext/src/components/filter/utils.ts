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

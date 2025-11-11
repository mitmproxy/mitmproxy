import type { Option } from "web/ducks/_options_gen";

export function getSettingDisplayName(setting: Option): string {
  return setting
    .split("_")
    .map((word, index) =>
      // Uppercase the first letter of the first word, lowercase the rest.
      index === 0
        ? word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        : word.toLowerCase(),
    )
    .join(" ");
}

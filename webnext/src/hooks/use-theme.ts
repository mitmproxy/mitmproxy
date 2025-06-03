import { useDarkMode } from "usehooks-ts";

export function useTheme() {
  const theme = useDarkMode({
    localStorageKey: "darkMode",
    defaultValue: window.matchMedia("(prefers-color-scheme: dark)").matches,
  });

  return theme;
}

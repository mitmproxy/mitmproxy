import { useDarkMode } from "@/hooks/use-dark-mode";

export function useTheme() {
  const theme = useDarkMode({
    localStorageKey: "darkMode",
    defaultValue: window.matchMedia("(prefers-color-scheme: dark)").matches,
    initializeWithValue: true,
  });

  return theme;
}

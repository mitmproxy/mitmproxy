import { Sun, Moon } from "lucide-react";
import { useEffect } from "react";
import { useDarkMode } from "usehooks-ts";

export function ThemeToggle() {
  const { isDarkMode, toggle: toggleDarkMode } = useDarkMode({
    localStorageKey: "darkMode",
    defaultValue: window.matchMedia("(prefers-color-scheme: dark)").matches,
  });

  const toggleTheme = () => {
    toggleDarkMode();

    if (isDarkMode) {
      document.documentElement.classList.remove("dark");
    } else {
      document.documentElement.classList.add("dark");
    }
  };

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
    }
  }, [isDarkMode]);

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent hover:text-accent-foreground cursor-pointer w-full"
    >
      {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      <span>{isDarkMode ? "Light Mode" : "Dark Mode"}</span>
    </button>
  );
}

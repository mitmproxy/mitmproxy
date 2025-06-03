import { LuSun, LuMoon } from "react-icons/lu";
import { useEffect } from "react";
import { useTheme } from "@/hooks/use-theme";

export function ThemeToggle() {
  const { isDarkMode, toggle: toggleDarkMode } = useTheme();

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
      type="button"
      onClick={toggleTheme}
      className="hover:bg-accent hover:text-accent-foreground flex w-full cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm"
    >
      {!isDarkMode ? (
        <LuSun className="h-4 w-4" />
      ) : (
        <LuMoon className="h-4 w-4" />
      )}
      <span>{!isDarkMode ? "Light Mode" : "Dark Mode"}</span>
    </button>
  );
}

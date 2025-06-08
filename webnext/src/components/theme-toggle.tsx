import { LuSun, LuMoon } from "react-icons/lu";
import { VscWand } from "react-icons/vsc";
import { useTheme } from "@/components/theme-provider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <button
      type="button"
      onClick={toggle}
      className="hover:bg-accent hover:text-accent-foreground flex w-full cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm"
    >
      {theme === "system" && <VscWand className="size-4" />}
      {theme === "dark" && <LuMoon className="size-4" />}
      {theme === "light" && <LuSun className="size-4" />}
      <span>
        {theme === "dark" && "Dark theme"}
        {theme === "light" && "Light theme"}
        {theme === "system" && "System theme"}
      </span>
    </button>
  );
}

import { LuSun, LuMoon } from "react-icons/lu";
import { VscWand } from "react-icons/vsc";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <Button variant="ghost" size="sm" onClick={toggle}>
      <span>
        {theme === "dark" && "Dark theme"}
        {theme === "light" && "Light theme"}
        {theme === "system" && "System theme"}
      </span>
      {theme === "system" && <VscWand className="h-4 w-4" />}
      {theme === "dark" && <LuMoon className="h-4 w-4" />}
      {theme === "light" && <LuSun className="h-4 w-4" />}
    </Button>
  );
}

import { useEffect } from "react";
import { useResolvedTheme } from "./useTheme";

/**
 * Applies the resolved `web_theme` to the document by setting `data-theme`
 * on the root element. Renders nothing.
 */
export default function ThemeManager() {
    const resolved = useResolvedTheme();

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", resolved);
    }, [resolved]);

    return null;
}

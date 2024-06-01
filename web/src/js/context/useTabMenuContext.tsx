import React, { createContext, useContext, useState } from "react";
import StartMenu from "../components/Header/StartMenu";

export interface Menu {
    (): JSX.Element;
    title: string;
}

// Define the shape of the context value
interface TabMenuContextType {
    ActiveMenu: Menu;
    setActiveMenu: React.Dispatch<React.SetStateAction<Menu>>;
}

// Create a context for tab menus
const TabMenuContext = createContext<TabMenuContextType | undefined>(undefined);

// Custom hook to access the tab menu context
export function useTabMenuContext() {
    const context = useContext(TabMenuContext);
    if (!context) {
        throw new Error(
            "useTabMenuContext must be used within a TabMenuProvider"
        );
    }
    return context;
}

// Provider component for tab menus
export function TabMenuProvider({ children }) {
    // State to track the active menu, initialized with StartMenu
    const [ActiveMenu, setActiveMenu] = useState<Menu>(() => StartMenu);

    // Provide the active menu and setter function to children components
    return (
        <TabMenuContext.Provider value={{ ActiveMenu, setActiveMenu }}>
            {children}
        </TabMenuContext.Provider>
    );
}

import React, { createContext, useContext, useState } from "react";
import StartMenu from "../components/Header/StartMenu";

export interface Menu {
    (): JSX.Element;
    title: string;
}

interface TabMenuContextType {
    ActiveMenu: Menu;
    setActiveMenu: React.Dispatch<React.SetStateAction<Menu>>;
}

const TabMenuContext = createContext<TabMenuContextType | undefined>(undefined);

export function useTabMenuContext() {
    const context = useContext(TabMenuContext);
    if (!context) {
        throw new Error(
            "useTabMenuContext must be used within a TabMenuProvider"
        );
    }
    return context;
}

export function TabMenuProvider({ children }) {
    const [ActiveMenu, setActiveMenu] = useState<Menu>(() => StartMenu);

    return (
        <TabMenuContext.Provider value={{ ActiveMenu, setActiveMenu }}>
            {children}
        </TabMenuContext.Provider>
    );
}

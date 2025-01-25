import * as React from "react";
import * as eventLogActions from "../../ducks/eventLog";
import * as commandBarActions from "../../ducks/commandBar";
import { useAppDispatch, useAppSelector } from "../../ducks";
import * as optionsActions from "../../ducks/options";

type MenuToggleProps = {
    value: boolean;
    onChange: (e: React.ChangeEvent) => void;
    children: React.ReactNode;
};

export function MenuToggle({ value, onChange, children }: MenuToggleProps) {
    return (
        <div className="menu-entry">
            <label>
                <input type="checkbox" checked={value} onChange={onChange} />
                {children}
            </label>
        </div>
    );
}

type OptionsToggleProps = {
    name: optionsActions.Option;
    children: React.ReactNode;
};

export function OptionsToggle({ name, children }: OptionsToggleProps) {
    const dispatch = useAppDispatch();
    const value = useAppSelector((state) => state.options[name]);

    return (
        <MenuToggle
            value={!!value}
            onChange={() => dispatch(optionsActions.update(name, !value))}
        >
            {children}
        </MenuToggle>
    );
}

export function EventlogToggle() {
    const dispatch = useAppDispatch();
    const visible = useAppSelector((state) => state.eventLog.visible);

    return (
        <MenuToggle
            value={visible}
            onChange={() => dispatch(eventLogActions.toggleVisibility())}
        >
            Display Event Log
        </MenuToggle>
    );
}

export function CommandBarToggle() {
    const dispatch = useAppDispatch();
    const visible = useAppSelector((state) => state.commandBar.visible);

    return (
        <MenuToggle
            value={visible}
            onChange={() => dispatch(commandBarActions.toggleVisibility())}
        >
            Display Command Bar
        </MenuToggle>
    );
}

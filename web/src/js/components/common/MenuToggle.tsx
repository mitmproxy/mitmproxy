import * as React from "react";
import { useDispatch } from "react-redux";
import * as eventLogActions from "../../ducks/eventLog";
import * as commandBarActions from "../../ducks/commandBar";
import { useAppDispatch, useAppSelector } from "../../ducks";
import * as optionsActions from "../../ducks/options";
import { ModeType } from "../Modes/Mode";
import { update as updateOptions } from "../../ducks/options";

type MenuToggleProps = {
    value: boolean;
    onChange: (e: React.ChangeEvent) => void;
    children: React.ReactNode;
    className: string;
};

export function MenuToggle({
    value,
    onChange,
    children,
    className,
}: MenuToggleProps) {
    return (
        <div className={className}>
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
    const dispatch = useAppDispatch(),
        value = useAppSelector((state) => state.options[name]);

    return (
        <MenuToggle
            value={!!value}
            onChange={() => dispatch(optionsActions.update(name, !value))}
            className="menu-entry"
        >
            {children}
        </MenuToggle>
    );
}

export function EventlogToggle() {
    const dispatch = useDispatch(),
        visible = useAppSelector((state) => state.eventLog.visible);

    return (
        <MenuToggle
            value={visible}
            onChange={() => dispatch(eventLogActions.toggleVisibility())}
            className="menu-entry"
        >
            Display Event Log
        </MenuToggle>
    );
}

export function CommandBarToggle() {
    const dispatch = useDispatch(),
        visible = useAppSelector((state) => state.commandBar.visible);

    return (
        <MenuToggle
            value={visible}
            onChange={() => dispatch(commandBarActions.toggleVisibility())}
            className="menu-entry"
        >
            Display Command Bar
        </MenuToggle>
    );
}

export function ModeToggle({
    children,
    modeType,
}: {
    children: React.ReactNode;
    modeType: ModeType;
}) {
    const dispatch = useDispatch();
    const modes = useAppSelector((state) => state.options.mode);
    const value = useAppSelector((state) =>
        state.options.mode.includes(modeType)
    );

    const handleToggleMode = () => {
        if (value) {
            const updatedModes = modes.filter((m) => !m.includes(modeType));
            dispatch(updateOptions("mode", updatedModes));
        } else {
            const updatedModes = modes.concat(modeType);
            dispatch(updateOptions("mode", updatedModes));
        }
    };

    return (
        <MenuToggle
            value={value}
            onChange={handleToggleMode}
            className="mode-entry"
        >
            {children}
        </MenuToggle>
    );
}
import React, {ChangeEvent} from "react"
import {useDispatch} from "react-redux"
import {toggleVisibility} from "../../ducks/eventLog"
import {useAppDispatch, useAppSelector} from "../../ducks";
import * as optionsActions from "../../ducks/options";


type MenuToggleProps = {
    value: boolean
    onChange: (e: ChangeEvent) => void
    children: React.ReactNode
}

export function MenuToggle({value, onChange, children}: MenuToggleProps) {
    return (
        <div className="menu-entry">
            <label>
                <input type="checkbox"
                       checked={value}
                       onChange={onChange}/>
                {children}
            </label>
        </div>
    )
}

type OptionsToggleProps = {
    name: optionsActions.Option,
    children: React.ReactNode
}

export function OptionsToggle({name, children}: OptionsToggleProps) {
    const dispatch = useAppDispatch(),
        value = useAppSelector(state => state.options[name]);

    return (
        <MenuToggle
            value={!!value}
            onChange={() => dispatch(optionsActions.update(name, !value))}
        >
            {children}
        </MenuToggle>
    )
}


export function EventlogToggle() {
    const dispatch = useDispatch(),
        visible = useAppSelector(state => state.eventLog.visible);

    return (
        <MenuToggle
            value={visible}
            onChange={() => dispatch(toggleVisibility())}
        >
            Display Event Log
        </MenuToggle>
    )
}

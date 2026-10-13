/* eslint-disable react/prop-types */
import type { ComponentProps } from "react";
import React from "react";
import type { Option } from "../../ducks/options";
import { update as updateOptions } from "../../ducks/options";
import classnames from "classnames";
import { useAppDispatch, useAppSelector } from "../../ducks";

const stopPropagation = (e: React.KeyboardEvent<HTMLElement>) => {
    if (e.key !== "Escape") {
        e.stopPropagation();
    }
};

interface OptionProps<S>
    extends Omit<
        ComponentProps<"input"> &
            ComponentProps<"select"> &
            ComponentProps<"textarea">,
        "value" | "onChange"
    > {
    value: S;
    onChange: (value: S) => any;
}

function BooleanOption({ value, onChange, ...props }: OptionProps<boolean>) {
    return (
        <div className="checkbox">
            <label>
                <input
                    type="checkbox"
                    checked={value}
                    onChange={(e) => onChange(e.target.checked)}
                    {...props}
                />
                Enable
            </label>
        </div>
    );
}

interface DraftInputProps
    extends Omit<ComponentProps<"input">, "value" | "onChange"> {
    value: string;
    onCommit: (value: string) => void;
}

// Keep what the user is typing in local state and only commit it on blur or Enter.
// Sending every keystroke to the backend makes options act on half-typed values,
// e.g. save_stream_file creating an empty file for every prefix of the path.
function DraftInput({ value, onCommit, onKeyDown, ...props }: DraftInputProps) {
    const [draft, setDraft] = React.useState(value);
    React.useEffect(() => setDraft(value), [value]);

    const commit = () => {
        if (draft !== value) {
            onCommit(draft);
        }
    };

    return (
        <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
                if (e.key === "Enter") {
                    commit();
                }
                onKeyDown?.(e);
            }}
            {...props}
        />
    );
}

function StringOption({ value, onChange, ...props }: OptionProps<string>) {
    return (
        <DraftInput
            type="text"
            value={value || ""}
            onCommit={onChange}
            {...props}
        />
    );
}

function Optional(Component) {
    return function OptionalWrapper({ onChange, ...props }) {
        return (
            <Component onChange={(x) => onChange(x ? x : null)} {...props} />
        );
    };
}

function NumberOption({ value, onChange, ...props }: OptionProps<number>) {
    return (
        <DraftInput
            type="number"
            value={String(value ?? "")}
            onCommit={(v) => onChange(parseInt(v))}
            {...props}
        />
    );
}

function FloatOption({ value, onChange, ...props }: OptionProps<number>) {
    return (
        <DraftInput
            type="number"
            step="any"
            value={String(value ?? "")}
            onCommit={(v) => onChange(parseFloat(v))}
            {...props}
        />
    );
}

interface ChoiceOptionProps extends OptionProps<string> {
    choices: string[];
}

export function ChoicesOption({
    value,
    onChange,
    choices,
    ...props
}: ChoiceOptionProps) {
    return (
        <select
            onChange={(e) => onChange(e.target.value)}
            value={value}
            {...props}
        >
            {choices.map((choice) => (
                <option key={choice} value={choice}>
                    {choice}
                </option>
            ))}
        </select>
    );
}

function StringSequenceOption({
    value,
    onChange,
    ...props
}: OptionProps<string[]>) {
    const [textAreaValue, setTextAreaValue] = React.useState(value.join("\n"));
    const height = Math.max(textAreaValue.split("\n").length, 1);

    const handleBlur = () => {
        //we send to the backend only the strings that are not empty
        const newValue = textAreaValue
            .split("\n")
            .map((line) => line.trim())
            .filter((line) => line !== "");
        if (newValue.join("\n") !== value.join("\n")) {
            onChange(newValue);
        }
    };

    return (
        <textarea
            rows={height}
            value={textAreaValue}
            onChange={(e) => setTextAreaValue(e.target.value)}
            onBlur={handleBlur}
            {...props}
        />
    );
}

export const Options = {
    bool: BooleanOption,
    str: StringOption,
    int: NumberOption,
    float: FloatOption,
    "optional str": Optional(StringOption),
    "optional int": Optional(NumberOption),
    "sequence of str": StringSequenceOption,
};

function PureOption({ choices, type, value, onChange, name, error }) {
    let Opt;
    const props: Partial<OptionProps<any> & ChoiceOptionProps> = {
        onChange,
        value,
    };
    if (choices) {
        Opt = ChoicesOption;
        props.choices = choices;
    } else {
        Opt = Options[type];
        if (!Opt) throw `unknown option type ${type}`;
    }
    if (Opt !== BooleanOption) {
        props.className = "input";
    }

    return (
        <div className={classnames({ "has-error": error })}>
            <Opt name={name} onKeyDown={stopPropagation} {...props} />
        </div>
    );
}

export default function OptionInput({ name }: { name: Option }) {
    const dispatch = useAppDispatch();
    const choices = useAppSelector(
        (state) => state.options_meta[name]?.choices,
    );
    const type = useAppSelector((state) => state.options_meta[name]?.type);
    const value = useAppSelector((state) => {
        const editState = state.ui.optionsEditor[name];
        return editState ? editState.value : state.options_meta[name]?.value;
    });
    const error = useAppSelector(
        (state) => state.ui.optionsEditor[name]?.error,
    );

    return (
        <PureOption
            name={name}
            choices={choices}
            type={type}
            value={value}
            error={error}
            onChange={(value) => dispatch(updateOptions(name, value))}
        />
    );
}

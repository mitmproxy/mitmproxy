import React, { Component } from "react";
import classnames from "classnames";
import { fetchApi } from "../../utils";
import Icon, { type IconName } from "../common/Icon";
import FilterDocs from "./FilterDocs";

// Wait for a pause in typing before validating to avoid a request per keystroke.
const FILTER_VALIDATION_DELAY = 300;

type FilterValidationResponse =
    | { valid: true; description: string }
    | { valid: false; error: string };

type FilterValidationState =
    | { status: "idle" }
    | { status: "pending" }
    | { status: "valid"; description: string }
    | { status: "invalid" | "error"; error: string };

export async function validateFilter(
    expression: string,
    signal?: AbortSignal,
): Promise<FilterValidationResponse> {
    const query = new URLSearchParams({ expression });
    const response = await fetchApi(`/filter/validate?${query}`, { signal });
    if (!response.ok) {
        throw new Error((await response.text()) || response.statusText);
    }
    return await response.json();
}

export enum FilterIcon {
    SEARCH = "search",
    HIGHLIGHT = "highlight",
    INTERCEPT = "intercept",
}

type FilterInputProps = {
    icon: IconName;
    color: string;
    placeholder: string;
    value: string;
    onChange: (value: string) => void;
};

type FilterInputState = {
    value: string;
    validation: FilterValidationState;
    focus: boolean;
    mousefocus: boolean;
};

export default class FilterInput extends Component<
    FilterInputProps,
    FilterInputState
> {
    inputRef = React.createRef<HTMLInputElement>();
    validationTimer?: ReturnType<typeof setTimeout>;
    // Abort obsolete requests, and use a generation counter as a race-safe
    // fallback in case a response completes before cancellation takes effect.
    validationController?: AbortController;
    validationGenerationId = 0;

    constructor(props: FilterInputProps) {
        super(props);

        // Consider both focus and mouseover for showing/hiding the tooltip,
        // because onBlur of the input is triggered before the click on the tooltip
        // finalized, hiding the tooltip just as the user clicks on it.
        this.state = {
            value: this.props.value,
            validation: { status: "idle" },
            focus: false,
            mousefocus: false,
        };

        this.onChange = this.onChange.bind(this);
        this.onFocus = this.onFocus.bind(this);
        this.onBlur = this.onBlur.bind(this);
        this.onKeyDown = this.onKeyDown.bind(this);
        this.onMouseEnter = this.onMouseEnter.bind(this);
        this.onMouseLeave = this.onMouseLeave.bind(this);
        this.selectFilter = this.selectFilter.bind(this);
    }

    UNSAFE_componentWillReceiveProps(nextProps: FilterInputProps) {
        // Local state intentionally diverges from props while typing
        // (only valid filters reach the parent via `onChange`), so an
        // unconditional sync would wipe the user's in-progress text on
        // any unrelated parent re-render.
        if (nextProps.value !== this.props.value) {
            // A successful validation may update the value prop with the draft
            // we already display. Only replace the draft if the new value came
            // from somewhere else.
            if (nextProps.value !== this.state.value) {
                this.cancelValidation();
                this.setState({
                    value: nextProps.value,
                    validation: { status: "idle" },
                });
            }
        }
    }

    componentWillUnmount() {
        this.cancelValidation();
    }

    getDesc() {
        if (!this.state.value) {
            return <FilterDocs selectHandler={this.selectFilter} />;
        }

        switch (this.state.validation.status) {
            case "valid":
                return this.state.validation.description;
            case "invalid":
            case "error":
                return this.state.validation.error;
            case "idle":
            case "pending":
                return <Icon name="loading" className="icon-spin" />;
        }
    }

    cancelValidation() {
        if (this.validationTimer !== undefined) {
            clearTimeout(this.validationTimer);
            this.validationTimer = undefined;
        }
        this.validationController?.abort();
        this.validationController = undefined;
        this.validationGenerationId++;
    }

    scheduleValidation(value: string) {
        this.cancelValidation();
        this.setState({ validation: { status: "pending" } });
        this.validationTimer = setTimeout(() => {
            this.validationTimer = undefined;
            this.validate(value, true);
        }, FILTER_VALIDATION_DELAY);
    }

    async validate(value: string, propagate: boolean) {
        this.cancelValidation();
        const generation = this.validationGenerationId;
        const controller = new AbortController();
        this.validationController = controller;
        this.setState({ validation: { status: "pending" } });

        try {
            const result = await validateFilter(value, controller.signal);
            if (
                generation !== this.validationGenerationId ||
                value !== this.state.value
            ) {
                return;
            }

            if (result.valid) {
                this.setState({
                    validation: {
                        status: "valid",
                        description: result.description,
                    },
                });
                if (propagate) {
                    this.props.onChange(value);
                }
            } else {
                this.setState({
                    validation: { status: "invalid", error: result.error },
                });
            }
        } catch (error) {
            if (
                controller.signal.aborted ||
                generation !== this.validationGenerationId
            ) {
                return;
            }
            this.setState({
                validation: { status: "error", error: String(error) },
            });
        } finally {
            if (generation === this.validationGenerationId) {
                this.validationController = undefined;
            }
        }
    }

    onChange(e: React.ChangeEvent<HTMLInputElement>) {
        const value = e.target.value;
        this.setState({ value });

        if (!value) {
            this.cancelValidation();
            this.setState({
                validation: { status: "valid", description: "" },
            });
            this.props.onChange(value);
        } else {
            this.scheduleValidation(value);
        }
    }

    onFocus() {
        this.setState({ focus: true });
        if (this.state.value && this.state.validation.status === "idle") {
            this.validate(this.state.value, false);
        }
    }

    onBlur() {
        this.setState({ focus: false });
    }

    onMouseEnter() {
        this.setState({ mousefocus: true });
    }

    onMouseLeave() {
        this.setState({ mousefocus: false });
    }

    onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
        if (e.key === "Escape" || e.key === "Enter") {
            this.blur();
            // If closed using ESC/ENTER, hide the tooltip.
            this.setState({ mousefocus: false });
        }
        e.stopPropagation();
    }

    selectFilter(value: string) {
        this.setState({ value });
        this.inputRef.current?.focus();

        this.validate(value, true);
    }

    blur() {
        this.inputRef.current?.blur();
    }

    select() {
        this.inputRef.current?.select();
    }

    render() {
        const { icon, color, placeholder } = this.props;
        const { value, validation, focus, mousefocus } = this.state;
        return (
            <div
                className={classnames("filter-input input-group", {
                    "has-error":
                        validation.status === "invalid" ||
                        validation.status === "error",
                })}
            >
                <span className="input-group-addon">
                    <span style={{ color }}>
                        <Icon name={icon} strokeWidth={2.5} />
                    </span>
                </span>
                <input
                    type="text"
                    ref={this.inputRef}
                    placeholder={placeholder}
                    className="input"
                    value={value}
                    onChange={this.onChange}
                    onFocus={this.onFocus}
                    onBlur={this.onBlur}
                    onKeyDown={this.onKeyDown}
                />
                {(focus || mousefocus) && (
                    <div
                        className="popover bottom"
                        onMouseEnter={this.onMouseEnter}
                        onMouseLeave={this.onMouseLeave}
                    >
                        <div className="arrow" />
                        <div className="popover-content">{this.getDesc()}</div>
                    </div>
                )}
            </div>
        );
    }
}

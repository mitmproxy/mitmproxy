import React, { Component } from "react";
import classnames from "classnames";
import Filt from "../../filt/filt";
import FilterDocs from "./FilterDocs";

type FilterInputProps = {
    type: string;
    color: any;
    placeholder: string;
    value: string;
    onChange: (value) => void;
};

type FilterInputState = {
    value: string;
    focus: boolean;
    mousefocus: boolean;
};

export default class FilterInput extends Component<
    FilterInputProps,
    FilterInputState
> {
    inputRef = React.createRef<HTMLInputElement>();

    constructor(props, context) {
        super(props, context);

        // Consider both focus and mouseover for showing/hiding the tooltip,
        // because onBlur of the input is triggered before the click on the tooltip
        // finalized, hiding the tooltip just as the user clicks on it.
        this.state = {
            value: this.props.value,
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

    UNSAFE_componentWillReceiveProps(nextProps) {
        this.setState({ value: nextProps.value });
    }

    isValid(filt) {
        try {
            if (filt) {
                Filt.parse(filt);
            }
            return true;
        } catch (e) {
            return false;
        }
    }

    getDesc() {
        if (!this.state.value) {
            return <FilterDocs selectHandler={this.selectFilter} />;
        }
        try {
            return Filt.parse(this.state.value).desc;
        } catch (e) {
            return "" + e;
        }
    }

    onChange(e) {
        const value = e.target.value;
        this.setState({ value });

        // Only propagate valid filters upwards.
        if (this.isValid(value)) {
            this.props.onChange(value);
        }
    }

    onFocus() {
        this.setState({ focus: true });
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

    onKeyDown(e) {
        if (e.key === "Escape" || e.key === "Enter") {
            this.blur();
            // If closed using ESC/ENTER, hide the tooltip.
            this.setState({ mousefocus: false });
        }
        e.stopPropagation();
    }

    selectFilter(cmd) {
        this.setState({ value: cmd });
        this.inputRef.current?.focus();
    }

    blur() {
        this.inputRef.current?.blur();
    }

    select() {
        this.inputRef.current?.select();
    }

    render() {
        const { type, color, placeholder } = this.props;
        const { value, focus, mousefocus } = this.state;
        return (
            <div
                className={classnames("filter-input input-group", {
                    "has-error": !this.isValid(value),
                })}
            >
                <span className="input-group-addon">
                    <i className={"fa fa-fw fa-" + type} style={{ color }} />
                </span>
                <input
                    type="text"
                    ref={this.inputRef}
                    placeholder={placeholder}
                    className="form-control"
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

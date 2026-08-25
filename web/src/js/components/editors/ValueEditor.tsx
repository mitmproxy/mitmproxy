import React, { Component } from "react";
import classnames from "classnames";

export interface ValueEditorProps {
    content: string;
    onEditDone: (newVal: string) => void;
    onEditStart?: () => void;
    className?: string;
    onInput?: (newVal: string) => void;
    onKeyDown?: (e: React.KeyboardEvent<HTMLSpanElement>) => void;
    placeholder?: string;
    selectAllOnClick?: boolean;
}

/** "plaintext-only" for browsers which support it, "true" for everyone else */
const plaintextOnly: string = (() => {
    const div = document.createElement("div");
    div.setAttribute("contenteditable", "PLAINTEXT-ONLY");
    return div.contentEditable === "plaintext-only" ? "plaintext-only" : "true";
})();

const EVENT_DEBUG = false;

export default class ValueEditor extends Component<ValueEditorProps> {
    input = React.createRef<HTMLSpanElement>();

    render() {
        const className = classnames("inline-input", this.props.className);

        return (
            <span
                ref={this.input}
                tabIndex={0}
                className={className}
                // @ts-expect-error placeholder works here.
                placeholder={this.props.placeholder}
                onFocus={this.onFocus}
                onBlur={this.onBlur}
                onKeyDown={this.onKeyDown}
                onInput={this.onInput}
                onPaste={this.onPaste}
                onMouseDown={this.onMouseDown}
                onClick={this.onClick}
            >
                {this.props.content}
            </span>
        );
    }

    componentDidUpdate(prevProps: Readonly<ValueEditorProps>) {
        if (prevProps.content !== this.props.content)
            this.props.onInput?.(this.props.content);
    }

    isEditing = (): boolean => {
        return this.input.current?.contentEditable === plaintextOnly;
    };

    startEditing = () => {
        if (!this.input.current) return console.error("unreachable");
        if (this.isEditing()) return;

        // For Firefox, we need to blur() and then focus() with a pause in between,
        // otherwise we run into a bunch of weird bugs.
        this.suppress_events = true;
        this.input.current.blur();
        this.input.current.contentEditable = plaintextOnly;
        window.requestAnimationFrame(() => {
            if (!this.input.current) return;
            this.input.current.focus();
            this.suppress_events = false;

            if (this.props.selectAllOnClick) {
                const range = document.createRange();
                range.selectNodeContents(this.input.current);
                const sel = window.getSelection();
                sel?.removeAllRanges();
                sel?.addRange(range);
            }

            this.props.onEditStart?.();
        });
    };
    resetValue = () => {
        if (!this.input.current) return console.error("unreachable");

        this.input.current.textContent = this.props.content;
        this.props.onInput?.(this.props.content);
    };
    finishEditing = () => {
        if (!this.input.current) return console.error("unreachable");

        this.props.onEditDone(this.input.current.textContent || "");

        this.input.current.blur();
        this.input.current.contentEditable = "inherit";
    };

    onPaste = (e: React.ClipboardEvent<HTMLSpanElement>) => {
        e.preventDefault();
        const content = e.clipboardData.getData("text/plain");
        document.execCommand("insertHTML", false, content);
    };

    /*
    We can't always keep inputs as contenteditable as that breaks text selection big time.
    As such, we do a fairly elaborate dance here to determine if we want to start editing or not.
    The current heuristic is similar to what the Chrome devtools do; we start editing if the user clicks
    and then does not select any content. We also handle focus events, but only if the focus is caused by
    keyboard navigation.
     */
    private suppress_events = false;
    onMouseDown = (_e: React.MouseEvent) => {
        if (EVENT_DEBUG) console.debug("onMouseDown", this.suppress_events);
        this.suppress_events = true;
        window.addEventListener("mouseup", this.onMouseUp, { once: true });
    };

    onMouseUp = (e: MouseEvent) => {
        const still_on_elem = e.target === this.input.current;
        const has_not_selected_text = !window.getSelection()?.toString();

        if (EVENT_DEBUG)
            console.warn(
                "mouseUp",
                this.suppress_events,
                still_on_elem,
                has_not_selected_text,
            );

        if (this.props.selectAllOnClick) {
            if (still_on_elem && has_not_selected_text) {
                this.startEditing();
            }
        } else {
            if (still_on_elem) {
                this.startEditing();
            }
        }
        this.suppress_events = false;
    };

    onClick = (_e: React.MouseEvent) => {
        if (EVENT_DEBUG) console.debug("onClick", this.suppress_events);
    };

    onFocus = (_e: React.FocusEvent) => {
        if (EVENT_DEBUG)
            console.debug("onFocus", this.props.content, this.suppress_events);
        if (!this.input.current) throw "unreachable";
        if (this.suppress_events) return;
        this.startEditing();
    };

    onInput = (_e: React.FormEvent) => {
        this.props.onInput?.(this.input.current?.textContent || "");
    };

    onBlur = (_e: React.FocusEvent<HTMLSpanElement>) => {
        if (EVENT_DEBUG)
            console.debug("onBlur", this.props.content, this.suppress_events);
        if (this.suppress_events) return;
        this.finishEditing();
    };

    onKeyDown = (e: React.KeyboardEvent<HTMLSpanElement>) => {
        if (EVENT_DEBUG) console.debug("keydown", e);
        e.stopPropagation();
        switch (e.key) {
            case "Escape":
                e.preventDefault();
                this.resetValue();
                this.finishEditing();
                break;
            case "Enter":
                if (!e.shiftKey) {
                    e.preventDefault();
                    this.finishEditing();
                }
                break;
            default:
                break;
        }
        this.props.onKeyDown?.(e);
    };
}

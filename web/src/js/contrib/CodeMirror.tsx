/* eslint-disable */
// Adapted from https://www.npmjs.com/package/react-codemirror
// Copyright (c) 2016 Jed Watson. MIT Licensed.

import * as React from "react";
import className from "classnames";
import codemirror from "codemirror";
import { isEqual } from "lodash";

function normalizeLineEndings(str) {
    if (!str) return str;
    return str.replace(/\r\n|\r/g, "\n");
}

type CodeMirrorProps = {
    autoFocus?: boolean;
    className?: any;
    codeMirrorInstance?: Function;
    defaultValue?: string;
    name?: string;
    onChange: Function;
    onCursorActivity?: Function;
    onFocusChange?: Function;
    onScroll?: Function;
    options?: any;
    path?: string;
    value?: string;
    preserveScrollPosition?: boolean;
};

type CodeMirrorState = {
    isFocused: boolean;
};

export default class CodeMirror extends React.Component<
    CodeMirrorProps,
    CodeMirrorState
> {
    codeMirror: any;
    textareaNode: any;

    constructor(props) {
        super(props);
        this.state = {
            isFocused: false,
        };
    }

    static defaultProps = {
        preserveScrollPosition: false,
    };

    getCodeMirrorInstance() {
        return this.props.codeMirrorInstance || codemirror;
    }

    UNSAFE_componentWillMount() {
        //this.componentWillReceiveProps = _.debounce(this.componentWillReceiveProps, 0);
        if (this.props.path) {
            console.error(
                "Warning: react-codemirror: the `path` prop has been changed to `name`",
            );
        }
    }

    componentDidMount() {
        const codeMirrorInstance = this.getCodeMirrorInstance();
        this.codeMirror = codeMirrorInstance.fromTextArea(
            this.textareaNode,
            this.props.options,
        );
        this.codeMirror.on("change", this.codemirrorValueChanged.bind(this));
        this.codeMirror.on("cursorActivity", this.cursorActivity.bind(this));
        this.codeMirror.on("focus", this.focusChanged.bind(this, true));
        this.codeMirror.on("blur", this.focusChanged.bind(this, false));
        this.codeMirror.on("scroll", this.scrollChanged.bind(this));
        this.codeMirror.setValue(
            this.props.defaultValue || this.props.value || "",
        );
    }

    componentWillUnmount() {
        // is there a lighter-weight way to remove the cm instance?
        if (this.codeMirror) {
            this.codeMirror.toTextArea();
        }
    }

    UNSAFE_componentWillReceiveProps(nextProps) {
        if (
            this.codeMirror &&
            nextProps.value !== undefined &&
            nextProps.value !== this.props.value &&
            normalizeLineEndings(this.codeMirror.getValue()) !==
                normalizeLineEndings(nextProps.value)
        ) {
            if (this.props.preserveScrollPosition) {
                const prevScrollPosition = this.codeMirror.getScrollInfo();
                this.codeMirror.setValue(nextProps.value);
                this.codeMirror.scrollTo(
                    prevScrollPosition.left,
                    prevScrollPosition.top,
                );
            } else {
                this.codeMirror.setValue(nextProps.value);
            }
        }
        if (typeof nextProps.options === "object") {
            for (const optionName in nextProps.options) {
                if (nextProps.options.hasOwnProperty(optionName)) {
                    this.setOptionIfChanged(
                        optionName,
                        nextProps.options[optionName],
                    );
                }
            }
        }
    }

    setOptionIfChanged(optionName, newValue) {
        const oldValue = this.codeMirror.getOption(optionName);
        if (!isEqual(oldValue, newValue)) {
            this.codeMirror.setOption(optionName, newValue);
        }
    }

    getCodeMirror() {
        return this.codeMirror;
    }

    focus() {
        if (this.codeMirror) {
            this.codeMirror.focus();
        }
    }

    focusChanged(focused) {
        this.setState({
            isFocused: focused,
        });
        this.props.onFocusChange && this.props.onFocusChange(focused);
    }

    cursorActivity(cm) {
        this.props.onCursorActivity && this.props.onCursorActivity(cm);
    }

    scrollChanged(cm) {
        this.props.onScroll && this.props.onScroll(cm.getScrollInfo());
    }

    codemirrorValueChanged(doc, change) {
        if (this.props.onChange && change.origin !== "setValue") {
            this.props.onChange(doc.getValue(), change);
        }
    }

    render() {
        const editorClassName = className(
            "ReactCodeMirror",
            this.state.isFocused ? "ReactCodeMirror--focused" : null,
            this.props.className,
        );
        return (
            <div className={editorClassName}>
                <textarea
                    ref={(ref) => (this.textareaNode = ref)}
                    name={this.props.name || this.props.path}
                    defaultValue={this.props.value}
                    autoComplete="off"
                    autoFocus={this.props.autoFocus}
                />
            </div>
        );
    }
}

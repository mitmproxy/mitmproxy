import React, { Component } from "react";
import classnames from "classnames";

type SplitterState = {
    applied: boolean;
    startPos: number;
    // .dragPointer === 0.1 means not dragging
    dragPointer: number;
};

type SplitterProps = {
    axis: string;
};

export default class Splitter extends Component<SplitterProps, SplitterState> {
    static defaultProps = { axis: "x" };

    node = React.createRef<HTMLDivElement>();

    constructor(props, context) {
        super(props, context);
        this.state = { applied: false, startPos: 0, dragPointer: 0.1 };
        this.onLostPointerCapture = this.onLostPointerCapture.bind(this);
        this.onPointerDown = this.onPointerDown.bind(this);
        this.onPointerMove = this.onPointerMove.bind(this);
    }

    onPointerDown(e) {
        if (this.state.dragPointer !== 0.1) {
            return;
        }
        e.target.setPointerCapture(e.pointerId);
        this.setState({
            startPos: this.props.axis === "x" ? e.pageX : e.pageY,
            dragPointer: e.pointerId,
        });
    }

    onLostPointerCapture(e) {
        if (this.state.dragPointer !== e.pointerId) {
            return;
        }
        const node = e.target.parentNode;
        const prev = node.previousElementSibling;

        node.style.transform = "";
        prev.style.flex = `0 0 ${Math.max(
            0,
            (this.props.axis === "x"
                ? prev.offsetWidth + e.pageX
                : prev.offsetHeight + e.pageY) - this.state.startPos,
        )}px`;
        node.nextElementSibling.style.flex = "1 1 auto";

        this.setState({ applied: true, dragPointer: 0.1 });
        this.onResize();
    }

    onPointerMove(e) {
        if (this.state.dragPointer !== e.pointerId) {
            return;
        }
        e.target.parentNode.style.transform =
            this.props.axis === "x"
                ? `translateX(${e.pageX - this.state.startPos}px)`
                : `translateY(${e.pageY - this.state.startPos}px)`;
    }

    onResize() {
        // Trigger a global resize event. This notifies components that employ virtual scrolling
        // that their viewport may have changed.
        window.setTimeout(
            () => window.dispatchEvent(new CustomEvent("resize")),
            1,
        );
    }

    reset(willUnmount) {
        if (!this.state.applied) {
            return;
        }

        if (this.node.current?.previousElementSibling instanceof HTMLElement) {
            this.node.current.previousElementSibling.style.flex = "";
        }
        if (this.node.current?.nextElementSibling instanceof HTMLElement) {
            this.node.current.nextElementSibling.style.flex = "";
        }

        if (!willUnmount) {
            this.setState({ applied: false });
        }
        this.onResize();
    }

    componentWillUnmount() {
        this.reset(true);
    }

    render() {
        return (
            <div
                ref={this.node}
                className={classnames(
                    "splitter",
                    this.props.axis === "x" ? "splitter-x" : "splitter-y",
                )}
            >
                <div
                    onLostPointerCapture={this.onLostPointerCapture}
                    onPointerDown={this.onPointerDown}
                    onPointerMove={this.onPointerMove}
                />
            </div>
        );
    }
}

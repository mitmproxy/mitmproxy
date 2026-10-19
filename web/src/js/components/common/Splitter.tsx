import React, { Component } from "react";
import classnames from "classnames";

type SplitterState = {
    applied: boolean;
    // .dragPointer === 0.1 means not dragging
    dragPointer: number;
};

type SplitterProps = {
    axis: string;
};

export default class Splitter extends Component<SplitterProps, SplitterState> {
    static defaultProps = { axis: "x" };

    node = React.createRef<HTMLDivElement>();

    // Captured at drag start so each move is computed from fixed values; using
    // the live (already-resized) sizes would compound the delta and the panel
    // would run away from the pointer.
    private dragStartPos = 0;
    private dragPrevStart = 0;
    private dragTotal = 0;

    constructor(props: SplitterProps) {
        super(props);
        this.state = { applied: false, dragPointer: 0.1 };
        this.onLostPointerCapture = this.onLostPointerCapture.bind(this);
        this.onPointerDown = this.onPointerDown.bind(this);
        this.onPointerMove = this.onPointerMove.bind(this);
    }

    private isX() {
        return this.props.axis === "x";
    }

    private siblings() {
        const node = this.node.current!;
        return {
            prev: node.previousElementSibling as HTMLElement | null,
            next: node.nextElementSibling as HTMLElement | null,
        };
    }

    private sizeOf(el: HTMLElement) {
        return this.isX() ? el.offsetWidth : el.offsetHeight;
    }

    // Clamp keeps the panel within the shared space: it can collapse to 0 but
    // not cross the far panel.
    private applyDrag(pos: number) {
        const { prev, next } = this.siblings();
        if (!prev || !next) {
            return;
        }
        const desired = this.dragPrevStart + (pos - this.dragStartPos);
        const newPrev = Math.max(0, Math.min(desired, this.dragTotal));

        prev.style.flex = `0 0 ${newPrev}px`;
        next.style.flex = "1 1 auto";
    }

    onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
        if (this.state.dragPointer !== 0.1) {
            return;
        }
        (e.target as HTMLDivElement).setPointerCapture(e.pointerId);

        const { prev, next } = this.siblings();
        const prevSize = prev ? this.sizeOf(prev) : 0;
        const nextSize = next ? this.sizeOf(next) : 0;
        this.dragStartPos = this.isX() ? e.pageX : e.pageY;
        this.dragPrevStart = prevSize;
        this.dragTotal = prevSize + nextSize;

        document.body.classList.add("splitter-resizing");
        if (!this.isX()) {
            document.body.classList.add("splitter-resizing-y");
        }

        this.setState({ dragPointer: e.pointerId });
    }

    onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
        if (this.state.dragPointer !== e.pointerId) {
            return;
        }
        this.applyDrag(this.isX() ? e.pageX : e.pageY);
    }

    onLostPointerCapture(e: React.PointerEvent<HTMLDivElement>) {
        if (this.state.dragPointer !== e.pointerId) {
            return;
        }

        document.body.classList.remove(
            "splitter-resizing",
            "splitter-resizing-y",
        );

        this.setState({ applied: true, dragPointer: 0.1 });
        this.onResize();
    }

    onResize() {
        // Trigger a global resize event. This notifies components that employ virtual scrolling
        // that their viewport may have changed.
        window.setTimeout(
            () => window.dispatchEvent(new CustomEvent("resize")),
            1,
        );
    }

    reset(willUnmount: boolean) {
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
        document.body.classList.remove(
            "splitter-resizing",
            "splitter-resizing-y",
        );
        this.reset(true);
    }

    render() {
        return (
            <div
                ref={this.node}
                className={classnames(
                    "splitter",
                    this.isX() ? "splitter-x" : "splitter-y",
                    { "splitter-dragging": this.state.dragPointer !== 0.1 },
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

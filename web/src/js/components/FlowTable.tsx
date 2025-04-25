import * as React from "react";
import { connect, shallowEqual } from "react-redux";
import * as autoscroll from "./helpers/AutoScroll";
import { calcVScroll, VScroll } from "./helpers/VirtualScroll";
import FlowTableHead from "./FlowTable/FlowTableHead";
import FlowRow from "./FlowTable/FlowRow";
import Filt from "../filt/filt";
import { Flow } from "../flow";
import { RootState } from "../ducks";

type FlowTableProps = {
    flowView: Flow[];
    flowViewIndex: { [id: string]: number };
    rowHeight: number;
    highlight: string;
    flowSelection: Flow[];
    flowSelectionIndex: { [id: string]: number };
};

type FlowTableState = {
    vScroll: VScroll;
    viewportTop: number;
};

export class PureFlowTable extends React.Component<
    FlowTableProps,
    FlowTableState
> {
    static defaultProps = {
        rowHeight: 32,
    };
    private viewport = React.createRef<HTMLDivElement>();
    private head = React.createRef<HTMLTableSectionElement>();

    constructor(props, context) {
        super(props, context);

        this.state = {
            vScroll: calcVScroll(),
            viewportTop: 0,
        };
        this.onViewportUpdate = this.onViewportUpdate.bind(this);
    }

    componentDidMount() {
        window.addEventListener("resize", this.onViewportUpdate);
        this.onViewportUpdate();
    }

    componentWillUnmount() {
        window.removeEventListener("resize", this.onViewportUpdate);
    }

    getSnapshotBeforeUpdate() {
        return autoscroll.isAtBottom(this.viewport);
    }

    componentDidUpdate(
        prevProps: FlowTableProps,
        prevState: FlowTableState,
        snapshot,
    ) {
        if (snapshot) {
            autoscroll.adjustScrollTop(this.viewport);
        }
        this.onViewportUpdate();

        const currentSelection = this.props.flowSelection;
        const prevSelection = prevProps.flowSelection;

        const selectedPotentiallyOffscreenFlow =
            currentSelection.length === 1 &&
            currentSelection[0].id !== prevSelection[0]?.id;

        if (selectedPotentiallyOffscreenFlow) {
            const { rowHeight, flowViewIndex, flowSelection } = this.props;
            const viewport = this.viewport.current!;
            const head = this.head.current;

            const headHeight = head ? head.offsetHeight : 0;

            const rowTop =
                flowViewIndex[flowSelection[0].id] * rowHeight + headHeight;
            const rowBottom = rowTop + rowHeight;

            const viewportTop = viewport.scrollTop;
            const viewportHeight = viewport.offsetHeight;

            // Account for pinned thead
            if (rowTop - headHeight < viewportTop) {
                viewport.scrollTop = rowTop - headHeight;
            } else if (rowBottom > viewportTop + viewportHeight) {
                viewport.scrollTop = rowBottom - viewportHeight;
            }
            this.onViewportUpdate();
        }
    }

    onViewportUpdate() {
        const viewport = this.viewport.current!;
        const viewportTop = viewport.scrollTop || 0;

        const vScroll = calcVScroll({
            viewportTop,
            viewportHeight: viewport.offsetHeight || 0,
            itemCount: this.props.flowView.length,
            rowHeight: this.props.rowHeight,
        });

        if (
            this.state.viewportTop !== viewportTop ||
            !shallowEqual(this.state.vScroll, vScroll)
        ) {
            // the next rendered state may only have much lower number of rows compared to what the current
            // viewportHeight anticipates. To make sure that we update (almost) at once, we already constrain
            // the maximum viewportTop value. See https://github.com/mitmproxy/mitmproxy/pull/5658 for details.
            const newViewportTop = Math.min(
                viewportTop,
                vScroll.end * this.props.rowHeight,
            );
            this.setState({
                vScroll,
                viewportTop: newViewportTop,
            });
        }
    }

    render() {
        const { vScroll, viewportTop } = this.state;
        const { flowView, flowSelectionIndex, highlight } = this.props;
        const isHighlighted = highlight ? Filt.parse(highlight) : () => false;

        return (
            <div
                className="flow-table"
                onScroll={this.onViewportUpdate}
                ref={this.viewport}
            >
                <table>
                    <thead
                        ref={this.head}
                        style={{ transform: `translateY(${viewportTop}px)` }}
                    >
                        <FlowTableHead />
                    </thead>
                    <tbody>
                        <tr style={{ height: vScroll.paddingTop }} />
                        {flowView
                            .slice(vScroll.start, vScroll.end)
                            .map((flow) => (
                                <FlowRow
                                    key={flow.id}
                                    flow={flow}
                                    selected={flow.id in flowSelectionIndex}
                                    highlighted={isHighlighted(flow)}
                                />
                            ))}
                        <tr style={{ height: vScroll.paddingBottom }} />
                    </tbody>
                </table>
            </div>
        );
    }
}

export default connect((state: RootState) => ({
    flowView: state.flows.view,
    flowViewIndex: state.flows.viewIndex,
    highlight: state.flows.highlight,
    flowSelection: state.flows.selected,
    flowSelectionIndex: state.flows.selectedIndex,
}))(PureFlowTable);

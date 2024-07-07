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
    flows: Flow[];
    rowHeight: number;
    highlight: string;
    selected: Flow;
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

    componentDidUpdate(prevProps, prevState, snapshot) {
        if (snapshot) {
            autoscroll.adjustScrollTop(this.viewport);
        }
        this.onViewportUpdate();

        const selectedNewFlow =
            this.props.selected && this.props.selected !== prevProps.selected;
        if (selectedNewFlow) {
            const { rowHeight, flows, selected } = this.props;
            const viewport = this.viewport.current!;
            const head = this.head.current;

            const headHeight = head ? head.offsetHeight : 0;

            const rowTop = flows.indexOf(selected) * rowHeight + headHeight;
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
            itemCount: this.props.flows.length,
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
        const { flows, selected, highlight } = this.props;
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
                        {flows.slice(vScroll.start, vScroll.end).map((flow) => (
                            <FlowRow
                                key={flow.id}
                                flow={flow}
                                selected={flow === selected}
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
    flows: state.flows.view,
    highlight: state.flows.highlight,
    selected: state.flows.byId[state.flows.selected[0]],
}))(PureFlowTable);

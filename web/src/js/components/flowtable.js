import React from "react";
import ReactDOM from "react-dom";
import {connect} from 'react-redux'
import classNames from "classnames";
import {reverseString} from "../utils.js";
import _ from "lodash";
import shallowEqual from "shallowequal";
import AutoScroll from "./helpers/AutoScroll";
import {calcVScroll} from "./helpers/VirtualScroll";
import flowtable_columns from "./flowtable-columns.js";
import Filt from "../filt/filt";


FlowRow.propTypes = {
    selectFlow: React.PropTypes.func.isRequired,
    columns: React.PropTypes.array.isRequired,
    flow: React.PropTypes.object.isRequired,
    highlight: React.PropTypes.string,
    selected: React.PropTypes.bool,
};

function FlowRow({flow, selected, highlight, columns, selectFlow}) {

    const className = classNames({
        "selected": selected,
        "highlighted": highlight && parseFilter(highlight)(flow),
        "intercepted": flow.intercepted,
        "has-request": flow.request,
        "has-response": flow.response,
    });

    return (
        <tr className={className} onClick={() => selectFlow(flow)}>
            {columns.map(Column => (
                <Column key={Column.name} flow={flow}/>
            ))}
        </tr>
    );
}

const FlowRowContainer = connect(
    (state, ownProps) => ({
        flow: state.flows.all.byId[ownProps.flowId],
        highlight: state.flows.highlight,
        selected: state.flows.selected.indexOf(ownProps.flowId) >= 0
    })
)(FlowRow)

function FlowTableHead({setSort, columns, sort}) {

        //const hasSort = Column.sortKeyFun;

        // let sortDesc = this.props.sort.sortDesc;
        //
        // if (Column === this.props.sort.sortColumn) {
        //     sortDesc = !sortDesc;
        //     this.props.setSort(sortColumn, sortDesc);
        // } else {
        //     this.props.setSort({sortColumn: hasSort && Column, sortDesc: false});
        // }
        //
        // let sortKeyFun = Column.sortKeyFun;
        // if (sortDesc) {
        //     sortKeyFun = hasSort && function () {
        //             const k = Column.sortKeyFun.apply(this, arguments);
        //             if (_.isString(k)) {
        //                 return reverseString("" + k);
        //             }
        //             return -k;
        //         };
        // }
        //this.props.setSortKeyFun(sortKeyFun);

        const sortColumn = sort.sortColumn;
        const sortType = sort.sortDesc ? "sort-desc" : "sort-asc";

        return (
            <tr>
                {columns.map(Column => (
                    <Column.Title
                        key={Column.name}
                        onClick={() => setSort({sortColumn: Column.name, sortDesc: Column.name != sort.sortColumn ? false : !sort.sortDesc})}
                        className={sortColumn === Column.name ? sortType : undefined}
                    />
                ))}
            </tr>
        );
}

FlowTableHead.propTypes = {
        setSort: React.PropTypes.func.isRequired,
        sort: React.PropTypes.object.isRequired,
        columns: React.PropTypes.array.isRequired
};

const FlowTableHeadContainer = connect(
    (state, ownProps) => ({
        sort: state.flows.sort
    })
)(FlowTableHead)

class FlowTable extends React.Component {

    static propTypes = {
        rowHeight: React.PropTypes.number,
    };

    static defaultProps = {
        rowHeight: 32,
    };

    constructor(props, context) {
        super(props, context);

        this.state = {vScroll: calcVScroll()};

        this.onViewportUpdate = this.onViewportUpdate.bind(this);
    }

    componentWillMount() {
        window.addEventListener("resize", this.onViewportUpdate);
    }

    componentWillUnmount() {
        window.removeEventListener("resize", this.onViewportUpdate);
    }

    componentWillReceiveProps(nextProps) {
        if (nextProps.selected && nextProps.selected !== this.props.selected) {
            window.setTimeout(() => this.scrollIntoView(nextProps.selected), 1)
        }
    }

    componentDidUpdate() {
        this.onViewportUpdate();
    }

    onViewportUpdate() {
        const viewport = ReactDOM.findDOMNode(this);
        const viewportTop = viewport.scrollTop;

        const vScroll = calcVScroll({
            viewportTop,
            viewportHeight: viewport.offsetHeight,
            itemCount: this.props.flows.length,
            rowHeight: this.props.rowHeight,
        });

        if (!shallowEqual(this.state.vScroll, vScroll) ||
            this.state.viewportTop !== viewportTop) {
            this.setState({vScroll, viewportTop});
        }
    }

    scrollIntoView(flow) {
        const viewport = ReactDOM.findDOMNode(this);
        const index = this.props.flows.indexOf(flow);
        const rowHeight = this.props.rowHeight;
        const head = ReactDOM.findDOMNode(this.refs.head);

        const headHeight = head ? head.offsetHeight : 0;

        const rowTop = (index * rowHeight) + headHeight;
        const rowBottom = rowTop + rowHeight;

        const viewportTop = viewport.scrollTop;
        const viewportHeight = viewport.offsetHeight;

        // Account for pinned thead
        if (rowTop - headHeight < viewportTop) {
            viewport.scrollTop = rowTop - headHeight;
        } else if (rowBottom > viewportTop + viewportHeight) {
            viewport.scrollTop = rowBottom - viewportHeight;
        }
    }

    render() {
        const vScroll = this.state.vScroll;
        const flows = this.props.flows.slice(vScroll.start, vScroll.end);

        const transform = `translate(0,${this.state.viewportTop}px)`;

        return (
            <div className="flow-table" onScroll={this.onViewportUpdate}>
                <table>
                    <thead ref="head" style={{ transform }}>
                    <FlowTableHeadContainer
                        columns={flowtable_columns}
                        setSortKeyFun={this.props.setSortKeyFun}
                        setSort={this.props.setSort}
                    />
                    </thead>
                    <tbody>
                    <tr style={{ height: vScroll.paddingTop }}></tr>
                    {flows.map(flow => (
                        <FlowRowContainer
                            key={flow.id}
                            flowId={flow.id}
                            columns={flowtable_columns}
                            selectFlow={this.props.selectFlow}
                        />
                    ))}
                    <tr style={{ height: vScroll.paddingBottom }}></tr>
                    </tbody>
                </table>
            </div>
        );
    }
}

FlowTable = AutoScroll(FlowTable)


const parseFilter = _.memoize(Filt.parse)

const FlowTableContainer = connect(
    state => ({
        flows: state.flows.view,
    })
)(FlowTable)

export default FlowTableContainer;

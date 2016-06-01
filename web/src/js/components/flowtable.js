import React from "react";
import ReactDOM from "react-dom";
import classNames from "classnames";
import {reverseString} from "../utils.js";
import _ from "lodash";
import shallowEqual from "shallowequal";
import AutoScroll from "./helpers/AutoScroll";
import {calcVScroll} from "./helpers/VirtualScroll";
import flowtable_columns from "./flowtable-columns.js";

FlowRow.propTypes = {
    selectFlow: React.PropTypes.func.isRequired,
    columns: React.PropTypes.array.isRequired,
    flow: React.PropTypes.object.isRequired,
    highlighted: React.PropTypes.bool,
    selected: React.PropTypes.bool,
};

function FlowRow(props) {
    const flow = props.flow;

    const className = classNames({
        "selected": props.selected,
        "highlighted": props.highlighted,
        "intercepted": flow.intercepted,
        "has-request": flow.request,
        "has-response": flow.response,
    });

    return (
        <tr className={className} onClick={() => props.selectFlow(flow)}>
            {props.columns.map(Column => (
                <Column key={Column.displayName} flow={flow}/>
            ))}
        </tr>
    );
}

class FlowTableHead extends React.Component {

    static propTypes = {
        setSortKeyFun: React.PropTypes.func.isRequired,
        columns: React.PropTypes.array.isRequired,
        onChangeSortMethod: React.PropTypes.array.isRequired,
        sortDesc: React.PropTypes.array.isRequired,
        sortColumn: React.PropTypes.array.isRequired
    };

    constructor(props, context) {
        super(props, context);
        this.state = { sortColumn: undefined, sortDesc: false };
    }

    onClick(Column) {
        const hasSort = Column.sortKeyFun;

        var sortDesc = this.props.sortDesc;

        if (Column === this.props.sortColumn) {
            sortDesc = !sortDesc;
            this.props.onChangeSortMethod(undefined, !sortDesc);
        } else {
            this.props.onChangeSortMethod(hasSort && Column, false);
        }

        let sortKeyFun = Column.sortKeyFun;
        if (sortDesc) {
            sortKeyFun = hasSort && function() {
                const k = Column.sortKeyFun.apply(this, arguments);
                if (_.isString(k)) {
                    return reverseString("" + k);
                }
                return -k;
            };
        }

        this.props.setSortKeyFun(sortKeyFun);
    }

    render() {
        const sortColumn = this.props.sortColumn;
        const sortType = this.props.sortDesc ? "sort-desc" : "sort-asc";
        return (
            <tr>
                {this.props.columns.map(Column => (
                    <Column.Title
                        key={Column.displayName}
                        onClick={() => this.onClick(Column)}
                        className={sortColumn === Column && sortType}
                    />
                ))}
            </tr>
        );
    }
}

class FlowTable extends React.Component {

    static contextTypes = {
        view: React.PropTypes.object.isRequired,
    };

    static propTypes = {
        rowHeight: React.PropTypes.number,
        flows: React.PropTypes.array.isRequired,
        vScroll: React.PropTypes.array.isRequired
    };

    static defaultProps = {
        rowHeight: 32,
    };

    constructor(props, context) {
        super(props, context);

        this.onChange = this.onChange.bind(this);
        this.onViewportUpdate = this.onViewportUpdate.bind(this);
    }

    componentWillMount() {
        window.addEventListener("resize", this.onViewportUpdate);
        this.context.view.addListener("add", this.onChange);
        this.context.view.addListener("update", this.onChange);
        this.context.view.addListener("remove", this.onChange);
        this.context.view.addListener("recalculate", this.onChange);
    }

    componentWillUnmount() {
        window.removeEventListener("resize", this.onViewportUpdate);
        this.context.view.removeListener("add", this.onChange);
        this.context.view.removeListener("update", this.onChange);
        this.context.view.removeListener("remove", this.onChange);
        this.context.view.removeListener("recalculate", this.onChange);
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

        if (!shallowEqual(this.props.vScroll, vScroll) ||
            this.props.viewportTop !== viewportTop) {
            this.props.onViewportUpdate(vScroll, viewportTop);
        }
    }

    onChange() {
        this.props.onChange(this.context.view.list);
    }

    scrollIntoView(flow) {
        const viewport = ReactDOM.findDOMNode(this);
        const index = this.context.view.indexOf(flow);
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
        const vScroll = this.props.vScroll;
        const highlight = this.context.view._highlight;
        const flows = this.props.flows.slice(vScroll.start, vScroll.end);

        const transform = `translate(0,${this.props.viewportTop}px)`;

        return (
            <div className="flow-table" onScroll={this.onViewportUpdate}>
                <table>
                    <thead ref="head" style={{ transform }}>
                        <FlowTableHead
                            columns={flowtable_columns}
                            setSortKeyFun={this.props.setSortKeyFun}
                            onChangeSortMethod={this.props.onChangeSortMethod}
                            sortColumn={this.props.sortColumn}
                            sortDesc={this.props.sortDesc}
                        />
                    </thead>
                    <tbody>
                        <tr style={{ height: vScroll.paddingTop }}></tr>
                        {flows.map(flow => (
                            <FlowRow
                                key={flow.id}
                                flow={flow}
                                columns={flowtable_columns}
                                selected={flow === this.props.selected}
                                highlighted={highlight && highlight[flow.id]}
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

export default AutoScroll(FlowTable);

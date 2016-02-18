var React = require("react");
var common = require("./common.js");
var utils = require("../utils.js");
var _ = require("lodash");

var VirtualScrollMixin = require("./virtualscroll.js");
var flowtable_columns = require("./flowtable-columns.js");

var FlowRow = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var columns = this.props.columns.map(function (Column) {
            return <Column key={Column.displayName} flow={flow}/>;
        }.bind(this));
        var className = "";
        if (this.props.selected) {
            className += " selected";
        }
        if (this.props.highlighted) {
            className += " highlighted";
        }
        if (flow.intercepted) {
            className += " intercepted";
        }
        if (flow.request) {
            className += " has-request";
        }
        if (flow.response) {
            className += " has-response";
        }

        return (
            <tr className={className} onClick={this.props.selectFlow.bind(null, flow)}>
                {columns}
            </tr>);
    },
    shouldComponentUpdate: function (nextProps) {
        return true;
        // Further optimization could be done here
        // by calling forceUpdate on flow updates, selection changes and column changes.
        //return (
        //(this.props.columns.length !== nextProps.columns.length) ||
        //(this.props.selected !== nextProps.selected)
        //);
    }
});

var FlowTableHead = React.createClass({
    getInitialState: function(){
        return {
            sortColumn: undefined,
            sortDesc: false
        };
    },
    onClick: function(Column){
        var sortDesc = this.state.sortDesc;
        var hasSort = Column.sortKeyFun;
        if(Column === this.state.sortColumn){
            sortDesc = !sortDesc;
            this.setState({
                sortDesc: sortDesc
            });
        } else {
            this.setState({
                sortColumn: hasSort && Column,
                sortDesc: false
            })
        }
        var sortKeyFun;
        if(!sortDesc){
            sortKeyFun = Column.sortKeyFun;
        } else {
            sortKeyFun = hasSort && function(){
                var k = Column.sortKeyFun.apply(this, arguments);
                if(_.isString(k)){
                    return utils.reverseString(""+k);
                } else {
                    return -k;
                }
            }
        }
        this.props.setSortKeyFun(sortKeyFun);
    },
    render: function () {
        var columns = this.props.columns.map(function (Column) {
            var onClick = this.onClick.bind(this, Column);
            var className;
            if(this.state.sortColumn === Column) {
                if(this.state.sortDesc){
                    className = "sort-desc";
                } else {
                    className = "sort-asc";
                }
            }
            return <Column.Title
                        key={Column.displayName}
                        onClick={onClick}
                        className={className} />;
        }.bind(this));
        return <thead>
            <tr>{columns}</tr>
        </thead>;
    }
});


var ROW_HEIGHT = 32;

var FlowTable = React.createClass({
    mixins: [common.StickyHeadMixin, common.AutoScrollMixin, VirtualScrollMixin],
    contextTypes: {
        view: React.PropTypes.object.isRequired
    },
    getInitialState: function () {
        return {
            columns: flowtable_columns
        };
    },
    componentWillMount: function () {
        this.context.view.addListener("add", this.onChange);
        this.context.view.addListener("update", this.onChange);
        this.context.view.addListener("remove", this.onChange);
        this.context.view.addListener("recalculate", this.onChange);
    },
    componentWillUnmount: function(){
        this.context.view.removeListener("add", this.onChange);
        this.context.view.removeListener("update", this.onChange);
        this.context.view.removeListener("remove", this.onChange);
        this.context.view.removeListener("recalculate", this.onChange);
    },
    getDefaultProps: function () {
        return {
            rowHeight: ROW_HEIGHT
        };
    },
    onScrollFlowTable: function () {
        this.adjustHead();
        this.onScroll();
    },
    onChange: function () {
        this.forceUpdate();
    },
    scrollIntoView: function (flow) {
        this.scrollRowIntoView(
            this.context.view.index(flow),
            this.refs.body.getDOMNode().offsetTop
        );
    },
    renderRow: function (flow) {
        var selected = (flow === this.props.selected);
        var highlighted =
            (
            this.context.view._highlight &&
            this.context.view._highlight[flow.id]
            );

        return <FlowRow key={flow.id}
            ref={flow.id}
            flow={flow}
            columns={this.state.columns}
            selected={selected}
            highlighted={highlighted}
            selectFlow={this.props.selectFlow}
        />;
    },
    render: function () {
        var flows = this.context.view.list;
        var rows = this.renderRows(flows);

        return (
            <div className="flow-table" onScroll={this.onScrollFlowTable}>
                <table>
                    <FlowTableHead ref="head"
                        columns={this.state.columns}
                        setSortKeyFun={this.props.setSortKeyFun}/>
                    <tbody ref="body">
                        { this.getPlaceholderTop(flows.length) }
                        {rows}
                        { this.getPlaceholderBottom(flows.length) }
                    </tbody>
                </table>
            </div>
        );
    }
});

module.exports = FlowTable;

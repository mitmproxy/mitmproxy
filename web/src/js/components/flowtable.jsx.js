var FlowRow = React.createClass({
    render: function () {
        var flow = this.props.flow;
        var columns = this.props.columns.map(function (Column) {
            return <Column key={Column.displayName} flow={flow}/>;
        }.bind(this));
        var className = "";
        if (this.props.selected) {
            className += "selected";
        }
        return (
            <tr className={className} onClick={this.props.selectFlow.bind(null, flow)}>
                {columns}
            </tr>);
    },
    shouldComponentUpdate: function (nextProps) {
        var isEqual = (
        this.props.columns.length === nextProps.columns.length &&
        this.props.selected === nextProps.selected &&
        this.props.flow.response === nextProps.flow.response);
        return !isEqual;
    }
});

var FlowTableHead = React.createClass({
    render: function () {
        var columns = this.props.columns.map(function (column) {
            return column.renderTitle();
        }.bind(this));
        return <thead>
            <tr>{columns}</tr>
        </thead>;
    }
});

var FlowTableBody = React.createClass({
    render: function () {
        var rows = this.props.flows.map(function (flow) {
            var selected = (flow == this.props.selected);
            return <FlowRow key={flow.id}
                ref={flow.id}
                flow={flow}
                columns={this.props.columns}
                selected={selected}
                selectFlow={this.props.selectFlow}
            />;
        }.bind(this));
        return <tbody>{rows}</tbody>;
    }
});


var FlowTable = React.createClass({
    mixins: [StickyHeadMixin, AutoScrollMixin],
    getInitialState: function () {
        return {
            columns: all_columns
        };
    },
    scrollIntoView: function (flow) {
        // Now comes the fun part: Scroll the flow into the view.
        var viewport = this.getDOMNode();
        var flowNode = this.refs.body.refs[flow.id].getDOMNode();
        var viewport_top = viewport.scrollTop;
        var viewport_bottom = viewport_top + viewport.offsetHeight;
        var flowNode_top = flowNode.offsetTop;
        var flowNode_bottom = flowNode_top + flowNode.offsetHeight;

        // Account for pinned thead by pretending that the flowNode starts
        // -thead_height pixel earlier.
        flowNode_top -= this.refs.body.getDOMNode().offsetTop;

        if (flowNode_top < viewport_top) {
            viewport.scrollTop = flowNode_top;
        } else if (flowNode_bottom > viewport_bottom) {
            viewport.scrollTop = flowNode_bottom - viewport.offsetHeight;
        }
    },
    render: function () {
        return (
            <div className="flow-table" onScroll={this.adjustHead}>
                <table>
                    <FlowTableHead ref="head"
                        columns={this.state.columns}/>
                    <FlowTableBody ref="body"
                        flows={this.props.flows}
                        selected={this.props.selected}
                        selectFlow={this.props.selectFlow}
                        columns={this.state.columns}/>
                </table>
            </div>
        );
    }
});

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
    render: function () {
        var columns = this.props.columns.map(function (column) {
            return column.renderTitle();
        }.bind(this));
        return <thead>
            <tr>{columns}</tr>
        </thead>;
    }
});


var ROW_HEIGHT = 32;

var FlowTable = React.createClass({
    mixins: [StickyHeadMixin, AutoScrollMixin],
    getInitialState: function () {
        return {
            columns: all_columns,
            start: 0,
            stop: 0
        };
    },
    componentWillMount: function () {
        if (this.props.view) {
            this.props.view.addListener("add update remove recalculate", this.onChange);
        }
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.view !== this.props.view) {
            if (this.props.view) {
                this.props.view.removeListener("add update remove recalculate");
            }
            nextProps.view.addListener("add update remove recalculate", this.onChange);
        }
    },
    componentDidMount: function () {
        this.onScroll();
    },
    onScroll: function () {
        this.adjustHead();

        var viewport = this.getDOMNode();
        var top = viewport.scrollTop;
        var height = viewport.offsetHeight;
        var start = Math.floor(top / ROW_HEIGHT);
        var stop = start + Math.ceil(height / ROW_HEIGHT);
        this.setState({
            start: start,
            stop: stop
        });
    },
    onChange: function () {
        console.log("onChange");
        this.forceUpdate();
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
        var space_top = 0, space_bottom = 0, fix_nth_row = null;
        var rows = [];
        if (this.props.view) {
            var flows = this.props.view.flows;
            var max = Math.min(flows.length, this.state.stop);
            console.log("render", this.props.view.flows.length, this.state.start, max - this.state.start, flows.length - this.state.stop);

            for (var i = this.state.start; i < max; i++) {
                var flow = flows[i];
                var selected = (flow === this.props.selected);
                rows.push(
                    <FlowRow key={flow.id}
                        ref={flow.id}
                        flow={flow}
                        columns={this.state.columns}
                        selected={selected}
                        selectFlow={this.props.selectFlow}
                    />
                );
            }

            space_top = this.state.start * ROW_HEIGHT;
            space_bottom = Math.max(0, flows.length - this.state.stop) * ROW_HEIGHT;
            if(this.state.start % 2 === 1){
                fix_nth_row = <tr></tr>;
            }
        }


        return (
            <div className="flow-table" onScroll={this.onScroll}>
                <table>
                    <FlowTableHead ref="head"
                        columns={this.state.columns}/>
                    <tbody>
                        <tr style={{height: space_top}}></tr>
                        { fix_nth_row }
                        {rows}
                        <tr style={{height: space_bottom}}></tr>
                    </tbody>
                </table>
            </div>
        );
    }
});

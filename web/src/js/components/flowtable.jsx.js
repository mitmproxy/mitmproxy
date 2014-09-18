/** @jsx React.DOM */

var FlowRow = React.createClass({
    render: function(){
        var flow = this.props.flow;
        var columns = this.props.columns.map(function(column){
            return column({
                key: column.displayName,
                flow: flow
            });
        }.bind(this));
        var className = "";
        if(this.props.selected){
            className += "selected";
        }
        return (
            <tr className={className} onClick={this.props.selectFlow.bind(null, flow)}>
                {columns}
            </tr>);
    }
});

var FlowTableHead = React.createClass({
    render: function(){
        var columns = this.props.columns.map(function(column){
            return column.renderTitle();
        }.bind(this));
        return <thead>{columns}</thead>;
    }
});

var FlowTableBody = React.createClass({
    render: function(){
        var rows = this.props.flows.map(function(flow){
            var selected = (flow == this.props.selected);
            return <FlowRow key={flow.id}
                            ref={flow.id}
                            flow={flow}
                            columns={this.props.columns}
                            selected={selected}
                            selectFlow={this.props.selectFlow}
                            />;
        }.bind(this));
        return <tbody onKeyDown={this.props.onKeyDown} tabIndex="0">{rows}</tbody>;
    }
});


var FlowTable = React.createClass({
    getInitialState: function () {
        return {
            flows: [],
            columns: all_columns
        };
    },
    componentDidMount: function () {
        this.flowStore = FlowStore.getView();
        this.flowStore.addListener("change",this.onFlowChange);
    },
    componentWillUnmount: function () {
        this.flowStore.removeListener("change",this.onFlowChange);
        this.flowStore.close();
    },
    onFlowChange: function () {
        this.setState({
            flows: this.flowStore.getAll()
        });
    },
    selectFlow: function(flow){
        this.setState({
            selected: flow
        });

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

        if(flowNode_top < viewport_top){
            viewport.scrollTop = flowNode_top;
        } else if(flowNode_bottom > viewport_bottom) {
            viewport.scrollTop = flowNode_bottom - viewport.offsetHeight;
        }
    },
    selectRowRelative: function(i){
        var index;
        if(!this.state.selected){
            if(i > 0){
                index = this.flows.length-1;
            } else {
                index = 0;
            }
        } else {
            index = _.findIndex(this.state.flows, function(f){
                return f === this.state.selected;
            }.bind(this));
            index = Math.min(Math.max(0, index+i), this.state.flows.length-1);
        }
        this.selectFlow(this.state.flows[index]);
    },
    onKeyDown: function(e){
        switch(e.keyCode){
            case Key.DOWN:
                this.selectRowRelative(+1);
                return false;
                break;
            case Key.UP:
                this.selectRowRelative(-1);
                return false;
                break;
            case Key.ENTER:
                console.log("Open details pane...", this.state.selected);
                break;
            case Key.ESC:
                console.log("")
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        return false;
    },
    onScroll: function(e){
        //Abusing CSS transforms to set thead into position:fixed.
        var head = this.refs.head.getDOMNode();
        head.style.transform = "translate(0,"+this.getDOMNode().scrollTop+"px)";
    },
    render: function () {
        var flows = this.state.flows.map(function(flow){
         return <div>{flow.request.method} {flow.request.scheme}://{flow.request.host}{flow.request.path}</div>;
        });
        return (
        <main onScroll={this.onScroll}>
            <table className="flow-table">
                <FlowTableHead ref="head"
                               columns={this.state.columns}/>
                <FlowTableBody ref="body"
                               selectFlow={this.selectFlow}
                               onKeyDown={this.onKeyDown}
                               selected={this.state.selected}
                               columns={this.state.columns}
                               flows={this.state.flows}/>
            </table>
        </main>
            );
    }
});

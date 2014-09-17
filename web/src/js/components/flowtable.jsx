/** @jsx React.DOM */

var FlowRow = React.createClass({
    render: function(){
        var flow = this.props.flow;
        var columns = this.props.columns.map(function(column){
            return column({flow: flow});
        }.bind(this));
        return <tr>{columns}</tr>;
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
            return <FlowRow flow={flow} columns={this.props.columns}/>
        }.bind(this));
        return <tbody>{rows}</tbody>;
    }
});

var PathColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="PathColumn">Path</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        return <td key="PathColumn">{flow.request.scheme + "://" + flow.request.host + flow.request.path}</td>;
    }
});
var MethodColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="MethodColumn">Method</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        return <td key="MethodColumn">{flow.request.method}</td>;
    }
});
var StatusColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="StatusColumn">Status</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        var status;
        if(flow.response){
            status = flow.response.code + " " + flow.response.msg;
        } else {
            status = null;
        }
        return <td key="StatusColumn">{status}</td>;
    }
});
var TimeColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="TimeColumn">Time</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        var time;
        if(flow.response){
            time = Math.round(1000 * (flow.response.timestamp_end - flow.request.timestamp_start))+"ms";
        } else {
            time = "...";
        }
        return <td key="TimeColumn">{time}</td>;
    }
});

var all_columns = [PathColumn, MethodColumn, StatusColumn, TimeColumn];

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
    render: function () {
        var flows = this.state.flows.map(function(flow){
         return <div>{flow.request.method} {flow.request.scheme}://{flow.request.host}{flow.request.path}</div>;
        });
        return (
            <table className="flow-table">
                <FlowTableHead columns={this.state.columns}/>
                <FlowTableBody columns={this.state.columns} flows={this.state.flows}/>
            </table>
            );
    }
});

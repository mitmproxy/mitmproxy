/** @jsx React.DOM */

var TrafficTable = React.createClass({
    getInitialState: function() {
        return {
            flows: []
        };
    },
    componentDidMount: function() {
        //this.flowStore = FlowStore.getView();
        //this.flowStore.addListener("change",this.onFlowChange);
    },
    componentWillUnmount: function() {
        //this.flowStore.removeListener("change",this.onFlowChange);
        //this.flowStore.close();
    },
    onFlowChange: function() {
        this.setState({
            //flows: this.flowStore.getAll()
        });
    },
    render: function() {
        /*var flows = this.state.flows.map(function(flow){
        return <div>{flow.request.method} {flow.request.scheme}://{flow.request.host}{flow.request.path}</div>;
        }); */
        //Dummy Text for layout testing
        x = "Flow";
        i = 12;
        while (i--) x += x;
        return ( 
            <div>Flow</div> 
        );
    }
});

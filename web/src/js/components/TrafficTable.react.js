/** @jsx React.DOM */

var TrafficTable = React.createClass({
    getInitialState() {
        return {
            flows: []
        };
    },
    componentDidMount() {
        //this.flowStore = FlowStore.getView();
        //this.flowStore.addListener("change",this.onFlowChange);
    },
    componentWillUnmount() {
        //this.flowStore.removeListener("change",this.onFlowChange);
        //this.flowStore.close();
    },
    onFlowChange() {
        this.setState({
            //flows: this.flowStore.getAll()
        });
    },
    render() {
        /*var flows = this.state.flows.map(function(flow){
        return <div>{flow.request.method} {flow.request.scheme}://{flow.request.host}{flow.request.path}</div>;
        }); */
        //Dummy Text for layout testing
        x = "Flow";
        i = 12;
        while (i--) x += x;
        return ( 
            <div><pre> { x } </pre></div> 
        );
    }
});
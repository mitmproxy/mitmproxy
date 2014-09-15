/** @jsx React.DOM */

var TrafficTable = React.createClass({
    /*getInitialState: function(){
        return {
            flows: []
        };
    },*/
    componentDidMount: function () {
        /*var flowStore = new DummyFlowStore([]);
        this.setState({flowStore: flowStore});

        flowStore.addChangeListener(this.onFlowsChange);

        $.getJSON("/flows.json").success(function (flows) {
            flows.forEach(function (flow, i) {
                window.setTimeout(function () {
                    flowStore.addFlow(flow);
                }, _.random(i*400,i*400+1000));
            });
        }.bind(this));*/
    },
    componentWillUnmount: function(){
        //this.state.flowStore.close();
    },
    onFlowsChange: function(event, flows){
        //this.setState({flows: flows.getAll()});
    },
    render: function () {
       /*var flows = this.state.flows.map(function(flow){
           return <div>{flow.request.method} {flow.request.scheme}://{flow.request.host}{flow.request.path}</div>;
       }); *//**/
       x = "WTF";
       i = 12;
       while(i--) x += x;
       return <div><pre>{x}</pre></div>;
   }
});
/** @jsx React.DOM */

var MainView = React.createClass({
    getInitialState: function() {
        return {
            flows: [],
        };
    },
    componentDidMount: function () {
        console.log("get view");
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
    selectFlow: function(flow) {
        if(flow){
            ReactRouter.replaceWith(
                "flow", 
                {
                    flowId: flow.id,
                    detailTab: this.props.params.detailTab || "request"
                }
            );
            this.refs.flowTable.scrollIntoView(flow);
        } else {
            ReactRouter.replaceWith("flows");
        }
    },
    selectDetailTab: function(panel) {
        ReactRouter.replaceWith(
            "flow", 
            {
                flowId: this.props.params.flowId,
                detailTab: panel
            }
        );
    },
    render: function() {
        var selected = _.find(this.state.flows, { id: this.props.params.flowId });

        var details = null;
        if(selected){
            details = (
                <FlowDetail ref="flowDetails" 
                            flow={selected}
                            selectTab={this.selectDetailTab}
                            active={this.props.params.detailTab}/>
            );
        }

        return (
            <div className="main-view">
                <FlowTable ref="flowTable"
                           flows={this.state.flows}
                           selectFlow={this.selectFlow}
                           selected={selected} />
                {details}
            </div>
        );
    }
});
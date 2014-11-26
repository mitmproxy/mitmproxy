/** @jsx React.DOM */

var MainView = React.createClass({
    getInitialState: function() {
        return {
            flows: [],
        };
    },
    componentDidMount: function () {
        //FIXME: The store should be global, move out of here.
        window.flowstore = new LiveFlowStore();

        this.flowStore = window.flowstore.open_view();
        this.flowStore.addListener("add",this.onFlowChange);
        this.flowStore.addListener("update",this.onFlowChange);
        this.flowStore.addListener("remove",this.onFlowChange);
        this.flowStore.addListener("recalculate",this.onFlowChange);
    },
    componentWillUnmount: function () {
        this.flowStore.removeListener("change",this.onFlowChange);
        this.flowStore.close();
    },
    onFlowChange: function () {
        this.setState({
            flows: this.flowStore.flows
        });
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
    selectFlowRelative: function(i){
        var index;
        if(!this.props.params.flowId){
            if(i > 0){
                index = this.state.flows.length-1;
            } else {
                index = 0;
            }
        } else {
            index = _.findIndex(this.state.flows, function(f){
                return f.id === this.props.params.flowId;
            }.bind(this));
            index = Math.min(Math.max(0, index+i), this.state.flows.length-1);
        }
        this.selectFlow(this.state.flows[index]);
    },
    onKeyDown: function(e){
        switch(e.keyCode){
            case Key.K:
            case Key.UP:
                this.selectFlowRelative(-1);
                break;
            case Key.J:
            case Key.DOWN:
                this.selectFlowRelative(+1);
                break;
            case Key.SPACE:
            case Key.PAGE_DOWN:
                this.selectFlowRelative(+10);
                break;
            case Key.PAGE_UP:
                this.selectFlowRelative(-10);
                break;
            case Key.ESC:
                this.selectFlow(null);
                break;
            case Key.H:
            case Key.LEFT:
                if(this.refs.flowDetails){
                    this.refs.flowDetails.nextTab(-1);
                }
                break;
            case Key.L:
            case Key.TAB:
            case Key.RIGHT:
                if(this.refs.flowDetails){
                    this.refs.flowDetails.nextTab(+1);
                }
                break;
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        return false;
    },
    render: function() {
        var selected = _.find(this.state.flows, { id: this.props.params.flowId });

        var details;
        if(selected){
            details = (
                <FlowDetail ref="flowDetails" 
                            flow={selected}
                            selectTab={this.selectDetailTab}
                            active={this.props.params.detailTab}/>
            );
        } else {
            details = null;
        }

        return (
            <div className="main-view" onKeyDown={this.onKeyDown} tabIndex="0">
                <FlowTable ref="flowTable"
                           flows={this.state.flows}
                           selectFlow={this.selectFlow}
                           selected={selected} />
                { details ? <Splitter/> : null }
                {details}
            </div>
        );
    }
});
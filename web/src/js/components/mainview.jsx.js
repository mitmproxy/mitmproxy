var MainView = React.createClass({
    mixins: [ReactRouter.Navigation, ReactRouter.State],
    getInitialState: function () {
        return {
            flows: []
        };
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.flowStore !== this.props.flowStore) {
            this.closeView();
            this.openView(nextProps.flowStore);
        }
    },
    openView: function (store) {
        var view = new FlowView(store);
        this.setState({
            view: view
        });
    },
    closeView: function () {
        this.state.view.close();
    },
    componentWillMount: function () {
        this.openView(this.props.flowStore);
    },
    componentWillUnmount: function () {
        this.closeView();
    },
    selectFlow: function (flow) {
        if (flow) {
            this.replaceWith(
                "flow",
                {
                    flowId: flow.id,
                    detailTab: this.getParams().detailTab || "request"
                }
            );
            console.log("TODO: Scroll into view");
            //this.refs.flowTable.scrollIntoView(flow);
        } else {
            this.replaceWith("flows");
        }
    },
    selectFlowRelative: function (shift) {
        var flows = this.state.view.flows;
        var index;
        if (!this.getParams().flowId) {
            if (shift > 0) {
                index = flows.length - 1;
            } else {
                index = 0;
            }
        } else {
            var currFlowId = this.getParams().flowId;
            var i = flows.length;
            while (i--) {
                if (flows[i].id === currFlowId) {
                    index = i;
                    break;
                }
            }
            index = Math.min(
                Math.max(0, index + shift),
                flows.length - 1);
        }
        this.selectFlow(flows[index]);
    },
    onKeyDown: function (e) {
        switch (e.keyCode) {
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
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(-1);
                }
                break;
            case Key.L:
            case Key.TAB:
            case Key.RIGHT:
                if (this.refs.flowDetails) {
                    this.refs.flowDetails.nextTab(+1);
                }
                break;
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        e.preventDefault();
    },
    render: function () {
        var selected = this.props.flowStore.get(this.getParams().flowId);

        var details;
        if (selected) {
            details = (
                <FlowDetail ref="flowDetails"
                    flow={selected}
                    active={this.getParams().detailTab}/>
            );
        } else {
            details = null;
        }

        return (
            <div className="main-view" onKeyDown={this.onKeyDown} tabIndex="0">
                <FlowTable ref="flowTable"
                    view={this.state.view}
                    selectFlow={this.selectFlow}
                    selected={selected} />
                { details ? <Splitter/> : null }
                {details}
            </div>
        );
    }
});
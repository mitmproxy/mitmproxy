var React = require("react");
var _ = require("lodash");

var common = require("../common.js");
var Nav = require("./nav.js");
var Messages = require("./messages.js");
var Details = require("./details.js");
var Prompt = require("../prompt.js");


var allTabs = {
    request: Messages.Request,
    response: Messages.Response,
    error: Messages.Error,
    details: Details
};

var FlowView = React.createClass({
    mixins: [common.StickyHeadMixin, common.Navigation, common.RouterState],
    getInitialState: function () {
        return {
            prompt: false
        };
    },
    getTabs: function (flow) {
        var tabs = [];
        ["request", "response", "error"].forEach(function (e) {
            if (flow[e]) {
                tabs.push(e);
            }
        });
        tabs.push("details");
        return tabs;
    },
    nextTab: function (i) {
        var tabs = this.getTabs(this.props.flow);
        var currentIndex = tabs.indexOf(this.getActive());
        // JS modulo operator doesn't correct negative numbers, make sure that we are positive.
        var nextIndex = (currentIndex + i + tabs.length) % tabs.length;
        this.selectTab(tabs[nextIndex]);
    },
    selectTab: function (panel) {
        this.replaceWith(
            "flow",
            {
                flowId: this.getParams().flowId,
                detailTab: panel
            }
        );
    },
    getActive: function(){
        return this.getParams().detailTab;
    },
    promptEdit: function () {
        var options;
        switch(this.getActive()){
            case "request":
                options = [
                    "method",
                    "url",
                    {text:"http version", key:"v"},
                    "header"
                    /*, "content"*/];
                break;
            case "response":
                options = [
                    {text:"http version", key:"v"},
                    "code",
                    "message",
                    "header"
                    /*, "content"*/];
                break;
            case "details":
                return;
            default:
                throw "Unknown tab for edit: " + this.getActive();
        }

        this.setState({
            prompt: {
                done: function (k) {
                    this.setState({prompt: false});
                    if(k){
                        this.refs.tab.edit(k);
                    }
                }.bind(this),
                options: options
            }
        });
    },
    render: function () {
        var flow = this.props.flow;
        var tabs = this.getTabs(flow);
        var active = this.getActive();

        if (!_.contains(tabs, active)) {
            if (active === "response" && flow.error) {
                active = "error";
            } else if (active === "error" && flow.response) {
                active = "response";
            } else {
                active = tabs[0];
            }
            this.selectTab(active);
        }

        var prompt = null;
        if (this.state.prompt) {
            prompt = <Prompt {...this.state.prompt}/>;
        }

        var Tab = allTabs[active];
        return (
            <div className="flow-detail" onScroll={this.adjustHead}>
                <Nav ref="head"
                    flow={flow}
                    tabs={tabs}
                    active={active}
                    selectTab={this.selectTab}/>
                <Tab ref="tab" flow={flow}/>
                {prompt}
            </div>
        );
    }
});

module.exports = FlowView;
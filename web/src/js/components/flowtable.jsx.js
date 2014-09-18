/** @jsx React.DOM */

var FlowRow = React.createClass({
    render: function(){
        var flow = this.props.flow;
        var columns = this.props.columns.map(function(column){
            return <column key={column.displayName} flow={flow}/>;
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
        return <thead><tr>{columns}</tr></thead>;
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
    mixins: [StickyHeadMixin, AutoScrollMixin],
    getInitialState: function () {
        return {
            columns: all_columns
        };
    },
    scrollIntoView: function(flow){
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
    selectFlowRelative: function(i){
        var index;
        if(!this.props.selected){
            if(i > 0){
                index = this.props.flows.length-1;
            } else {
                index = 0;
            }
        } else {
            index = _.findIndex(this.props.flows, function(f){
                return f === this.props.selected;
            }.bind(this));
            index = Math.min(Math.max(0, index+i), this.props.flows.length-1);
        }
        this.props.selectFlow(this.props.flows[index]);
    },
    onKeyDown: function(e){
        switch(e.keyCode){
            case Key.DOWN:
                this.selectFlowRelative(+1);
                break;
            case Key.UP:
                this.selectFlowRelative(-1);
                break;
            case Key.PAGE_DOWN:
                this.selectFlowRelative(+10);
                break;
            case Key.PAGE_UP:
                this.selectFlowRelative(-10);
                break;
            case Key.ESC:
                this.props.selectFlow(null);
                break;
            default:
                console.debug("keydown", e.keyCode);
                return;
        }
        return false;
    },
    render: function () {
        return (
            <div className="flow-table" onScroll={this.adjustHead}>
                <table>
                    <FlowTableHead ref="head"
                                   columns={this.state.columns}/>
                    <FlowTableBody ref="body"
                                   flows={this.props.flows}
                                   selected={this.props.selected}
                                   selectFlow={this.props.selectFlow}
                                   columns={this.state.columns}
                                   onKeyDown={this.onKeyDown}/>
                </table>
            </div>
            );
    }
});

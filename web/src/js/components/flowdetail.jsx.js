/** @jsx React.DOM */

var FlowDetailNav = React.createClass({
    render: function(){

        var items = ["request", "response", "details"].map(function(e){
            var str = e.charAt(0).toUpperCase() + e.slice(1);
            var className = this.props.active === e ? "active" : "";
            var onClick = function(){
                this.props.selectTab(e);
                return false;
            }.bind(this);
            return <a key={e}
                      href="#" 
                      className={className}
                      onClick={onClick}>{str}</a>;
        }.bind(this));
        return (
            <nav ref="head" className="nav-tabs nav-tabs-sm">
                {items}
            </nav>
        );
    } 
});

var FlowDetailRequest = React.createClass({
    render: function(){
        return <div>request</div>;
    }
});

var FlowDetailResponse = React.createClass({
    render: function(){
        return <div>response</div>;
    }
});

var FlowDetailConnectionInfo = React.createClass({
    render: function(){
        return <div>details</div>;
    }
})

var tabs = {
    request: FlowDetailRequest,
    response: FlowDetailResponse,
    details: FlowDetailConnectionInfo
}

var FlowDetail = React.createClass({
    mixins: [StickyHeadMixin],
    render: function(){
        var flow = JSON.stringify(this.props.flow, null, 2);
        var Tab = tabs[this.props.active];
        return (
            <div className="flow-detail" onScroll={this.adjustHead}>
                <FlowDetailNav active={this.props.active} selectTab={this.props.selectTab}/>
                <Tab/>
            </div>
            );
    } 
});
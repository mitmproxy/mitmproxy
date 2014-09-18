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

var Headers = React.createClass({
    render: function(){
        var rows = this.props.message.headers.map(function(header){
            return (
                <tr>
                    <td className="header-name">{header[0]}</td>
                    <td className="header-value">{header[1]}</td>
                </tr>
            );
        })
        return (
            <table className="header-table">
                <tbody>
                    {rows}
                </tbody>
            </table>
        );
    }
})

var FlowDetailRequest = React.createClass({
    render: function(){
        var flow = this.props.flow;
        var first_line = [
                flow.request.method,
                RequestUtils.pretty_url(flow.request),
                "HTTP/"+ flow.response.httpversion.join(".")
            ].join(" ");
        var content = null;
        if(flow.request.contentLength > 0){
            content = "Request Content Size: "+ formatSize(flow.request.contentLength);
        } else {
            content = <div className="alert alert-info">No Content</div>;
        }

        //TODO: Styling

        return (
            <section>
                <code>{ first_line }</code>
                <Headers message={flow.request}/>
                <hr/>
                {content}
            </section>
        );
    }
});

var FlowDetailResponse = React.createClass({
    render: function(){
        var flow = this.props.flow;
        var first_line = [
                "HTTP/"+ flow.response.httpversion.join("."),
                flow.response.code,
                flow.response.msg
            ].join(" ");
        var content = null;
        if(flow.response.contentLength > 0){
            content = "Response Content Size: "+ formatSize(flow.response.contentLength);
        } else {
            content = <div className="alert alert-info">No Content</div>;
        }

        //TODO: Styling

        return (
            <section>
                <code>{ first_line }</code>
                <Headers message={flow.response}/>
                <hr/>
                {content}
            </section>
        );
    }
});

var FlowDetailConnectionInfo = React.createClass({
    render: function(){
        return <section>details</section>;
    }
});

var tabs = {
    request: FlowDetailRequest,
    response: FlowDetailResponse,
    details: FlowDetailConnectionInfo
};

var FlowDetail = React.createClass({
    mixins: [StickyHeadMixin],
    render: function(){
        var flow = JSON.stringify(this.props.flow, null, 2);
        var Tab = tabs[this.props.active];
        return (
            <div className="flow-detail" onScroll={this.adjustHead}>
                <FlowDetailNav ref="head" active={this.props.active} selectTab={this.props.selectTab}/>
                <Tab flow={this.props.flow}/>
            </div>
            );
    } 
});
/** @jsx React.DOM */


var TLSColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="tls" className="col-tls"></th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        var ssl = (flow.request.scheme == "https");
        return <td className={ssl ? "col-tls-https" : "col-tls-http"}></td>;
    }
});


var IconColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="icon" className="col-icon"></th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        return <td className="resource-icon resource-icon-plain"></td>;
    }
});

var PathColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="path" className="col-path">Path</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        return <td>{flow.request.scheme + "://" + flow.request.host + flow.request.path}</td>;
    }
});


var MethodColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="method" className="col-method">Method</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        return <td>{flow.request.method}</td>;
    }
});


var StatusColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="status" className="col-status">Status</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        var status;
        if(flow.response){
            status = flow.response.code;
        } else {
            status = null;
        }
        return <td>{status}</td>;
    }
});


var TimeColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="time" className="col-time">Time</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        var time;
        if(flow.response){
            time = Math.round(1000 * (flow.response.timestamp_end - flow.request.timestamp_start))+"ms";
        } else {
            time = "...";
        }
        return <td>{time}</td>;
    }
});


var all_columns = [TLSColumn, IconColumn, PathColumn, MethodColumn, StatusColumn, TimeColumn];


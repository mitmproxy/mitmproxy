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
        var classes = React.addons.classSet({
            "col-tls": true,
            "col-tls-https": ssl,
            "col-tls-http": !ssl
        });
        return <td className={classes}></td>;
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
        return <td className="col-icon"><div className="resource-icon resource-icon-plain"></div></td>;
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
        return <td className="col-path">{flow.request.scheme + "://" + flow.request.host + flow.request.path}</td>;
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
        return <td className="col-method">{flow.request.method}</td>;
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
        return <td className="col-status">{status}</td>;
    }
});


var SizeColumn = React.createClass({
    statics: {
        renderTitle: function(){
            return <th key="size" className="col-size">Size</th>;
        }
    },
    render: function(){
        var flow = this.props.flow;
        var size = formatSize(
                flow.request.contentLength +
                (flow.response.contentLength || 0));
        return <td className="col-size">{size}</td>;
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
        return <td className="col-time">{time}</td>;
    }
});


var all_columns = [
    TLSColumn,
    IconColumn,
    PathColumn,
    MethodColumn,
    StatusColumn,
    SizeColumn,
    TimeColumn];


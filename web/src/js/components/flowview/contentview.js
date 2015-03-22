var React = require("react");
var _ = require("lodash");

var MessageUtils = require("../../flow/utils.js").MessageUtils;
var utils = require("../../utils.js");

var image_regex = /^image\/(png|jpe?g|gif|vnc.microsoft.icon|x-icon)$/i;
var Image = React.createClass({
    statics: {
        matches: function (message) {
            return image_regex.test(MessageUtils.getContentType(message));
        }
    },
    render: function () {
        var message_name = this.props.flow.request === this.props.message ? "request" : "response";
        var url = "/flows/" + this.props.flow.id + "/" + message_name + "/content";
        return <div className="flowview-image">
            <img src={url} alt="preview" className="img-thumbnail"/>
        </div>;
    }
});

var Raw = React.createClass({
    statics: {
        matches: function (message) {
            return true;
        }
    },
    render: function () {
        //FIXME
        return <div>raw</div>;
    }
});


var Auto = React.createClass({
    statics: {
        matches: function () {
            return false; // don't match itself
        },
        findView: function (message) {
            for (var i = 0; i < all.length; i++) {
                if (all[i].matches(message)) {
                    return all[i];
                }
            }
            return all[all.length - 1];
        }
    },
    render: function () {
        var View = Auto.findView(this.props.message);
        return <View {...this.props}/>;
    }
});

var all = [Auto, Image, Raw];


var ContentEmpty = React.createClass({
    render: function () {
        var message_name = this.props.flow.request === this.props.message ? "request" : "response";
        return <div className="alert alert-info">No {message_name} content.</div>;
    }
});

var ContentMissing = React.createClass({
    render: function () {
        var message_name = this.props.flow.request === this.props.message ? "Request" : "Response";
        return <div className="alert alert-info">{message_name} content missing.</div>;
    }
});

var TooLarge = React.createClass({
    render: function () {
        var size = utils.formatSize(this.props.message.contentLength);
        return <div className="alert alert-warning">
            <button onClick={this.props.onClick} className="btn btn-xs btn-warning pull-right">Display anyway</button>
            {size} content size.
        </div>;
    }
});

var ViewSelector = React.createClass({
    render: function () {
        var views = [];
        for (var i = 0; i < all.length; i++) {
            var view = all[i];
            var className = "btn btn-default";
            if (view === this.props.active) {
                className += " active";
            }
            var text;
            if (view === Auto) {
                text = "auto: " + Auto.findView(this.props.message).displayName.toLowerCase();
            } else {
                text = view.displayName.toLowerCase();
            }
            views.push(
                <button
                    key={view.displayName}
                    onClick={this.props.selectView.bind(null, view)}
                    className={className}>
                    {text}
                </button>
            );
        }

        return <div className="view-selector btn-group btn-group-xs">{views}</div>;
    }
});

var ContentView = React.createClass({
    getInitialState: function () {
        return {
            displayLarge: false,
            View: Auto
        };
    },
    propTypes: {
        // It may seem a bit weird at the first glance:
        // Every view takes the flow and the message as props, e.g.
        // <Auto flow={flow} message={flow.request}/>
        flow: React.PropTypes.object.isRequired,
        message: React.PropTypes.object.isRequired,
    },
    selectView: function (view) {
        this.setState({
            View: view
        });
    },
    displayLarge: function () {
        this.setState({displayLarge: true});
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.message !== this.props.message) {
            this.setState(this.getInitialState());
        }
    },
    render: function () {
        var message = this.props.message;
        if (message.contentLength === 0) {
            return <ContentEmpty {...this.props}/>;
        } else if (message.contentLength === null) {
            return <ContentMissing {...this.props}/>;
        } else if (message.contentLength > 1024 * 1024 * 3 && !this.state.displayLarge) {
            return <TooLarge {...this.props} onClick={this.displayLarge}/>;
        }

        return <div>
            <this.state.View {...this.props} />
            <div className="text-center">
                <ViewSelector selectView={this.selectView} active={this.state.View} message={message}/>
            </div>
        </div>;
    }
});

module.exports = ContentView;
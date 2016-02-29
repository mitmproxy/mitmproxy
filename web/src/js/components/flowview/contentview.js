import React from "react";
import _ from "lodash";

import {MessageUtils} from "../../flow/utils.js";
import {formatSize} from "../../utils.js";

var image_regex = /^image\/(png|jpe?g|gif|vnc.microsoft.icon|x-icon)$/i;
var ViewImage = React.createClass({
    statics: {
        matches: function (message) {
            return image_regex.test(MessageUtils.getContentType(message));
        }
    },
    render: function () {
        var url = MessageUtils.getContentURL(this.props.flow, this.props.message);
        return <div className="flowview-image">
            <img src={url} alt="preview" className="img-thumbnail"/>
        </div>;
    }
});

var RawMixin = {
    getInitialState: function () {
        return {
            content: undefined,
            request: undefined
        }
    },
    requestContent: function (nextProps) {
        if (this.state.request) {
            this.state.request.abort();
        }
        var request = MessageUtils.getContent(nextProps.flow, nextProps.message);
        this.setState({
            content: undefined,
            request: request
        });
        request.done(function (data) {
            this.setState({content: data});
        }.bind(this)).fail(function (jqXHR, textStatus, errorThrown) {
            if (textStatus === "abort") {
                return;
            }
            this.setState({content: "AJAX Error: " + textStatus + "\r\n" + errorThrown});
        }.bind(this)).always(function () {
            this.setState({request: undefined});
        }.bind(this));

    },
    componentWillMount: function () {
        this.requestContent(this.props);
    },
    componentWillReceiveProps: function (nextProps) {
        if (nextProps.message !== this.props.message) {
            this.requestContent(nextProps);
        }
    },
    componentWillUnmount: function () {
        if (this.state.request) {
            this.state.request.abort();
        }
    },
    render: function () {
        if (!this.state.content) {
            return <div className="text-center">
                <i className="fa fa-spinner fa-spin"></i>
            </div>;
        }
        return this.renderContent();
    }
};

var ViewRaw = React.createClass({
    mixins: [RawMixin],
    statics: {
        matches: function (message) {
            return true;
        }
    },
    renderContent: function () {
        return <pre>{this.state.content}</pre>;
    }
});

var json_regex = /^application\/json$/i;
var ViewJSON = React.createClass({
    mixins: [RawMixin],
    statics: {
        matches: function (message) {
            return json_regex.test(MessageUtils.getContentType(message));
        }
    },
    renderContent: function () {
        var json = this.state.content;
        try {
            json = JSON.stringify(JSON.parse(json), null, 2);
        } catch (e) {
        }
        return <pre>{json}</pre>;
    }
});

var ViewAuto = React.createClass({
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
        var View = ViewAuto.findView(this.props.message);
        return <View {...this.props}/>;
    }
});

var all = [ViewAuto, ViewImage, ViewJSON, ViewRaw];


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
    statics: {
        isTooLarge: function (message) {
            var max_mb = ViewImage.matches(message) ? 10 : 0.2;
            return message.contentLength > 1024 * 1024 * max_mb;
        }
    },
    render: function () {
        var size = formatSize(this.props.message.contentLength);
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
            if (view === ViewAuto) {
                text = "auto: " + ViewAuto.findView(this.props.message).displayName.toLowerCase().replace("view", "");
            } else {
                text = view.displayName.toLowerCase().replace("view", "");
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
            View: ViewAuto
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
        } else if (!this.state.displayLarge && TooLarge.isTooLarge(message)) {
            return <TooLarge {...this.props} onClick={this.displayLarge}/>;
        }

        var downloadUrl = MessageUtils.getContentURL(this.props.flow, message);

        return <div>
            <this.state.View {...this.props} />
            <div className="view-options text-center">
                <ViewSelector selectView={this.selectView} active={this.state.View} message={message}/>
            &nbsp;
                <a className="btn btn-default btn-xs" href={downloadUrl}>
                    <i className="fa fa-download"/>
                </a>
            </div>
        </div>;
    }
});

export default ContentView;
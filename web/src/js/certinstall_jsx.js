/** @jsx React.DOM */

var CertInstallView = React.createClass({displayName: 'CertInstallView',
    render: function () {
        return React.DOM.div({className: "certinstall"}, 
            React.DOM.h2(null, " Click to install the mitmproxy certificate: "), 
            React.DOM.div({id: "certbank", className: "row"}, 
                React.DOM.div({className: "col-md-3"}, 
                    React.DOM.a({href: "/cert/pem"}, React.DOM.i({className: "fa fa-apple fa-5x"})), 
                    React.DOM.p(null, "Apple")
                ), 
                React.DOM.div({className: "col-md-3"}, 
                    React.DOM.a({href: "/cert/p12"}, React.DOM.i({className: "fa fa-windows fa-5x"})), 
                    React.DOM.p(null, "Windows")
                ), 
                React.DOM.div({className: "col-md-3"}, 
                    React.DOM.a({href: "/cert/pem"}, React.DOM.i({className: "fa fa-android fa-5x"})), 
                    React.DOM.p(null, "Android")
                ), 
                React.DOM.div({className: "col-md-3"}, 
                    React.DOM.a({href: "/cert/pem"}, React.DOM.i({className: "fa fa-asterisk fa-5x"})), 
                    React.DOM.p(null, "Other")
                )
            )
        );
    }
});

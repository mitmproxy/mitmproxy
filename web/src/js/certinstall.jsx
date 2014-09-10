/** @jsx React.DOM */

var CertInstallView = React.createClass({
    render: function () {
        return <div className="certinstall">
            <h2> Click to install the mitmproxy certificate: </h2>
            <div id="certbank" className="row">
                <div className="col-md-3">
                    <a href="/cert/pem"><i className="fa fa-apple fa-5x"></i></a>
                    <p>Apple</p>
                </div>
                <div className="col-md-3">
                    <a href="/cert/p12"><i className="fa fa-windows fa-5x"></i></a>
                    <p>Windows</p>
                </div>
                <div className="col-md-3">
                    <a href="/cert/pem"><i className="fa fa-android fa-5x"></i></a>
                    <p>Android</p>
                </div>
                <div className="col-md-3">
                    <a href="/cert/pem"><i className="fa fa-asterisk fa-5x"></i></a>
                    <p>Other</p>
                </div>
            </div>
        </div>;
    }
});

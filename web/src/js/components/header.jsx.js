var MainMenu = React.createClass({
    statics: {
        title: "Traffic",
        route: "flows"
    },
    toggleEventLog: function () {
        SettingsActions.update({
            showEventLog: !this.props.settings.showEventLog
        });
    },
    clearFlows: function(){
        $.post("/flows/clear");
    },
    render: function () {
        return (
            <div>
                <button className={"btn " + (this.props.settings.showEventLog ? "btn-primary" : "btn-default")} onClick={this.toggleEventLog}>
                    <i className="fa fa-database"></i>&nbsp;Display Event Log
                </button>&nbsp;
                <button className="btn btn-default" onClick={this.clearFlows}>
                    <i className="fa fa-eraser"></i>&nbsp;Clear Flows
                </button>
            </div>
        );
    }
});


var ToolsMenu = React.createClass({
    statics: {
        title: "Tools",
        route: "flows"
    },
    render: function () {
        return <div>Tools Menu</div>;
    }
});


var ReportsMenu = React.createClass({
    statics: {
        title: "Visualization",
        route: "reports"
    },
    render: function () {
        return <div>Reports Menu</div>;
    }
});


var header_entries = [MainMenu, ToolsMenu, ReportsMenu];


var Header = React.createClass({
    mixins: [ReactRouter.Navigation],
    getInitialState: function () {
        return {
            active: header_entries[0]
        };
    },
    handleClick: function (active, e) {
        e.preventDefault();
        this.transitionTo(active.route);
        this.setState({active: active});
    },
    handleFileClick: function () {
        console.log("File click");
    },
    render: function () {
        var header = header_entries.map(function (entry, i) {
            var classes = React.addons.classSet({
                active: entry == this.state.active
            });
            return (
                <a key={i}
                    href="#"
                    className={classes}
                    onClick={this.handleClick.bind(this, entry)}
                >
                    { entry.title}
                </a>
            );
        }.bind(this));

        return (
            <header>
                <div className="title-bar">
                mitmproxy { this.props.settings.version }
                </div>
                <nav className="nav-tabs nav-tabs-lg">
                    <a href="#" className="special" onClick={this.handleFileClick}> File </a>
                    {header}
                </nav>
                <div className="menu">
                    <this.state.active settings={this.props.settings}/>
                </div>
            </header>
        );
    }
});

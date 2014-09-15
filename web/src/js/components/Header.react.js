/** @jsx React.DOM */

var MainMenu = React.createClass({
    toggleEventLog() {
        SettingsActions.update({
            showEventLog: !this.props.settings.showEventLog
        });
    },
    render(){
        return <div>
            <button className={"btn " + (this.props.settings.showEventLog ? "btn-primary" : "btn-default")} onClick={this.toggleEventLog}>
                <i className="fa fa-database"></i> Display Event Log
            </button>
            </div>;
    }
});
var ToolsMenu = React.createClass({
    render(){
        return (<div>Tools Menu</div>);
    }
});
var ReportsMenu = React.createClass({
    render(){
        return (<div>Reports Menu</div>);
    }
});


var _Header_Entries = {
    main: {
        title: "Traffic",
        route: "main",
        menu: MainMenu
    },
    tools: {
        title: "Tools",
        route: "main",
        menu: ToolsMenu
    },
    reports: {
        title: "Visualization",
        route: "reports",
        menu: ReportsMenu
    }
};

var Header = React.createClass({
    getInitialState(){
        return {
            active: "main"
        };
    },
    handleClick(active){
        this.setState({active: active});
        ReactRouter.transitionTo(_Header_Entries[active].route);
        return false;
    },
    handleFileClick(){
        console.log("File click");
    },

    render(){
        var header = [];
        for(var item in _Header_Entries){
            var classes = this.state.active == item ? "active" : "";
            header.push(<a key={item} href="#" className={classes}
                onClick={this.handleClick.bind(this, item)}>{ _Header_Entries[item].title }</a>);
        }

        var menu = _Header_Entries[this.state.active].menu({
            settings: this.props.settings
        });
        return (
            <header>
                <div className="title-bar">
                    mitmproxy { this.props.settings.version }
                </div>
                <nav>
                    <a href="#" className="special" onClick={this.handleFileClick}> File </a>
                    {header}
                </nav>
                <div className="menu">
                    { menu }
                </div>
            </header>);
    }
});
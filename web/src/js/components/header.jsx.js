var MainMenu = React.createClass({
    mixins: [Navigation, State],
    getInitialState: function(){
        this.onQueryChange(Query.FILTER, function(oldVal, nextVal){
            this.setState({filter: nextVal});
        }.bind(this));
        return {
            filter: this.getQuery()[Query.FILTER]
        };
    },
    statics: {
        title: "Traffic",
        route: "flows"
    },
    toggleEventLog: function () {
        SettingsActions.update({
            showEventLog: !this.props.settings.showEventLog
        });
    },
    clearFlows: function () {
        $.post("/flows/clear");
    },
    setFilter: function(e){
        e.preventDefault();
        this.setQuery(Query.FILTER, this.state.filter);
    },
    onFilterChange: function(e){
        this.setState({filter: e.target.value});
    },
    render: function () {
        return (
            <div>
                <button className={"btn " + (this.props.settings.showEventLog ? "btn-primary" : "btn-default")} onClick={this.toggleEventLog}>
                    <i className="fa fa-database"></i>
                &nbsp;Display Event Log
                </button>
            &nbsp;
                <button className="btn btn-default" onClick={this.clearFlows}>
                    <i className="fa fa-eraser"></i>
                &nbsp;Clear Flows
                </button>
                &nbsp;
                <form className="form-inline" onSubmit={this.setFilter} style={{display:"inline-block"}}>
                    <input type="text" placeholder="filter expression"
                        onChange={this.onFilterChange} value={this.state.filter}
                        className="form-control"
                    />
                    </form>

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

var FileMenu = React.createClass({
    getInitialState: function () {
        return {
            showFileMenu: false
        };
    },
    handleFileClick: function (e) {
        e.preventDefault();
        if (!this.state.showFileMenu) {
            var close = function () {
                this.setState({showFileMenu: false});
                document.removeEventListener("click", close);
            }.bind(this);
            document.addEventListener("click", close);

            this.setState({
                showFileMenu: true
            });
        }
    },
    handleNewClick: function (e) {
        e.preventDefault();
        console.error("unimplemented: handleNewClick");
    },
    handleOpenClick: function (e) {
        e.preventDefault();
        console.error("unimplemented: handleOpenClick");
    },
    handleSaveClick: function (e) {
        e.preventDefault();
        console.error("unimplemented: handleSaveClick");
    },
    handleShutdownClick: function (e) {
        e.preventDefault();
        console.error("unimplemented: handleShutdownClick");
    },
    render: function () {
        var fileMenuClass = "dropdown pull-left" + (this.state.showFileMenu ? " open" : "");

        return (
            <div className={fileMenuClass}>
                <a href="#" className="special" onClick={this.handleFileClick}> File </a>
                <ul className="dropdown-menu" role="menu">
                    <li>
                        <a href="#" onClick={this.handleNewClick}>
                            <i className="fa fa-fw fa-file"></i>
                            New
                        </a>
                    </li>
                    <li>
                        <a href="#" onClick={this.handleOpenClick}>
                            <i className="fa fa-fw fa-folder-open"></i>
                            Open
                        </a>
                    </li>
                    <li>
                        <a href="#" onClick={this.handleSaveClick}>
                            <i className="fa fa-fw fa-save"></i>
                            Save
                        </a>
                    </li>
                    <li role="presentation" className="divider"></li>
                    <li>
                        <a href="#" onClick={this.handleShutdownClick}>
                            <i className="fa fa-fw fa-plug"></i>
                            Shutdown
                        </a>
                    </li>
                </ul>
            </div>
        );
    }
});


var header_entries = [MainMenu, ToolsMenu, ReportsMenu];


var Header = React.createClass({
    mixins: [Navigation],
    getInitialState: function () {
        return {
            active: header_entries[0]
        };
    },
    handleClick: function (active, e) {
        e.preventDefault();
        this.replaceWith(active.route);
        this.setState({active: active});
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
                    <FileMenu/>
                    {header}
                </nav>
                <div className="menu">
                    <this.state.active settings={this.props.settings}/>
                </div>
            </header>
        );
    }
});

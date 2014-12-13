var FilterInput = React.createClass({
    getInitialState: function () {
        // Focus: Show popover
        // Mousefocus: Mouse over Tooltip
        // onBlur is triggered before click on tooltip,
        // hiding the tooltip before link is clicked.
        return {
            value: this.props.value,
            focus: false,
            mousefocus: false
        };
    },
    componentWillReceiveProps: function (nextProps) {
        this.setState({value: nextProps.value});
    },
    onChange: function (e) {
        var nextValue = e.target.value;
        this.setState({
            value: nextValue
        });
        try {
            Filt.parse(nextValue);
        } catch (err) {
            return;
        }
        this.props.onChange(nextValue);
    },
    isValid: function () {
        try {
            Filt.parse(this.state.value);
            return true;
        } catch (e) {
            return false;
        }
    },
    getDesc: function () {
        var desc;
        try {
            desc = Filt.parse(this.state.value).desc;
        } catch (e) {
            desc = "" + e;
        }
        if (desc !== "true") {
            return desc;
        } else {
            return (
                <a href="https://mitmproxy.org/doc/features/filters.html" target="_blank">
                    <i className="fa fa-external-link"></i>
                    Filter Documentation
                </a>
            );
        }
    },
    onFocus: function () {
        this.setState({focus: true});
    },
    onBlur: function () {
        this.setState({focus: false});
    },
    onMouseEnter: function () {
        this.setState({mousefocus: true});
    },
    onMouseLeave: function () {
        this.setState({mousefocus: false});
    },
    onKeyDown: function (e) {
        if (e.target.value === "" &&
            e.keyCode === Key.BACKSPACE) {
            e.preventDefault();
            this.remove();
        }
    },
    remove: function () {
        if(this.props.onRemove) {
            this.props.onRemove();
        }
    },
    focus: function () {
        this.refs.input.getDOMNode().select();
    },
    render: function () {
        var isValid = this.isValid();
        var icon = "fa fa-fw fa-" + this.props.type;
        var groupClassName = "filter-input input-group" + (isValid ? "" : " has-error");

        var popover;
        if (this.state.focus || this.state.mousefocus) {
            popover = (
                <div className="popover bottom" onMouseEnter={this.onMouseEnter} onMouseLeave={this.onMouseLeave}>
                    <div className="arrow"></div>
                    <div className="popover-content">
                    {this.getDesc()}
                    </div>
                </div>
            );
        }

        return (
            <div className={groupClassName}>
                <span className="input-group-addon">
                    <i className={icon} style={{color: this.props.color}}></i>
                </span>
                <input type="text" placeholder="filter expression" className="form-control"
                    ref="input"
                    onChange={this.onChange}
                    onFocus={this.onFocus}
                    onBlur={this.onBlur}
                    onKeyDown={this.onKeyDown}
                    value={this.state.value}/>
                {popover}
            </div>
        );
    }
});

var MainMenu = React.createClass({
    mixins: [Navigation, State],
    getInitialState: function () {
        return {
            filter: this.getQuery()[Query.FILTER] || "",
            highlight: (this.getQuery()[Query.HIGHLIGHT] || "").split("&").map(decodeURIComponent)
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
        $.post("/clear");
    },
    applyFilter: function (filter, highlight) {
        var d = {};
        d[Query.FILTER] = filter;
        d[Query.HIGHLIGHT] = highlight.map(encodeURIComponent).join("&");
        this.setQuery(d);
    },
    onFilterChange: function (val) {
        this.setState({filter: val});
        this.applyFilter(val, this.state.highlight);
    },
    onHighlightChange: function (index, val) {
        var highlight = this.state.highlight.slice();
        highlight[index] = val;
        if (highlight[highlight.length - 1] !== "" && highlight.length < 14) {
            highlight.push("");
        }
        this.setState({
            highlight: highlight
        });
        this.applyFilter(this.state.filter, highlight);
    },
    onHighlightRemove: function (index) {
        if (this.state.highlight.length > 1 && index < this.state.highlight.length - 1) {
            var highlight = this.state.highlight.slice();
            highlight.splice(index, 1);
            this.setState({
                highlight: highlight
            });
        }
        this.refs["highlight-" + Math.max(0, index - 1)].focus();
    },
    getColor: function (index) {
        var colors = [
            "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#1f77b4", "#bcbd22", "#17becf",
            "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5", "#aec7e8", "#dbdb8d", "#9edae5"
        ];
        return colors[index % colors.length];
    },
    render: function () {
        var highlightFilterInputs = [];
        for (var i = 0; i < this.state.highlight.length; i++) {
            highlightFilterInputs.push(<span key={"placeholder-" + i}> </span>);
            highlightFilterInputs.push(
                <FilterInput
                    key={"highlight-" + i}
                    ref={"highlight-" + i}
                    type="tag"
                    color={this.getColor(i)}
                    value={this.state.highlight[i]}
                    onChange={this.onHighlightChange.bind(this, i)}
                    onRemove={this.onHighlightRemove.bind(this, i)}
                />
            );

        }

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
                <form className="form-inline" style={{display:"inline"}}>
                    <FilterInput type="filter" color="black" value={this.state.filter} onChange={this.onFilterChange} />
                    { highlightFilterInputs }
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

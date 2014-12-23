var Footer = React.createClass({
    render: function () {
        var mode = this.props.settings.mode;
        var intercept = this.props.settings.intercept;
        return (
            <footer>
                {mode != "regular" ? <span className="label label-success">{mode} mode</span> : null}
                &nbsp;
                {intercept ? <span className="label label-success">Intercept: {intercept}</span> : null}
            </footer>
        );
    }
});

var Footer = React.createClass({
    render: function () {
        var mode = this.props.settings.mode;
        return (
            <footer>
                {mode != "regular" ? <span className="label label-success">{mode} mode</span> : null}
            </footer>
        );
    }
});

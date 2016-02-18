var React = require("react");
var _ = require("lodash");

var utils = require("../utils.js");
var common = require("./common.js");

var Prompt = React.createClass({
    mixins: [common.ChildFocus],
    propTypes: {
        options: React.PropTypes.array.isRequired,
        done: React.PropTypes.func.isRequired,
        prompt: React.PropTypes.string
    },
    componentDidMount: function () {
        React.findDOMNode(this).focus();
    },
    onKeyDown: function (e) {
        e.stopPropagation();
        e.preventDefault();
        var opts = this.getOptions();
        for (var i = 0; i < opts.length; i++) {
            var k = opts[i].key;
            if (utils.Key[k.toUpperCase()] === e.keyCode) {
                this.done(k);
                return;
            }
        }
        if (e.keyCode === utils.Key.ESC || e.keyCode === utils.Key.ENTER) {
            this.done(false);
        }
    },
    onClick: function (e) {
        this.done(false);
    },
    done: function (ret) {
        this.props.done(ret);
        this.returnFocus();
    },
    getOptions: function () {
        var opts = [];

        var keyTaken = function (k) {
            return _.includes(_.pluck(opts, "key"), k);
        };

        for (var i = 0; i < this.props.options.length; i++) {
            var opt = this.props.options[i];
            if (_.isString(opt)) {
                var str = opt;
                while (str.length > 0 && keyTaken(str[0])) {
                    str = str.substr(1);
                }
                opt = {
                    text: opt,
                    key: str[0]
                };
            }
            if (!opt.text || !opt.key || keyTaken(opt.key)) {
                throw "invalid options";
            } else {
                opts.push(opt);
            }
        }
        return opts;
    },
    render: function () {
        var opts = this.getOptions();
        opts = _.map(opts, function (o) {
            var prefix, suffix;
            var idx = o.text.indexOf(o.key);
            if (idx !== -1) {
                prefix = o.text.substring(0, idx);
                suffix = o.text.substring(idx + 1);

            } else {
                prefix = o.text + " (";
                suffix = ")";
            }
            var onClick = function (e) {
                this.done(o.key);
                e.stopPropagation();
            }.bind(this);
            return <span
                key={o.key}
                className="option"
                onClick={onClick}>
            {prefix}
                <strong className="text-primary">{o.key}</strong>{suffix}
            </span>;
        }.bind(this));
        return <div tabIndex="0" onKeyDown={this.onKeyDown} onClick={this.onClick} className="prompt-dialog">
            <div className="prompt-content">
            {this.props.prompt || <strong>Select: </strong> }
            {opts}
            </div>
        </div>;
    }
});

module.exports = Prompt;
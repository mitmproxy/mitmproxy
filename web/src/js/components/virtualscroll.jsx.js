var VirtualScrollMixin = {
    getInitialState: function () {
        return {
            start: 0,
            stop: 0
        }
    },
    getPlaceholderTop: function () {
        var style = {
            height: this.state.start * this.props.rowHeight
        };
        var spacer = <tr key="placeholder-top" style={style}></tr>;

        if (this.state.start % 2 === 1) {
            // fix even/odd rows
            return [spacer, <tr key="placeholder-top-2"></tr>];
        } else {
            return spacer;
        }
    },
    getPlaceholderBottom: function (total) {
        var style = {
            height: Math.max(0, total - this.state.stop) * this.props.rowHeight
        };
        return <tr key="placeholder-bottom" style={style}></tr>;
    },
    onScroll: function () {
        var viewport = this.getDOMNode();
        var top = viewport.scrollTop;
        var height = viewport.offsetHeight;
        var start = Math.floor(top / this.props.rowHeight);
        var stop = start + Math.ceil(height / this.props.rowHeight);
        this.setState({
            start: start,
            stop: stop
        });
    },
    scrollRowIntoView: function(index, head_height){

        var row_top = (index * this.props.rowHeight) + head_height;
        var row_bottom = row_top + this.props.rowHeight;

        var viewport = this.getDOMNode();
        var viewport_top = viewport.scrollTop;
        var viewport_bottom = viewport_top + viewport.offsetHeight;

        // Account for pinned thead
        if (row_top - head_height < viewport_top) {
            viewport.scrollTop = row_top - head_height;
        } else if (row_bottom > viewport_bottom) {
            viewport.scrollTop = row_bottom - viewport.offsetHeight;
        }
    },
};
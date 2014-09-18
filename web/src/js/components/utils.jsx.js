/** @jsx React.DOM */

//React utils. For other utilities, see ../utils.js

var Splitter = React.createClass({
    getDefaultProps: function () {
    return {
        axis: "x"
        }
    },
    getInitialState: function(){
        return {
            applied: false,
            startX: false,
            startY: false
        };
    },
    onMouseDown: function(e){
        this.setState({
            startX: e.pageX,
            startY: e.pageY
        });
        window.addEventListener("mousemove",this.onMouseMove);
        window.addEventListener("mouseup",this.onMouseUp);
    },
    onMouseUp: function(e){
        window.removeEventListener("mouseup",this.onMouseUp);
        window.removeEventListener("mousemove",this.onMouseMove);

        var node = this.getDOMNode();
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;
        this.getDOMNode().style.transform="";

        var dX = e.pageX-this.state.startX;
        var dY = e.pageY-this.state.startY;
        var flexBasis;
        if(this.props.axis === "x"){
            flexBasis = prev.offsetWidth + dX;
        } else {
            flexBasis = prev.offsetHeight + dY;
        }

        prev.style.flex = "0 0 "+Math.max(0, flexBasis)+"px";   
        next.style.flex = "1 1 auto";

        this.setState({
            applied: true
        });
    },
    onMouseMove: function(e){
        var dX = 0, dY = 0;
        if(this.props.axis === "x"){
            dX = e.pageX-this.state.startX;
        } else {
            dY = e.pageY-this.state.startY;
        }
        this.getDOMNode().style.transform = "translate("+dX+"px,"+dY+"px)";
    },
    reset: function(){
        if(!this.state.applied){
            return;
        }
        var node = this.getDOMNode();
        var prev = node.previousElementSibling;
        var next = node.nextElementSibling;
        
        prev.style.flex = "";
        next.style.flex = "";
    },
    render: function(){
        var className = "splitter";
        if(this.props.axis === "x"){
            className += " splitter-x";
        } else {
            className += " splitter-y";
        }
        return <div className={className} onMouseDown={this.onMouseDown}></div>;
    }
});
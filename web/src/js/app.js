$(function () {
    ReactRouter.run(routes, function (Handler) {
        React.render(<Handler/>, document.body);
    });
    var UpdateConnection = new Connection("/updates");
    UpdateConnection.onmessage = function (message) {
        var m = JSON.parse(message.data);
        AppDispatcher.dispatchServerAction(m);
    };
});
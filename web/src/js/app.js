$(function () {
    window.app = React.renderComponent(ProxyApp, document.body);
    var UpdateConnection = new Connection("/updates");
    UpdateConnection.onmessage = function (message) {
        var m = JSON.parse(message.data);
        AppDispatcher.dispatchServerAction(m);
    };
});
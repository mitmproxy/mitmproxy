$(function () {
    window.ws = new Connection("/updates");

    ReactRouter.run(routes, function (Handler) {
        React.render(<Handler/>, document.body);
    });
});
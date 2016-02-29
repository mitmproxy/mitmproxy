
import flux from "flux";

const PayloadSources = {
    VIEW: "view",
    SERVER: "server"
};


export var AppDispatcher = new flux.Dispatcher();
AppDispatcher.dispatchViewAction = function (action) {
    action.source = PayloadSources.VIEW;
    this.dispatch(action);
};
AppDispatcher.dispatchServerAction = function (action) {
    action.source = PayloadSources.SERVER;
    this.dispatch(action);
};
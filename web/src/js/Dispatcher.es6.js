const PayloadSources = {
  VIEW_ACTION: "VIEW_ACTION",
  SERVER_ACTION: "SERVER_ACTION"
};

class Dispatcher {

  constructor() {
    this.callbacks = [];
  }

  register(callback){
    this.callbacks.push(callback);
  }

  unregister(callback){
    var index = this.callbacks.indexOf(f);
    if (index >= 0) {
      this.callbacks.splice(this.callbacks.indexOf(f), 1);
    }
  }

  dispatch(payload){
    console.debug("dispatch", payload);
    this.callbacks.forEach((callback) => {
        callback(payload);
    });
  }

}

AppDispatcher = new Dispatcher();
AppDispatcher.dispatchViewAction = function(action){
  action.actionSource = PayloadSources.VIEW_ACTION;
  this.dispatch(action);
};
AppDispatcher.dispatchServerAction = function(action){
  action.actionSource = PayloadSources.SERVER_ACTION;
  this.dispatch(action);
};
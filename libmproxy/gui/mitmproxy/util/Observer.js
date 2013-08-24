/**
 * "Polyfill" for Harmony Object.observe
 * The module is designed to be replaced by Object.observe as soon as the harmony spec is finalized.
 *
 */
define(["dojo/_base/declare"], function(declare) {
  "use strict";

  var Observer = {};

  Observer.ObservablePolyfillMixin = declare([], {
    constructor: function() {
      Object.defineProperty(this, "_observe", {
        value: [],
        configurable: false,
        enumerable: false,
        writable: false
      });
    },
    notify: function(record) {
      var self = this;
      this._observe.forEach(function(observer){
        observer.call(self, record);
      });
    }
  });



  Observer.observe = function(obj, observer, ownable) {
    obj._observe.push(observer);
    if(ownable)
      return {"remove": function(){
        Observer.unobserve(obj,observer);
      }};
  };
  Observer.unobserve = function(obj, observer) {
    var index = obj._observe.indexOf(observer);
    if(index >= 0){
        obj._observe.splice(index,1);
    }
  };
  /*
  Observer.observeProperty = function(obj, prop, callback) {
    var observer = function(records) {
      if (records.name === prop) {
        callback.apply(this, arguments);
      }
    };
    Observer.observe(obj,observer);
    return {
      remove: function() {
        Observer.unobserve(obj,observer);
      }
    };
  };
  */


  return Observer;
});
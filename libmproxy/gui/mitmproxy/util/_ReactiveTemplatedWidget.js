/**
 * Reactive templating for Dojo
 */
define([
    "dojo/_base/declare",
    "dojo/dom-construct",
    "dojo/aspect",
    "dojo/on",
    "dojo/query",
    "dijit/_WidgetBase",
    "dijit/registry",
    "./Observer"
], function(declare, domConstruct, aspect, on, query, _WidgetBase, registry, Observer) {

  var default_bindings = {
    "bind": function(type, node, value) {
      var obj = value[0];
      var prop = value[1];
      obj[prop] = node;
    },
    "options": function(type, node, optionArray) {
      optionArray = optionArray || [];
      var optionsFragment = document.createDocumentFragment();
      optionArray.forEach(function(optionName) {
        var option = document.createElement("option");
        option.value = option.textContent = optionName;
        optionsFragment.appendChild(option);
      });
      domConstruct.place(optionsFragment, node, "only");
    },
    "select": function(type, node, value) {
      //query('option:not([value="'+value+'"])', node).removeAttr("selected");
      query('option[value="' + value + '"]', node).attr("selected", "selected");
    },
    "css": function(type, node, value) {
      if (value)
        node.style[value[0]] = value[1];
    },
    "on": function(type, node, value) {
      eventListenerBinding.call(this, value[0], node, value[1]);
    },
    "toggleClass": function(type, node, value) {
      value = value.slice();
      while(value.length > 0){
        var className = value.shift();
        var show = !!value.shift();
        (show ? node.classList.add : node.classList.remove).call(node.classList,className);
      }
      
    }
  };

  var appendChild = function(type, node, value) {
    if (!value)
      value = domConstruct.create("div");
    domConstruct.place(value, node, "only");
    node.dataset.suppressBind = true;
  };
  default_bindings.appendChild = appendChild;
  default_bindings.widget = function(type, node, value) {
    if (value && node.firstChild === value.domNode)
      return;

    var widget;
    if (node.firstChild)
      widget = registry.byNode(node.firstChild);
    if (widget)
      widget.destroyRecursive(false);
    if (value) {
      this.own(value);
    }
    appendChild(type, node, value ? value.domNode : undefined);
  };

  var children = function(type, node, value) {
    var self = this;

    //remove existing nodes
    Array.prototype.slice.call(node.children).forEach(function(e) {
      if (value.indexOf(e) === -1) {
        var widget = registry.byNode(e);
        if (widget)
          widget.destroyRecursive(false);
      } else {
        e._existed = true;
      }
      node.removeChild(e);
    });

    //Add new ones
    value.forEach(function(e) {
      node.appendChild(e);
      if (e._existed) {
        delete e._existed;
      } else {
        var widget = registry.byNode(e);
        if (widget)
          self.own(widget);
      }
    });
  };

  default_bindings.children = children;
  default_bindings.widgets = function(type, node, value) {
    children.call(this, type, node, value.map(function(e) {
      return e.domNode ? e.domNode : e;
    }));
  };

  var hide = function(type, node, value) {
    if (value) {
      node.classList.add("hide");
    } else {
      node.classList.remove("hide");
    }
  };
  default_bindings.hide = hide;
  default_bindings.show = function(type, node, value) {
    hide(type, node, !value);
  };

  var eventListenerBinding = function(type, node, func) {
    var evt_handle = on(node, type, func);
    //Remove event handler before updating the next bindings
    var asp_handle = aspect.before(this, "updateBindings", function() {
      evt_handle.remove();
      asp_handle.remove();
    });
    this.own(evt_handle, asp_handle);
  };

  ["click", "load", "change","input","submit","blur","focus","mouseover","mouseout"].forEach(function(event) {
    default_bindings[event] = eventListenerBinding;
  });

  var _ReactiveTemplatedWidget = declare([_WidgetBase, Observer.ObservablePolyfillMixin], {
    _bindings: default_bindings,
    constructor: function() {
      this.context = this.context || {};
      this.updateBindings = this.updateBindings.bind(this);
      Observer.observe(this, function(records) {
        if (records.name === "model" || records.name === "context")
          this.updateBindings();
      });
    },
    getBinding: function(type) {
      if (this.bindings && (type in this.bindings)) {
        return this.bindings[type];
      } else if (type in this._bindings) {
        return this._bindings[type];
      }
    },
    updateBinding: function(type, node, value) {
      // console.debug("update_binding", arguments);
      var binding = this.getBinding(type);
      if (binding) {
        binding.apply(this, Array.prototype.slice.call(arguments));
      } else {
        node[type] = value;
      }
    },
    /**
     *  Compiles the Widget Template and converts it into a DOM Node.
     *  Returns the DOM Node.
     */
    _buildDom: function() {

      //convert template string into DOM
      var domNode = domConstruct.toDom(this.templateString);

      //If we have multiple nodes, toDom returns a  #document-fragment.
      //Wrap it in a <div>, if necessary.
      if (domNode.nodeType === 11) {
        var _domNode = domConstruct.create("div");
        _domNode.appendChild(domNode);
        domNode = _domNode;
      }
      return domNode;
    },
    _eval: function(expr) {
      /*jshint evil:true, withstmt:true*/
      with({
        view: this,
        model: this.model
      }) {
        with(this.context) {
          with(this.model || {}) {
            return eval(expr);
          }
        }
      }
    },
    _parseBinding: function(binding) {
      var splitPosType = binding.indexOf(":");
      var type = binding.substr(0, splitPosType).trim();
      var property_expr = binding.substr(splitPosType + 1).trim();

      property_expr = decodeURIComponent(property_expr); //decode encoded ";"s

      return [type, property_expr];
    },
    updateBindings: function() {
      var self = this;

      if (this.observedModel && this.model !== this.observedModel) {
        //console.log("unobserve old model");
        Observer.unobserve(this.observedModel, this.updateBindings);
      }
      if (this.model && this.model !== this.observedModel) {
        //console.log("observe new model");
        Observer.observe(this.model, this.updateBindings);
        this.observedModel = this.model;
      }

      var handleBinding = function(node, binding) {

        //Don't handle nodes whose parentNode is hidden.
        var parentNode = node;
        while (parentNode !== self.domNode) {
          if (parentNode.classList.contains("hide")) {
            return;
          }
          parentNode = parentNode.parentNode;
        }

        var value = this._eval(binding[1]);
        this.updateBinding(binding[0], node, value);
      };

      this.node_bindings.forEach(function(binding_info) {
        var node = binding_info[0];
        var bindings = binding_info[1];
        bindings.forEach(handleBinding.bind(self, node));
      });
    },
    buildRendering: function() {
      var self = this;

      this.domNode = this._buildDom();
      this.node_bindings = [];

      var nodes_to_bind = query("[data-bind]", this.domNode);
      if (this.domNode.dataset.bind) //query doesn't include the root node, check manually.
        nodes_to_bind.push(this.domNode);

      nodes_to_bind.forEach(function(node) {

        var parentNode = node;
        while (parentNode !== self.domNode) {
          parentNode = parentNode.parentNode;
          if (parentNode.dataset.suppressBind) {
            return;
          }
        }

        var raw_bindings = node.dataset.bind.split(";");
        var bindings = raw_bindings.map(self._parseBinding.bind(self));
        self.node_bindings.push([node, bindings]);
      });

      this.updateBindings();

      this.inherited(arguments);
    },
    destroy: function() {
      if (this.observedModel) {
        Observer.unobserve(this.observedModel, this.updateBindings);
      }
      this.inherited(arguments);
    }
  });
  return _ReactiveTemplatedWidget;
});
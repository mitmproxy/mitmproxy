define(["dojo/_base/declare",
		"../util/Observer",
        "jquery",
        "bootstrap/js/popover",
		"../util/_ReactiveTemplatedWidget",
		"dojo/text!./templates/Searchbar.html",
        "dojo/text!./templates/Searchbar-filterbutton.html",
		"dojo/text!./templates/Searchbar-syntaxhelp.html"
], function(
	declare,
	Observer,
    $,
    _,
	_ReactiveTemplatedWidget,
	template,
	templateButton,
    syntaxHelp) {
        
	var FilterButton = declare([_ReactiveTemplatedWidget], {
		templateString: templateButton,
		empty: true,
        query: "",
        value: "",
        state: "active",
        postCreate: function(){
            this.inherited(arguments);
            this.updateStatus();
        },
		onSubmit: function(event) {
			event && event.preventDefault();
			if (this.query !== this.value) {
				this.query = this.value;
				this.notify({name: "query"});
				this.updateStatus();
			}
		},
        onClick: function(event) {
          if(this.state === "closable") {
              event.preventDefault();
              this.inputNode.value = "";
              this.onInput();
              this.onSubmit();
          }
        },
		onInput: function() {
            this.value = this.inputNode.value.trim();
			this.empty = (this.value === "");
            this.notify({name: "value"});
			this.updateStatus();
		},
        onFocus: function(){
          this.focused = true;
          this.updateStatus();
        },
        onBlur: function(){
          this.focused = false;
          //Uncomment the next two lines to disable autosearch on focus lost
          if(this.value !== this.query)
            this.onSubmit();
          this.updateStatus();
        },
		updateStatus: function() {
            this.state = (this.value === this.query) ? 
                (this.focused || this.empty ? "done" : "closable") :
                (this.focused ? "active" : "warn");
			this.updateBindings();
		}
	});

	return declare([_ReactiveTemplatedWidget], {
		templateString: template,
		type: {
			isfilter: true
		},
		constructor: function() {
			this.filters = [];
			this.colors = ["#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#1f77b4", "#bcbd22", "#17becf",
					"#ffbb78", "#98df8a", "#ff9896", "#c5b0d5", "#aec7e8", "#dbdb8d", "#9edae5"
			];
		},
		postCreate: function() {
			this.inherited(arguments);
			this.addFilter({
				filter: true,
				fixed: true,
				alwaysVisible: true
			});
			this.addFilter({
				color: this.colors.shift(),
				fixed: true,
				alwaysVisible: true
			});
            $(this.domNode).popover({
                trigger: "hover",
                placement: "bottom",
                selector: ".input-group-addon",
                html: true,
                title: "Filter Syntax",
                content: syntaxHelp,
                container:"body"
            });
		},
        destroy: function(){
            $(this.domNode).popover("destroy");
            this.inherited(arguments);
        },
		addFilter: function(options) {
			var self = this;
            options.last = true;
			var filter = new FilterButton(options);
			this.own(Observer.observe(filter, function(records) {
				if (records.name === "query")
					self.onSubmit(filter);
                if (records.name === "value")
					self.onInput(filter);
			},true));

            var last = this.filters[this.filters.length-1];
            if(last) {
                last.last = false;
                last.updateStatus();
            }
			this.filters.push(filter);
            this.updateBindings();
            filter.domNode.style.opacity = "0.0";
			this.filtersNode.appendChild(filter.domNode);
            
            window.setTimeout(function(){
                filter.domNode.style.opacity = "";
            },0);
            
		},
		removeFilter: function(filter) {
			this.colors.unshift(filter.color);
			filter.destroyRecursive(false);
            var index = this.filters.indexOf(filter);
            if(index == this.filters.length-1) {
                this.filters[index-1].last = true;
                this.filters[index-1].updateStatus();
            }
			this.filters.splice(this.filters.indexOf(filter), 1);
			this.updateBindings();
		},
        onInput: function(filter) {
            var last = this.filters[this.filters.length - 1];
            var secondToLast = this.filters[this.filters.length - 2];
            //Add new one if last one has content
			if (!last.empty && this.colors.length > 0) {
				this.addFilter({
					color: this.colors.shift()
				});
                this.getParent().resize();
			}
            if (filter !== last && !last.fixed && last.empty && secondToLast.empty) {
				//Remove last one if we just cleared the second last one
				this.removeFilter(last);
                this.getParent().resize();
			}
        },
		onSubmit: function(filter) {
			var last = this.filters[this.filters.length - 1];
			var secondToLast = this.filters[this.filters.length - 2];

			//remove filter if empty and not last
			if (!filter.fixed && filter.empty && last !== filter) {
                var focusIndex = Math.max(0,this.filters.indexOf(filter)-1);
				this.removeFilter(filter);
                this.filters[focusIndex].inputNode.focus();
                this.getParent().resize();
			} else if (!last.fixed && last.empty && secondToLast.empty) {
				//Remove last one if we just cleared either the second last one
				this.removeFilter(last);
                this.getParent().resize();
			}

			var query = {};
			this.filters.forEach(function(filter) {
                var name;
                if(filter.filter) {
                    name = "filter"
                } else {
                    //We change the color opacity already for the tag
                    // more performant than recalculating rgba valuesfor every flow.
                    name = ("rgba("+
                        parseInt(filter.color.substr(1,2),16)+","+
                        parseInt(filter.color.substr(3,2),16)+","+
                        parseInt(filter.color.substr(5,2),16)+",0.5)");
                }
				if(filter.query){
					query[name] = filter.query;
				}
			});
			this.query = query;
			this.notify({name:"query"});
		}
	});

});
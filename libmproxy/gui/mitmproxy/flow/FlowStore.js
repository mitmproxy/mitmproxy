/**
 * Implements dojo/store/api/Store
 */
define(["dojo/when", "dojo/_base/lang", "dojo/_base/declare", "dojo/store/JsonRest", "./FlowFactory"], function(when, lang, declare, JsonRest, FlowFactory) {

	var callListeners = function(listeners, object, removedFrom, insertedInto) {
		console.log("callListeners", arguments);
		var copyListeners = listeners.slice();
		for (var i = 0, l = copyListeners.length; i < l; i++) {
			var listener = copyListeners[i];
			listener(object, removedFrom, insertedInto);
		}
	};

	var FlowStore = declare([JsonRest], {
		constructor: function() {
			this.queryUpdaters = [];
		},
		sortParam: "sort",
		_observeFunc: function(results) {
			var store = this;
			var listeners = [],
				queryUpdater;

			return function(listener, includeObjectUpdates) {
				if (listeners.push(listener) === 1) { // first listener was added, create the query checker and updater
					queryUpdater = function( changed, existingId ) {
						when(results, function(resultsArray) {
							var options = lang.mixin({}, results.options);
							options.plain = true;
							when(store.query(results.query, options), function(newResults) { //re-query store to obtain new results

								var _in_old, _in_new;

								//lazy computed identity -> element mapping
								//for performance reasons these mappings can be omitted if id_is === id_should for all elements.
								var in_old = function(){
									if(!_in_old) {
										_in_old = {};
										resultsArray.forEach(function(e) {
											_in_old[store.getIdentity(e)] = e;
										});
									}
									return _in_old;
								};
								var in_new = function(){
									if(!_in_new) {
										_in_new = {};
										newResults.forEach(function(e) {
											_in_new[store.getIdentity(e)] = true;
										});
									}
									return _in_new;
								};

								var remove = function(i) {
									var obj = resultsArray[i];
									resultsArray.splice(i, 1);
									callListeners(listeners, obj, i, -1);
								};
								var insert = function(i, obj) {
									resultsArray.splice(i, 0, obj);
									callListeners(listeners, obj, -1, i);
								};

								//Not-so trivial algorithm transforming resultsArray into an array
								//where ident(resultsArray[i]) === ident(newResults[i]) for every i.
								//Worst Case complexity is O(n^2), but we do much better usually.
								for (var i = 0; i < resultsArray.length || i < newResults.length; i++) {
									//Contract: ident(resultsArray[x]) === ident(newResults[x]) for x < i.

									var obj_is = resultsArray[i];
									var id_is = obj_is ? store.getIdentity(obj_is) : undefined;
									var obj_new = newResults[i];
									var id_should = obj_new ? store.getIdentity(obj_new) : undefined;

									//trivial case: already in the right position
									if (id_is === id_should) {
										if (includeObjectUpdates && existingId === id_is)
											callListeners(listeners, obj_is, i, i);
										continue;
									}

									//Remove elements that are not present in the new set.
									if (id_is && !(id_is in in_new())) {
										remove(i);
										i--;
										continue;
									}

									//less trivial case: element exists in resultsArray, but in a different position.
									//=> remove there and insert at our position.
									if (id_should in in_old()) {
										var obj_move = in_old()[id_should];
										var oldIndex = resultsArray.indexOf(obj_move);
										remove(oldIndex);
										insert(i, obj_move);
										continue;

									//element doesn't exist in resultsArray. We need to make a flow out of it as we are querying the store plainly.
									} else {
										FlowFactory.makeFlow(obj_new);
										insert(i, obj_new);
										continue;
									}


								}
							});
						});

					};

					console.debug("add queryUpdater #"+(store.queryUpdaters.length+1));
					store.queryUpdaters.push(queryUpdater);
				}

				var handle = {};
				handle.cancel = function() {
					console.debug("handle.cancel");
					// remove this listener
					var index = listeners.indexOf(listener);
					if (index > -1) { // check to make sure we haven't already called cancel
						listeners.splice(index, 1);
						if (!listeners.length) {
							console.debug("remove queryUpdater");
							// no more listeners, remove the query updater too
							store.queryUpdaters.splice(store.queryUpdaters.indexOf(queryUpdater), 1);
						}
					}
				};
				return handle;
			};
		},
		query: function(query, options) {
            if(this._total && options && options.count && this._total <= options.start + options.count){
                options.count += 50;
            }

			console.debug("query", query, options);
			var results = this.inherited(arguments);
			options = options || {};

            /* This is a very ugly workaround for https://github.com/SitePen/dgrid/issues/363 */
            /* It makes your and my eyes bleed. */
            var self = this;
            results.total.then(function(total){
                self._total = total;
            });
            if(options.count > 260){
                console.debug("Running dgrid total count bugfix...");
                mitmproxy.MainLayout.trafficPane.grid.refresh({keepScrollPosition:true});
            }


			if (options.plain) //used to speed up observe queries
				return results;

			//transform json objects into flows
			results.then(function(resultsArray) {
				resultsArray.forEach(function(flowData) {
					FlowFactory.makeFlow(flowData);
				});
			});

			results.query = query;
			results.options = options;

			results.observe = this._observeFunc(results);
			return results;
		},
		notify: function(object, existingId) {
			var updaters = this.queryUpdaters.slice();
			for(var i = 0, l = updaters.length; i < l; i++){
				updaters[i](object, existingId);
			}
		}
	});
	//TODO: notify dgrid if total count has changed
	//https://github.com/SitePen/dgrid/issues/363


	return FlowStore;
});
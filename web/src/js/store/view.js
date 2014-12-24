function SortByStoreOrder(elem) {
    return this.store.index(elem.id);
}

var default_sort = SortByStoreOrder;
var default_filt = function(elem){
    return true;
};

function StoreView(store, filt, sortfun) {
    EventEmitter.call(this);
    filt = filt || default_filt;
    sortfun = sortfun || default_sort;

    this.store = store;

    this.add = this.add.bind(this);
    this.update = this.update.bind(this);
    this.remove = this.remove.bind(this);
    this.recalculate = this.recalculate.bind(this);
    this.store.addListener("add", this.add);
    this.store.addListener("update", this.update);
    this.store.addListener("remove", this.remove);
    this.store.addListener("recalculate", this.recalculate);

    this.recalculate(filt, sortfun);
}

_.extend(StoreView.prototype, EventEmitter.prototype, {
    close: function () {
        this.store.removeListener("add", this.add);
        this.store.removeListener("update", this.update);
        this.store.removeListener("remove", this.remove);
        this.store.removeListener("recalculate", this.recalculate);
        },
        recalculate: function (filt, sortfun) {
        if (filt) {
            this.filt = filt.bind(this);
        }
        if (sortfun) {
            this.sortfun = sortfun.bind(this);
        }

        this.list = this.store.list.filter(this.filt);
        this.list.sort(function (a, b) {
            return this.sortfun(a) - this.sortfun(b);
        }.bind(this));
        this.emit("recalculate");
    },
    index: function (elem) {
        return _.sortedIndex(this.list, elem, this.sortfun);
    },
    add: function (elem) {
        if (this.filt(elem)) {
            var idx = this.index(elem);
            if (idx === this.list.length) { //happens often, .push is way faster.
                this.list.push(elem);
            } else {
                this.list.splice(idx, 0, elem);
            }
            this.emit("add", elem, idx);
        }
    },
    update: function (elem) {
        var idx;
        var i = this.list.length;
        // Search from the back, we usually update the latest entries.
        while (i--) {
            if (this.list[i].id === elem.id) {
                idx = i;
                break;
            }
        }

        if (idx === -1) { //not contained in list
            this.add(elem);
        } else if (!this.filt(elem)) {
            this.remove(elem.id);
        } else {
            if (this.sortfun(this.list[idx]) !== this.sortfun(elem)) { //sortpos has changed
                this.remove(this.list[idx]);
                this.add(elem);
            } else {
                this.list[idx] = elem;
                this.emit("update", elem, idx);
            }
        }
    },
    remove: function (elem_id) {
        var idx = this.list.length;
        while (idx--) {
            if (this.list[idx].id === elem_id) {
                this.list.splice(idx, 1);
                this.emit("remove", elem_id, idx);
                break;
            }
        }
    }
});
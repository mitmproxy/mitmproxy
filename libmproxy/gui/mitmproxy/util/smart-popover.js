define(["jquery", "bootstrap/js/popover"], function ($, _) {

    /* Returns the distance of the given point to the closest point of the given box. */
    var getDistance = function (point, box) {
        var dist_y = 0, dist_x = 0;
        if (point.y < box.top) {
            dist_y = box.top - point.y;
        } else if (point.y > (box.top + box.height)) {
            dist_y = point.y - (box.top + box.height);
        }
        if (point.x < box.left) {
            dist_x = box.left - point.x;
        } else if (point.x > (box.left + box.width)) {
            dist_x = point.x - (box.left + box.width);
        }
        var dist = Math.sqrt((dist_y * dist_y) + (dist_x * dist_x));
        return dist;
    };

    $.fn.smartPopover = function (option) {

        option = option || {};
        option.trigger = "manual";

        this.each(function () {
            var $this = $(this);
            var Popover = $.fn.popover.Constructor;
            var popOver = $this.popover(option).data("bs.popover");

            var activePopoverEvent = false; //false: No active popover. event: The event that initiated the popover display.

            var onEvent = function (maxDist, event) {
                //Check if the triggering event is the one that just opened the popover
                //This is the case if we listen for a click event.
                if (event.originalEvent === activePopoverEvent) {
                    return;
                }
                var self = event.data.obj;

                var tip = self.$tip;
                var box = tip.offset();
                box.width = tip.width();
                box.height = tip.height();
                var dist = getDistance({x: event.clientX, y: event.clientY}, box);
                if (dist > (maxDist === undefined ? (self.options.hideDistance || 100) : maxDist)) {
                    popOver.leave(self);
                    activePopoverEvent = false;
                    $(document.body).off("mousemove", onMouseMove);
                    $(document.body).off("click", onClick);
                }
            };

            var onMouseMove = onEvent.bind(popOver, undefined);
            var onClick = onEvent.bind(popOver, 0);


            $this.on("mouseenter click", option.selector, function (event) {

                //var self = event instanceof this.constructor ?
                //    event : $(event.currentTarget)[this.type](this.getDelegateOptions()).data('bs.' + this.type)

                if (activePopoverEvent)
                    return;
                activePopoverEvent = event.originalEvent;
                popOver.enter(event);
                var _subPopover = $(event.currentTarget)[popOver.type](popOver.getDelegateOptions()).data('bs.' + popOver.type);
                $(document.body).on("mousemove", {obj: _subPopover}, onMouseMove);
                $(document.body).on("click", {obj: _subPopover}, onClick);
            });
        });
    }
});
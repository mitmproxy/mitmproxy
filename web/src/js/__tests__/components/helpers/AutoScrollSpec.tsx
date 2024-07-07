import * as React from "react";
import * as autoscroll from "../../../components/helpers/AutoScroll";
import TestUtils from "react-dom/test-utils";

describe("Autoscroll", () => {
    class TComponent extends React.Component {
        private viewport = React.createRef<HTMLDivElement>();

        getSnapshotBeforeUpdate() {
            return autoscroll.isAtBottom(this.viewport);
        }

        componentDidUpdate(prevProps, prevState, snapshot) {
            if (snapshot) {
                autoscroll.adjustScrollTop(this.viewport);
            }
        }

        render() {
            return <div ref={this.viewport}>foo</div>;
        }
    }

    it("should update component", () => {
        const autoScroll = TestUtils.renderIntoDocument(
            <TComponent></TComponent>,
        );
        const viewport = autoScroll.viewport.current;

        expect(autoScroll.getSnapshotBeforeUpdate()).toBe(false);

        viewport.scrollTop = 10;
        Object.defineProperty(viewport, "scrollHeight", {
            value: 10,
            writable: true,
        });
        expect(autoScroll.getSnapshotBeforeUpdate()).toBe(true);

        Object.defineProperty(viewport, "scrollHeight", {
            value: 42,
            writable: true,
        });
        autoScroll.componentDidUpdate({}, {}, true);
        expect(viewport.scrollTop).toBe(42);
    });
});

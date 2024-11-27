import * as React from "react";
import * as autoscroll from "../../../components/helpers/AutoScroll";
import { fireEvent, render } from "../../test-utils";

describe("Autoscroll", () => {
    interface TComponentProps {
        height: number;
    }

    class TComponent extends React.Component<TComponentProps> {
        private viewport = React.createRef<HTMLDivElement>();

        getSnapshotBeforeUpdate(prevProps) {
            this.fixupJsDom(prevProps.height);
            return autoscroll.isAtBottom(this.viewport);
        }

        componentDidUpdate(prevProps, prevState, snapshot) {
            this.fixupJsDom(this.props.height);
            if (snapshot) {
                autoscroll.adjustScrollTop(this.viewport);
            }
        }

        fixupJsDom(scrollHeight: number) {
            // work around jsdom limitations
            Object.defineProperty(this.viewport.current!, "clientHeight", {
                value: 100,
                writable: true,
            });
            Object.defineProperty(this.viewport.current!, "scrollHeight", {
                value: scrollHeight,
                writable: true,
            });
        }

        render() {
            return <div ref={this.viewport} />;
        }
    }

    it("should update component", () => {
        const { rerender, container } = render(<TComponent height={120} />);
        const viewport = container.firstElementChild!;

        fireEvent.scroll(viewport, { target: { scrollTop: 10 } });
        rerender(<TComponent height={140} />);

        expect(viewport.scrollTop).toBe(10);

        fireEvent.scroll(viewport, { target: { scrollTop: 40 } });
        rerender(<TComponent height={160} />);

        expect(viewport.scrollTop).toBeGreaterThanOrEqual(60);
    });
});

import * as React from "react";
import EventLogList from "../../../components/EventLog/EventList";
import type { EventLogItem } from "../../../ducks/eventLog";
import { LogLevel } from "../../../ducks/eventLog";
import { render } from "../../test-utils";

describe("EventList Component", () => {
    const mockEventList: EventLogItem[] = [
        { id: "1", level: LogLevel.info, message: "foo" },
        { id: "2", level: LogLevel.error, message: "bar" },
    ];

    it("should render correctly", () => {
        const { asFragment, unmount } = render(
            <EventLogList events={mockEventList} />,
        );
        expect(asFragment()).toMatchSnapshot();
        unmount(); // no errors
    });

    it("does not call onViewportUpdate when events and rowHeight are unchanged", () => {
        // Regression guard for an infinite componentDidUpdate -> setState
        // cycle (React "Maximum update depth exceeded" when scrolling the
        // event log). Before the props-comparison gate in componentDidUpdate,
        // onViewportUpdate ran on EVERY update, including the setState the
        // previous call itself produced, so with variable row heights the
        // recomputed vScroll could ping-pong between windows and never
        // converge. The same fix was applied to FlowTable in #8233.
        const spy = jest.spyOn(EventLogList.prototype, "onViewportUpdate");
        const { rerender } = render(<EventLogList events={mockEventList} />);
        spy.mockClear(); // ignore the componentDidMount call

        // Re-render with the same events reference and rowHeight. This
        // triggers componentDidUpdate but changes none of onViewportUpdate's
        // inputs, so it must not run.
        rerender(<EventLogList events={mockEventList} />);
        expect(spy).not.toHaveBeenCalled();

        spy.mockRestore();
    });

    it("calls onViewportUpdate when the events list changes", () => {
        // Complement of the previous test: a new events array must still
        // refresh the virtual-scroll window, otherwise appended log lines
        // would never become visible.
        const spy = jest.spyOn(EventLogList.prototype, "onViewportUpdate");
        const { rerender } = render(<EventLogList events={mockEventList} />);
        spy.mockClear();

        const moreEvents: EventLogItem[] = [
            ...mockEventList,
            { id: "3", level: LogLevel.info, message: "baz" },
        ];
        rerender(<EventLogList events={moreEvents} />);
        expect(spy).toHaveBeenCalled();

        spy.mockRestore();
    });
});

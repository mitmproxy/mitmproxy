import * as React from "react";
import EventLogList from "../../../components/EventLog/EventList";
import TestUtils from "react-dom/test-utils";
import { EventLogItem, LogLevel } from "../../../ducks/eventLog";

describe("EventList Component", () => {
    const mockEventList: EventLogItem[] = [
        { id: "1", level: LogLevel.info, message: "foo" },
        { id: "2", level: LogLevel.error, message: "bar" },
    ];
    const eventLogList = TestUtils.renderIntoDocument(
        <EventLogList events={mockEventList} />,
    );

    it("should render correctly", () => {
        expect(eventLogList.state).toMatchSnapshot();
        expect(eventLogList.props).toMatchSnapshot();
    });

    it("should handle componentWillUnmount", () => {
        window.removeEventListener = jest.fn();
        eventLogList.componentWillUnmount();
        expect(window.removeEventListener).toBeCalledWith(
            "resize",
            eventLogList.onViewportUpdate,
        );
    });
});

import * as React from "react";
import EventLogList from "../../../components/EventLog/EventList";
import { EventLogItem, LogLevel } from "../../../ducks/eventLog";
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
});

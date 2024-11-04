jest.mock("../../components/EventLog/EventList");

import * as React from "react";
import renderer from "react-test-renderer";
import EventLog, { PureEventLog } from "../../components/EventLog";
import { Provider } from "react-redux";
import { TStore } from "../ducks/tutils";

window.addEventListener = jest.fn();
window.removeEventListener = jest.fn();

describe("EventLog Component", () => {
    let store = TStore(),
        provider = renderer.create(
            <Provider store={store}>
                <EventLog />
            </Provider>,
        ),
        tree = provider.toJSON();

    it("should connect to state and render correctly", () => {
        expect(tree).toMatchSnapshot();
    });

    it("should handle toggleFilter", () => {
        const debugToggleButton = tree.children[0].children[1].children[0];
        debugToggleButton.props.onClick();
    });

    provider = renderer.create(
        <Provider store={store}>
            <EventLog />
        </Provider>,
    );
    const eventLog = provider.root.findByType(PureEventLog);
    const mockEvent = { preventDefault: jest.fn() };

    it("should handle DragStart", () => {
        eventLog.instance.onDragStart(mockEvent);
        expect(mockEvent.preventDefault).toBeCalled();
        expect(window.addEventListener).toBeCalledWith(
            "mousemove",
            eventLog.instance.onDragMove,
        );
        expect(window.addEventListener).toBeCalledWith(
            "mouseup",
            eventLog.instance.onDragStop,
        );
        expect(window.addEventListener).toBeCalledWith(
            "dragend",
            eventLog.instance.onDragStop,
        );
        mockEvent.preventDefault.mockClear();
    });

    it("should handle DragMove", () => {
        eventLog.instance.onDragMove(mockEvent);
        expect(mockEvent.preventDefault).toBeCalled();
        mockEvent.preventDefault.mockClear();
    });

    console.error = jest.fn(); // silent the error.
    it("should handle DragStop", () => {
        eventLog.instance.onDragStop(mockEvent);
        expect(mockEvent.preventDefault).toBeCalled();
        expect(window.removeEventListener).toBeCalledWith(
            "mousemove",
            eventLog.instance.onDragMove,
        );
    });
});

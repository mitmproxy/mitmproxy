import * as React from "react";
import FileMenu from "../../../components/Header/FileMenu";
import { Provider } from "react-redux";
import { TStore } from "../../ducks/tutils";
import { fireEvent, render, screen, waitFor } from "../../test-utils";
import { FilterName, setFilter } from "../../../ducks/ui/filter";

describe("FileMenu Component", () => {
    it("should render correctly", () => {
        const store = TStore();
        const { asFragment } = render(
            <Provider store={store}>
                <FileMenu />
            </Provider>,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should use relative URLs when saving flows", async () => {
        const replace = jest.fn();
        const originalLocation = window.location;
        Object.defineProperty(window, "location", {
            configurable: true,
            value: { ...originalLocation, replace },
        });
        try {
            const store = TStore();
            store.dispatch(setFilter("~d example.com & ~c 200"));
            expect(store.getState().ui.filter[FilterName.Search]).toBe(
                "~d example.com & ~c 200",
            );

            render(
                <Provider store={store}>
                    <FileMenu />
                </Provider>,
            );

            fireEvent.click(screen.getByText("File"));
            await waitFor(() => screen.getByText("Save"));
            fireEvent.click(screen.getByText("Save"));
            expect(replace).toHaveBeenCalledWith("./flows/dump");

            fireEvent.click(screen.getByText("File"));
            await waitFor(() => screen.getByText("Save filtered"));
            fireEvent.click(screen.getByText("Save filtered"));
            expect(replace).toHaveBeenCalledWith(
                "./flows/dump?filter=~d%20example.com%20%26%20~c%20200",
            );
        } finally {
            Object.defineProperty(window, "location", {
                configurable: true,
                value: originalLocation,
            });
        }
    });
});

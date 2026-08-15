import * as React from "react";
import OptionMenu from "../../../components/Header/OptionMenu";
import { fireEvent, render, screen, waitFor } from "../../test-utils";
import { enableFetchMocks } from "jest-fetch-mock";
import { TStore, testState } from "../../ducks/tutils";

enableFetchMocks();

const withColumnWidths = () =>
    TStore({
        ...testState,
        ui: { ...testState.ui, columnWidths: { size: 70 } },
    });

describe("OptionMenu Component", () => {
    it("should render correctly", () => {
        const { asFragment } = render(<OptionMenu />);
        expect(asFragment()).toMatchSnapshot();
    });

    it("should update the web_theme option from the theme selector", async () => {
        fetchMock.mockResponseOnce("");

        render(<OptionMenu />);
        fireEvent.change(screen.getByDisplayValue("system"), {
            target: { value: "dark" },
        });

        await waitFor(() =>
            expect(fetchMock).toHaveBeenCalledWith(
                "./options",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({ web_theme: "dark" }),
                }),
            ),
        );
    });

    it("resets the flow table column widths", () => {
        const { store } = render(<OptionMenu />, { store: withColumnWidths() });

        fireEvent.click(screen.getByText("Reset Widths"));

        expect(store.getState().ui.columnWidths).toEqual({});
    });

    it("has nothing to reset until a column is resized", () => {
        render(<OptionMenu />);

        expect(screen.getByText("Reset Widths").closest("button")).toBeDisabled();
    });
});

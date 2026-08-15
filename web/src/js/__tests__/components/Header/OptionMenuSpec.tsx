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

        fireEvent.click(screen.getByText("Reset Column Widths"));

        expect(store.getState().ui.columnWidths).toEqual({});
    });

    it("has nothing to reset until a column is resized", () => {
        render(<OptionMenu />);

        expect(
            screen.getByText("Reset Column Widths").closest("button"),
        ).toBeDisabled();
    });

    it("lists the flow table columns behind the Columns dropdown, closed by default", () => {
        render(<OptionMenu />);

        expect(screen.queryByText("Start time")).not.toBeInTheDocument();

        fireEvent.click(screen.getByText("Columns"));

        // "timestamp" is not in the default web_columns; "method" is.
        expect(screen.getByLabelText("Start time")).not.toBeChecked();
        expect(screen.getByLabelText("Method")).toBeChecked();
    });

    it("unchecking a column removes it from web_columns", async () => {
        fetchMock.mockResponseOnce("");
        render(<OptionMenu />);
        fireEvent.click(screen.getByText("Columns"));

        fireEvent.click(screen.getByLabelText("Method"));

        await waitFor(() =>
            expect(fetchMock).toHaveBeenCalledWith(
                "./options",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({
                        web_columns: [
                            "tls",
                            "icon",
                            "path",
                            "status",
                            "size",
                            "time",
                        ],
                    }),
                }),
            ),
        );
    });

    it("checking a column re-adds it to web_columns in the default order", async () => {
        fetchMock.mockResponseOnce("");
        render(<OptionMenu />);
        fireEvent.click(screen.getByText("Columns"));

        fireEvent.click(screen.getByLabelText("Start time"));

        await waitFor(() =>
            expect(fetchMock).toHaveBeenCalledWith(
                "./options",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({
                        web_columns: [
                            "tls",
                            "icon",
                            "path",
                            "method",
                            "status",
                            "size",
                            "time",
                            "timestamp",
                        ],
                    }),
                }),
            ),
        );
    });

    it("does not let the last visible column be unchecked", () => {
        const store = TStore({
            ...testState,
            options: { ...testState.options, web_columns: ["path"] },
        });
        render(<OptionMenu />, { store });
        fireEvent.click(screen.getByText("Columns"));

        expect(screen.getByLabelText("Path")).toBeDisabled();
    });
});

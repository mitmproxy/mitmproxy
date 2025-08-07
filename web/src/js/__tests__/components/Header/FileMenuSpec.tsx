import React from "react";
import FileMenu from "../../../components/Header/FileMenu";
import { Provider } from "react-redux";
import { TStore } from "../../ducks/tutils";
import { act, fireEvent, render, screen } from "../../test-utils";
import * as flowsActions from "../../../ducks/flows";
import { fetchApi } from "../../../utils";

jest.mock("../../../utils");

describe("FileMenu Component", () => {
    let store;

    beforeEach(() => {
        store = TStore();
        jest.resetAllMocks();
    });

    it("should render correctly", () => {
        const { asFragment } = render(
            <Provider store={store}>
                <FileMenu />
            </Provider>,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    describe("File menu interactions", () => {
        let confirmMock;

        beforeEach(() => {
            confirmMock = jest.spyOn(window, "confirm").mockReturnValue(true);
        });

        afterEach(() => {
            confirmMock.mockRestore();
        });

        it("should clear all the flows", async () => {
            render(
                <Provider store={store}>
                    <FileMenu />
                </Provider>,
            );

            await act(() => fireEvent.click(screen.getByText("File")));

            // Click Clear All and assert side effects
            fireEvent.click(screen.getByText("Clear All"));
            expect(confirmMock).toHaveBeenCalled();
            await store.dispatch(flowsActions.clear());
            expect(fetchApi).toHaveBeenCalledWith("/clear", { method: "POST" });
        });

        it("it should trigger file upload correctly", async () => {
            render(
                <Provider store={store}>
                    <FileMenu />
                </Provider>,
            );

            await act(() => fireEvent.click(screen.getByText("File")));

            // Click Open... and dispatch upload
            fireEvent.click(screen.getByText("Open..."));
            const fileInput = document.querySelector('input[type="file"]');
            expect(fileInput).toBeTruthy();

            const dummyFile = new File(["dummy content"], "dummy.txt", {
                type: "text/plain",
            });

            // Simulate selecting a file
            await act(() =>
                fireEvent.change(fileInput as Element, {
                    target: { files: [dummyFile] },
                }),
            );

            expect(fetchApi).toHaveBeenCalledWith(
                "/flows/dump",
                expect.objectContaining({
                    method: "POST",
                    body: expect.any(FormData),
                }),
            );
        });

        it("should display save filename prompt and trigger anchor click to save file", async () => {
            const promptMock = jest
                .spyOn(window, "prompt")
                .mockReturnValue("myfile");
            const clickMock = jest.fn();
            const originalCreateElement = document.createElement.bind(document);

            jest.spyOn(document, "createElement").mockImplementation(
                (tagName) => {
                    const element = originalCreateElement(tagName);
                    if (tagName === "a") {
                        element.click = clickMock;
                    }
                    return element;
                },
            );

            render(
                <Provider store={store}>
                    <FileMenu />
                </Provider>,
            );

            await act(() => fireEvent.click(screen.getByText("File")));
            fireEvent.click(screen.getByText("Save"));

            expect(promptMock).toHaveBeenCalledWith("Enter filename", "flows");
            expect(clickMock).toHaveBeenCalled();

            promptMock.mockRestore();
        });
    });
});

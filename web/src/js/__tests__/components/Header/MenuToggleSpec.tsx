import * as React from "react";
import renderer from "react-test-renderer";
import {
    EventlogToggle,
    MenuToggle,
    OptionsToggle,
} from "../../../components/Header/MenuToggle";
import { fireEvent, render, screen, waitFor } from "../../test-utils";

import { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

describe("MenuToggle Component", () => {
    it("should render correctly", () => {
        const changeFn = jest.fn();
        const menuToggle = renderer.create(
            <MenuToggle onChange={changeFn} value={true}>
                <p>foo children</p>
            </MenuToggle>,
        );
        const tree = menuToggle.toJSON();
        expect(tree).toMatchSnapshot();
    });
});

test("OptionsToggle", async () => {
    fetchMock.mockReject(new Error("backend missing"));

    const { asFragment, store } = render(
        <OptionsToggle name="anticache">toggle anticache</OptionsToggle>,
    );

    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("toggle anticache"));

    await waitFor(() =>
        expect(store.getState().ui.optionsEditor.anticache?.error).toContain(
            "backend missing",
        ),
    );
});

test("EventlogToggle", async () => {
    const { asFragment, store } = render(<EventlogToggle />);
    expect(asFragment()).toMatchSnapshot();

    expect(store.getState().eventLog.visible).toBeTruthy();
    fireEvent.click(screen.getByText("Display Event Log"));

    expect(store.getState().eventLog.visible).toBeFalsy();
});

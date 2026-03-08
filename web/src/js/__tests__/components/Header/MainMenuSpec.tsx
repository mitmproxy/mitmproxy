import * as React from "react";
import FlowListMenu, {
    ClearAll,
} from "../../../components/Header/FlowListMenu";
import { fireEvent, render, screen } from "../../test-utils";
import { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

test("MainMenu", () => {
    const { asFragment } = render(<FlowListMenu />);
    expect(asFragment()).toMatchSnapshot();
});

test("ClearAll dispatches clear action", async () => {
    fetchMock.mockOnce("", { status: 200 });

    render(<ClearAll />);
    fireEvent.click(screen.getByText("Clear All"));

    expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/clear"),
        expect.objectContaining({ method: "POST" }),
    );
});

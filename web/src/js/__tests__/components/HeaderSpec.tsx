import * as React from "react";
import { act, fireEvent, render, screen } from "../test-utils";
import Header from "../../components/Header";

test("Header", async () => {
    const { asFragment } = render(<Header />);
    expect(asFragment()).toMatchSnapshot();

    await act(() => fireEvent.click(screen.getByText("Options")));
    expect(asFragment()).toMatchSnapshot();
    expect(screen.getByText("Edit Options")).toBeTruthy();

    await act(() => fireEvent.click(screen.getByText("File")));
    expect(asFragment()).toMatchSnapshot();
    expect(screen.getByText("Open...")).toBeTruthy();

    await act(() => fireEvent.click(screen.getByText("File")));
    expect(screen.queryByText("Open...")).toBeNull();

    await act(() => fireEvent.click(screen.getByText("Capture")));
    expect(asFragment()).toMatchSnapshot();
});

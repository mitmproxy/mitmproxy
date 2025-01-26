import * as React from "react";
import { fireEvent, render, screen } from "../test-utils";
import Header from "../../components/Header";

test("Header", async () => {
    const { asFragment } = render(<Header />);

    expect(asFragment()).toMatchSnapshot();

    fireEvent.click(screen.getByText("Options"));
    expect(asFragment()).toMatchSnapshot();
    expect(screen.getByText("Edit Options")).toBeTruthy();

    fireEvent.click(screen.getByText("File"));
    expect(asFragment()).toMatchSnapshot();
    expect(screen.getByText("Open...")).toBeTruthy();

    fireEvent.click(screen.getByText("File"));
    expect(screen.queryByText("Open...")).toBeNull();

    fireEvent.click(screen.getByText("Capture"));
    expect(asFragment()).toMatchSnapshot();
});

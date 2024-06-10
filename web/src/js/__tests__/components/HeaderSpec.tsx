import * as React from "react";
import { render, screen, fireEvent } from "../test-utils";
import Header from "../../components/Header";
import OptionMenu from "../../components/Header/OptionMenu";

test("Header", async () => {
    const { asFragment } = render(
        <Header ActiveMenu={OptionMenu} setActiveMenu={jest.fn()} />
    );

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

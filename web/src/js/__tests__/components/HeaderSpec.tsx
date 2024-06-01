import * as React from "react";
import { render, screen, fireEvent } from "../test-utils";
import Header from "../../components/Header";
import { TabMenuProvider } from "../../context/useTabMenuContext";

test("Header", async () => {
    // Wrap Header with TabMenuProvider
    const { asFragment } = render(
        <TabMenuProvider>
            <Header />
        </TabMenuProvider>
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
});

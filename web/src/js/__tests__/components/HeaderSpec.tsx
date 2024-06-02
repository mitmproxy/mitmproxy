import * as React from "react";
import { render, screen, fireEvent } from "../test-utils";
import Header from "../../components/Header";
import {
    TabMenuProvider,
    useTabMenuContext,
} from "../../context/useTabMenuContext";

test("Header", async () => {
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

    fireEvent.click(screen.getByText("Capture"));
    expect(asFragment()).toMatchSnapshot();
});

// Error component to test useTabMenuContext outside of TabMenuProvider
const ErrorComponent = () => {
    try {
        useTabMenuContext();
    } catch (error) {
        return <div>{error.message}</div>;
    }
    return null;
};

test("useTabMenuContext throws error when used outside TabMenuProvider", () => {
    const consoleError = jest
        .spyOn(console, "error")
        .mockImplementation(() => {});

    render(<ErrorComponent />);

    expect(
        screen.getByText(
            "useTabMenuContext must be used within a TabMenuProvider"
        )
    ).toBeInTheDocument();

    consoleError.mockRestore();
});

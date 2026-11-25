import * as React from "react";
import OptionModal, {
    PureOptionDefault,
} from "../../../components/Modal/OptionModal";
import { fireEvent, render, screen } from "../../test-utils";
import { TStore, testState } from "../../ducks/tutils";

describe("OptionModal Component", () => {
    it("leaves the flow table columns to the column picker", () => {
        const store = TStore({
            ...testState,
            options_meta: {
                ...testState.options_meta,
                web_columns: {
                    type: "sequence of str",
                    default: ["path", "method"],
                    value: ["path", "method"],
                    help: "Columns to show in the flow list",
                    choices: undefined,
                },
            },
        });
        render(<OptionModal />, { store });

        expect(screen.getByText("anticache")).toBeInTheDocument();
        expect(screen.queryByText("web_columns")).not.toBeInTheDocument();
    });

    it("filters options by name and help text", () => {
        render(<OptionModal />);
        const search = screen.getByLabelText("Search options");

        // Match by option name (case-insensitive)
        fireEvent.change(search, { target: { value: "LISTEN" } });
        expect(screen.getByText("listen_port")).toBeInTheDocument();
        expect(screen.queryByText("anticache")).not.toBeInTheDocument();

        // Match by help text
        fireEvent.change(search, { target: { value: "304-not-modified" } });
        expect(screen.getByText("anticache")).toBeInTheDocument();
        expect(screen.queryByText("listen_port")).not.toBeInTheDocument();

        // Match multiple space-separated terms across name and help
        fireEvent.change(search, { target: { value: "proxy port" } });
        expect(screen.getByText("listen_port")).toBeInTheDocument();
        expect(screen.queryByText("anticache")).not.toBeInTheDocument();

        // Empty state when nothing matches
        fireEvent.change(search, { target: { value: "nonexistent_option" } });
        expect(screen.getByText("No matching options.")).toBeInTheDocument();
    });

    it("clears the search input via the clear button and keeps focus", () => {
        render(<OptionModal />);
        const search = screen.getByLabelText(
            "Search options",
        ) as HTMLInputElement;

        expect(screen.queryByLabelText("Clear search")).not.toBeInTheDocument();

        fireEvent.change(search, { target: { value: "listen" } });
        const clearBtn = screen.getByLabelText("Clear search");
        expect(clearBtn).toBeInTheDocument();

        fireEvent.mouseDown(clearBtn);
        fireEvent.click(clearBtn);

        expect(search.value).toBe("");
        expect(search).toHaveFocus();
        expect(screen.queryByLabelText("Clear search")).not.toBeInTheDocument();
        expect(screen.getByText("anticache")).toBeInTheDocument();
        expect(screen.getByText("listen_port")).toBeInTheDocument();
    });

    it("stops non-Escape keys and clears active search on Escape before letting Escape bubble", () => {
        const parentKeyDown = jest.fn();
        render(
            <div onKeyDown={parentKeyDown}>
                <OptionModal />
            </div>,
        );
        const search = screen.getByLabelText(
            "Search options",
        ) as HTMLInputElement;

        // Regular keys must not bubble to global flow shortcuts.
        fireEvent.keyDown(search, { key: "d" });
        expect(parentKeyDown).not.toHaveBeenCalled();

        // First Escape with non-empty query clears the search without bubbling.
        fireEvent.change(search, { target: { value: "listen" } });
        fireEvent.keyDown(search, { key: "Escape" });
        expect(search.value).toBe("");
        expect(parentKeyDown).not.toHaveBeenCalled();

        // Keys on the clear button must not bubble to global shortcuts,
        // and Escape on it clears the query and returns focus to the input.
        fireEvent.change(search, { target: { value: "listen" } });
        const clearBtn = screen.getByLabelText("Clear search");
        clearBtn.focus();
        fireEvent.keyDown(clearBtn, { key: " " });
        expect(parentKeyDown).not.toHaveBeenCalled();
        fireEvent.keyDown(clearBtn, { key: "Escape" });
        expect(search.value).toBe("");
        expect(search).toHaveFocus();
        expect(parentKeyDown).not.toHaveBeenCalled();

        // Second Escape with empty query bubbles so the global handler closes the modal.
        fireEvent.keyDown(search, { key: "Escape" });
        expect(parentKeyDown).toHaveBeenCalledTimes(1);
    });
});

describe("PureOptionDefault Component", () => {
    it("should return null when the value is default", () => {
        const { asFragment } = render(
            <PureOptionDefault value="foo" defaultVal="foo" />,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should handle boolean type", () => {
        const { asFragment } = render(
            <PureOptionDefault value={true} defaultVal={false} />,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should handle array", () => {
        let a = [""],
            b = [],
            c = ["c"],
            { asFragment } = render(
                <PureOptionDefault value={a} defaultVal={b} />,
            );
        expect(asFragment()).toMatchSnapshot();

        asFragment = render(
            <PureOptionDefault value={a} defaultVal={c} />,
        ).asFragment;
        expect(asFragment()).toMatchSnapshot();
    });

    it("should handle string", () => {
        const { asFragment } = render(
            <PureOptionDefault value="foo" defaultVal="" />,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should handle null value", () => {
        const { asFragment } = render(
            <PureOptionDefault value="foo" defaultVal={null} />,
        );
        expect(asFragment()).toMatchSnapshot();
    });
});

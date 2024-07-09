import * as React from "react";
import { render, screen, userEvent, waitFor } from "../test-utils";
import CommandBar from "../../components/CommandBar";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";

enableFetchMocks();

test("CommandBar", async () => {
    fetchMock.mockOnceIf(
        "./commands",
        JSON.stringify({
            "flow.decode": {
                help: "Decode flows.",
                parameters: [
                    {
                        name: "flows",
                        type: "flow[]",
                        kind: "POSITIONAL_OR_KEYWORD",
                    },
                    {
                        name: "part",
                        type: "str",
                        kind: "POSITIONAL_OR_KEYWORD",
                    },
                ],
                return_type: null,
                signature_help: "flow.decode flows part",
            },
            "flow.encode": {
                help: "Encode flows with a specified encoding.",
                parameters: [
                    {
                        name: "flows",
                        type: "flow[]",
                        kind: "POSITIONAL_OR_KEYWORD",
                    },
                    {
                        name: "part",
                        type: "str",
                        kind: "POSITIONAL_OR_KEYWORD",
                    },
                    {
                        name: "encoding",
                        type: "choice",
                        kind: "POSITIONAL_OR_KEYWORD",
                    },
                ],
                return_type: null,
                signature_help: "flow.encode flows part encoding",
            },
        }),
    );
    fetchMock.mockOnceIf(
        "./commands/commands.history.get",
        JSON.stringify({ value: ["foo"] }),
    );
    fetchMock.mockOnceIf(
        "./commands/commands.history.add",
        JSON.stringify({ value: null }),
    );
    fetchMock.mockOnceIf(
        "./commands/flow.encode",
        JSON.stringify({ value: null }),
    );

    const { asFragment } = render(<CommandBar />);
    expect(asFragment()).toMatchSnapshot();
    await waitFor(() => screen.getByText('["flow.decode","flow.encode"]'));
    expect(asFragment()).toMatchSnapshot();

    const input = screen.getByPlaceholderText("Enter command");

    await userEvent.type(input, "x");
    expect(screen.getByText("[]")).toBeInTheDocument();
    await userEvent.type(input, "{backspace}");

    await userEvent.type(input, "fl");
    await userEvent.tab();
    expect(input).toHaveValue("flow.decode");
    await userEvent.tab();
    expect(input).toHaveValue("flow.encode");

    fetchMock.mockOnce(JSON.stringify({ value: null }));
    await userEvent.type(input, "{enter}");
    await waitFor(() => screen.getByText("Command Result"));

    await userEvent.type(input, "{arrowdown}");
    expect(input).toHaveValue("");

    await userEvent.type(input, "{arrowup}");
    expect(input).toHaveValue("flow.encode");
    await userEvent.type(input, "{arrowup}");
    expect(input).toHaveValue("foo");
    await userEvent.type(input, "{arrowdown}");
    expect(input).toHaveValue("flow.encode");
    await userEvent.type(input, "{arrowdown}");
    expect(input).toHaveValue("");
});

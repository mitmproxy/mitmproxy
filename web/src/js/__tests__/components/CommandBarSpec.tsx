import * as React from "react"
import {render, screen, userEvent, waitFor} from "../test-utils";
import CommandBar from "../../components/CommandBar";
import fetchMock, {enableFetchMocks} from "jest-fetch-mock";

enableFetchMocks();

test("CommandBar", async () => {
    fetchMock.mockOnceIf("./commands", JSON.stringify({
            "flow.decode": {
                "help": "Decode flows.",
                "parameters": [
                    {"name": "flows", "type": "flow[]", "kind": "POSITIONAL_OR_KEYWORD"},
                    {"name": "part", "type": "str", "kind": "POSITIONAL_OR_KEYWORD"}
                ],
                "return_type": null,
                "signature_help": "flow.decode flows part"
            },
            "flow.encode": {
                "help": "Encode flows with a specified encoding.",
                "parameters": [
                    {"name": "flows", "type": "flow[]", "kind": "POSITIONAL_OR_KEYWORD"},
                    {"name": "part", "type": "str", "kind": "POSITIONAL_OR_KEYWORD"},
                    {"name": "encoding", "type": "choice", "kind": "POSITIONAL_OR_KEYWORD"}
                ],
                "return_type": null,
                "signature_help": "flow.encode flows part encoding"
            }
        }
    ));
    fetchMock.mockOnceIf("./commands/commands.history.get", JSON.stringify({value: ["foo"]}));
    fetchMock.mockOnceIf("./commands/commands.history.add", JSON.stringify({value: null}));
    fetchMock.mockOnceIf("./commands/flow.encode", JSON.stringify({value: null}));

    const {asFragment} = render(<CommandBar/>);
    expect(asFragment()).toMatchSnapshot();
    await waitFor(() => screen.getByText('["flow.decode","flow.encode"]'))
    expect(asFragment()).toMatchSnapshot();

    const input = screen.getByPlaceholderText("Enter command");

    userEvent.type(input, 'x');
    expect(screen.getByText("[]")).toBeInTheDocument();
    userEvent.type(input, "{backspace}");

    userEvent.type(input, 'fl');
    userEvent.tab();
    expect(input).toHaveValue('flow.decode');
    userEvent.tab();
    expect(input).toHaveValue('flow.encode');

    fetchMock.mockOnce(JSON.stringify({value: null}));
    userEvent.type(input, "{enter}");
    await waitFor(() => screen.getByText("Command Result"));

    userEvent.type(input, "{arrowdown}");
    expect(input).toHaveValue("");

    userEvent.type(input, "{arrowup}");
    expect(input).toHaveValue("flow.encode");
    userEvent.type(input, "{arrowup}");
    expect(input).toHaveValue("foo");
    userEvent.type(input, "{arrowdown}");
    expect(input).toHaveValue("flow.encode");
    userEvent.type(input, "{arrowdown}");
    expect(input).toHaveValue("");
});

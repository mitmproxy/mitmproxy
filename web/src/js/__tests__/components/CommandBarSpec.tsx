import * as React from "react"
import {render, waitFor, screen} from "../test-utils";
import CommandBar from "../../components/CommandBar";
import fetchMock, {enableFetchMocks} from "jest-fetch-mock";

enableFetchMocks();

test("CommandBar", async () => {
    fetchMock.mockResponseOnce(JSON.stringify({
            "flow.decode": {"help": "Decode flows.",
                "parameters": [{"name": "flows", "type": "flow[]", "kind": "POSITIONAL_OR_KEYWORD"}, {
                    "name": "part",
                    "type": "str",
                    "kind": "POSITIONAL_OR_KEYWORD"
                }],
                "return_type": null,
                "signature_help": "flow.decode flows part"
            }
        }
    ));

    const {asFragment} = render(<CommandBar/>);
    expect(asFragment()).toMatchSnapshot();
    await waitFor(() => screen.getByText('["flow.decode"]'))
    expect(asFragment()).toMatchSnapshot();
});

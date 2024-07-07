import * as React from "react";
import { render } from "../../test-utils";
import { TStore } from "../../ducks/tutils";
import Regular from "../../../components/Modes/Regular";
import * as backendState from "../../../ducks/backendState";

test("RegularSpec", async () => {
    const store = TStore();
    const { asFragment } = render(<Regular />, { store });

    expect(asFragment()).toMatchSnapshot();

    store.dispatch(
        backendState.mockUpdate({
            servers: [
                {
                    description: "Regular Mode",
                    full_spec: "regular",
                    is_running: false,
                    last_exception: "port already in use",
                    listen_addrs: [],
                    type: "regular",
                },
            ],
        }),
    );

    expect(asFragment()).toMatchSnapshot();
});

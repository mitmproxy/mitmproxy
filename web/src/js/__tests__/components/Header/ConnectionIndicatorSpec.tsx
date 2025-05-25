import * as React from "react";
import ConnectionIndicator from "../../../components/Header/ConnectionIndicator";
import * as connectionActions from "../../../ducks/connection";
import { act, render } from "../../test-utils";
import { TStore } from "../../ducks/tutils";

test("ConnectionIndicator", async () => {
    const { asFragment, store } = render(<ConnectionIndicator />, {
        store: TStore(null),
    });
    expect(asFragment()).toMatchSnapshot();

    act(() => store.dispatch(connectionActions.startFetching()));
    expect(asFragment()).toMatchSnapshot();

    act(() => store.dispatch(connectionActions.finishFetching()));
    expect(asFragment()).toMatchSnapshot();

    act(() => store.dispatch(connectionActions.connectionError("wat")));
    expect(asFragment()).toMatchSnapshot();
});

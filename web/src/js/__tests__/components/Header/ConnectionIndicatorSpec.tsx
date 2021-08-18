import * as React from "react"
import ConnectionIndicator from '../../../components/Header/ConnectionIndicator'
import * as connectionActions from '../../../ducks/connection'
import {render} from "../../test-utils"


test("ConnectionIndicator", async () => {
    const {asFragment, store} = render(<ConnectionIndicator/>);
    expect(asFragment()).toMatchSnapshot()

    store.dispatch(connectionActions.startFetching())
    expect(asFragment()).toMatchSnapshot()

    store.dispatch(connectionActions.connectionEstablished())
    expect(asFragment()).toMatchSnapshot()

    store.dispatch(connectionActions.connectionError("wat"))
    expect(asFragment()).toMatchSnapshot()

    store.dispatch(connectionActions.setOffline())
    expect(asFragment()).toMatchSnapshot()
});

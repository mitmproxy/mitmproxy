import * as React from "react"
import {render} from "../test-utils";
import CaptureSetup from "../../components/CaptureSetup";
import {TStore} from "../ducks/tutils";


test("CaptureSetup", async () => {
    const store = TStore(),
        {asFragment} = render(<CaptureSetup/>, {store});
    expect(asFragment()).toMatchSnapshot();
});

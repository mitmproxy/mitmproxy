import * as React from "react";
import { render } from "../../test-utils";
import CaptureSetup from "../../../components/Modes/CaptureSetup";
import { TStore } from "../../ducks/tutils";

test("CaptureSetup", async () => {
    const store = TStore();
    const { asFragment } = render(<CaptureSetup />, { store });
    expect(asFragment()).toMatchSnapshot();
});

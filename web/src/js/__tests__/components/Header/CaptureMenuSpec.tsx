import * as React from "react";
import renderer from "react-test-renderer";
import { Provider } from "react-redux";
import OptionMenu from "../../../components/Header/OptionMenu";
import { TStore } from "../../ducks/tutils";
import CaptureMenu from "../../../components/Header/CaptureMenu";

describe("CaptureMenu Component", () => {
    it("should render correctly", () => {
        let store = TStore(),
            provider = renderer.create(
                <Provider store={store}>
                    <CaptureMenu />
                </Provider>
            ),
            tree = provider.toJSON();
        expect(tree).toMatchSnapshot();
    });
});

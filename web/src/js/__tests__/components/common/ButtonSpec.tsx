import * as React from "react";
import renderer from "react-test-renderer";
import Button from "../../../components/common/Button";

describe("Button Component", () => {
    it("should render correctly", () => {
        const button = renderer.create(
            <Button
                className="classname"
                onClick={() => "onclick"}
                title="title"
                icon="icon"
            >
                <a>foo</a>
            </Button>,
        );
        const tree = button.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should be able to be disabled", () => {
        const button = renderer.create(
            <Button className="classname" onClick={() => "onclick"} disabled>
                <a>foo</a>
            </Button>,
        );
        const tree = button.toJSON();
        expect(tree).toMatchSnapshot();
    });
});

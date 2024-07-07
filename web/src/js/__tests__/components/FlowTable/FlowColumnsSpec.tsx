import * as React from "react";
import renderer from "react-test-renderer";
import FlowColumns from "../../../components/FlowTable/FlowColumns";
import { TFlow, TTCPFlow } from "../../ducks/tutils";
import { render } from "../../test-utils";

test("should render columns", async () => {
    const tflow = TFlow();
    Object.entries(FlowColumns).forEach(([name, Col]) => {
        const { asFragment } = render(
            <table>
                <tbody>
                    <tr>
                        <Col flow={tflow} />
                    </tr>
                </tbody>
            </table>,
        );
        expect(asFragment()).toMatchSnapshot(name);
    });
});

describe("Flowcolumns Components", () => {
    it("should render IconColumn", () => {
        let tcpflow = TTCPFlow(),
            iconColumn = renderer.create(<FlowColumns.icon flow={tcpflow} />),
            tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();

        const tflow = { ...TFlow(), websocket: undefined };
        iconColumn = renderer.create(<FlowColumns.icon flow={tflow} />);
        tree = iconColumn.toJSON();
        // plain
        expect(tree).toMatchSnapshot();
        // not modified
        tflow.response.status_code = 304;
        iconColumn = renderer.create(<FlowColumns.icon flow={tflow} />);
        tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();
        // redirect
        tflow.response.status_code = 302;
        iconColumn = renderer.create(<FlowColumns.icon flow={tflow} />);
        tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();
        // image
        const imageFlow = { ...TFlow(), websocket: undefined };
        imageFlow.response.headers = [["Content-Type", "image/jpeg"]];
        iconColumn = renderer.create(<FlowColumns.icon flow={imageFlow} />);
        tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();
        // javascript
        const jsFlow = { ...TFlow(), websocket: undefined };
        jsFlow.response.headers = [
            ["Content-Type", "application/x-javascript"],
        ];
        iconColumn = renderer.create(<FlowColumns.icon flow={jsFlow} />);
        tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();
        // css
        const cssFlow = { ...TFlow(), websocket: undefined };
        cssFlow.response.headers = [["Content-Type", "text/css"]];
        iconColumn = renderer.create(<FlowColumns.icon flow={cssFlow} />);
        tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();
        // html
        const htmlFlow = { ...TFlow(), websocket: undefined };
        htmlFlow.response.headers = [["Content-Type", "text/html"]];
        iconColumn = renderer.create(<FlowColumns.icon flow={htmlFlow} />);
        tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();
        // default
        const fooFlow = { ...TFlow(), websocket: undefined };
        fooFlow.response.headers = [["Content-Type", "foo"]];
        iconColumn = renderer.create(<FlowColumns.icon flow={fooFlow} />);
        tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();
        // no response
        const noResponseFlow = { ...TFlow(), response: undefined };
        iconColumn = renderer.create(
            <FlowColumns.icon flow={noResponseFlow} />,
        );
        tree = iconColumn.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should render pathColumn", () => {
        let tflow = TFlow(),
            pathColumn = renderer.create(<FlowColumns.path flow={tflow} />),
            tree = pathColumn.toJSON();
        expect(tree).toMatchSnapshot();

        tflow.error.msg = "Connection killed.";
        tflow.intercepted = true;
        pathColumn = renderer.create(<FlowColumns.path flow={tflow} />);
        tree = pathColumn.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should render TimeColumn", () => {
        let tflow = TFlow(),
            timeColumn = renderer.create(<FlowColumns.time flow={tflow} />),
            tree = timeColumn.toJSON();
        expect(tree).toMatchSnapshot();

        const noResponseFlow = { ...tflow, response: undefined };
        timeColumn = renderer.create(
            <FlowColumns.time flow={noResponseFlow} />,
        );
        tree = timeColumn.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should render CommentColumn", () => {
        const tflow = TFlow();
        const commentColumn = renderer.create(
            <FlowColumns.comment flow={tflow} />,
        );
        const tree = commentColumn.toJSON();
        expect(tree).toMatchSnapshot();
    });
});

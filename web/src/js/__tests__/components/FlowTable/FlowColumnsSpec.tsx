import * as React from "react";
import FlowColumns from "../../../components/FlowTable/FlowColumns";
import { TFlow, TTCPFlow } from "../../ducks/tutils";
import { render } from "../../test-utils";
import { Flow } from "../../../flow";

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
    function testFlowColumn(elem) {
        const { asFragment } = render(
            <table>
                <tbody>
                    <tr>{elem}</tr>
                </tbody>
            </table>,
        );
        expect(asFragment()).toMatchSnapshot();
    }

    it("should render IconColumn", () => {
        const testIconColumn = (flow: Flow) =>
            testFlowColumn(<FlowColumns.icon flow={flow} />);

        // TCP
        let tcpflow = TTCPFlow();
        testIconColumn(tcpflow);
        // plain
        const tflow = { ...TFlow(), websocket: undefined };
        testIconColumn(tflow);
        // not modified
        tflow.response.status_code = 304;
        testIconColumn(tflow);
        // redirect
        tflow.response.status_code = 302;
        testIconColumn(tflow);
        // image
        const imageFlow = { ...TFlow(), websocket: undefined };
        imageFlow.response.headers = [["Content-Type", "image/jpeg"]];
        testIconColumn(imageFlow);
        // javascript
        const jsFlow = { ...TFlow(), websocket: undefined };
        jsFlow.response.headers = [
            ["Content-Type", "application/x-javascript"],
        ];
        testIconColumn(jsFlow);
        // css
        const cssFlow = { ...TFlow(), websocket: undefined };
        cssFlow.response.headers = [["Content-Type", "text/css"]];
        testIconColumn(cssFlow);
        // html
        const htmlFlow = { ...TFlow(), websocket: undefined };
        htmlFlow.response.headers = [["Content-Type", "text/html"]];
        testIconColumn(htmlFlow);
        // default
        const fooFlow = { ...TFlow(), websocket: undefined };
        fooFlow.response.headers = [["Content-Type", "foo"]];
        testIconColumn(fooFlow);
        // no response
        const noResponseFlow = { ...TFlow(), response: undefined };
        testIconColumn(noResponseFlow);
    });

    it("should render pathColumn", () => {
        let tflow = TFlow();
        testFlowColumn(<FlowColumns.path flow={tflow} />);

        tflow.error.msg = "Connection killed.";
        tflow.intercepted = true;
        testFlowColumn(<FlowColumns.path flow={tflow} />);
    });

    it("should render TimeColumn", () => {
        let tflow = TFlow();
        testFlowColumn(<FlowColumns.time flow={tflow} />);

        const noResponseFlow = { ...tflow, response: undefined };
        testFlowColumn(<FlowColumns.time flow={noResponseFlow} />);
    });

    it("should render CommentColumn", () => {
        const tflow = TFlow();
        testFlowColumn(<FlowColumns.comment flow={tflow} />);
    });
});

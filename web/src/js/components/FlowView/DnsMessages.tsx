import * as React from "react";

import { useAppSelector } from "../../ducks";
import { DNSFlow, DNSMessage, DNSResourceRecord } from "../../flow";

const Summary: React.FC<{
    message: DNSMessage;
}> = ({ message }) => (
    <div>
        {message.query ? message.op_code : message.response_code}
        &nbsp;
        {message.truncation ? "(Truncated)" : ""}
    </div>
);

const Questions: React.FC<{
    message: DNSMessage;
}> = ({ message }) => (
    <>
        <h5>{message.recursion_desired ? "Recursive " : ""}Question</h5>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Class</th>
                </tr>
            </thead>
            <tbody>
                {message.questions.map((question, index) => (
                    <tr key={index}>
                        <td>{question.name}</td>
                        <td>{question.type}</td>
                        <td>{question.class}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    </>
);

const ResourceRecords: React.FC<{
    name: string;
    values: DNSResourceRecord[];
}> = ({ name, values }) => (
    <>
        <h5>{name}</h5>
        {values.length > 0 ? (
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Class</th>
                        <th>TTL</th>
                        <th>Data</th>
                    </tr>
                </thead>
                <tbody>
                    {values.map((rr, index) => (
                        <tr key={index}>
                            <td>{rr.name}</td>
                            <td>{rr.type}</td>
                            <td>{rr.class}</td>
                            <td>{rr.ttl}</td>
                            <td>
                                {JSON.stringify(rr.data).replace(/^"|"$/g, "")}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        ) : (
            "—"
        )}
    </>
);

const Message: React.FC<{
    type: "request" | "response";
    message: DNSMessage;
}> = ({ type, message }) => (
    <section className={"dns-" + type}>
        <div className={`first-line ${type}-line`}>
            <Summary message={message} />
        </div>
        <Questions message={message} />
        <hr />
        <ResourceRecords
            name={`${message.authoritative_answer ? "Authoritative " : ""}${
                message.recursion_available ? "Recursive " : ""
            }Answer`}
            values={message.answers}
        />
        <hr />
        <ResourceRecords name="Authority" values={message.authorities} />
        <hr />
        <ResourceRecords name="Additional" values={message.additionals} />
    </section>
);

export function Request() {
    const flow = useAppSelector((state) => state.flows.selected[0]) as DNSFlow;
    return <Message type="request" message={flow.request} />;
}

Request.displayName = "Request";

export function Response() {
    const flow = useAppSelector(
        (state) => state.flows.selected[0],
    ) as DNSFlow & { response: DNSMessage };
    return <Message type="response" message={flow.response} />;
}

Response.displayName = "Response";

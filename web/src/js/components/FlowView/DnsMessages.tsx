import * as React from "react";
import { useTranslation } from "react-i18next";
import { useAppSelector } from "../../ducks";
import type { DNSFlow, DNSMessage, DNSResourceRecord } from "../../flow";

const Summary: React.FC<{
    message: DNSMessage;
}> = ({ message }) => {
    const { t } = useTranslation();
    return (
        <div>
            {message.query ? message.op_code : message.response_code}
            &nbsp;
            {message.truncation ? t("flowView.dnsMessages.truncated") : ""}
        </div>
    );
};

const Questions: React.FC<{
    message: DNSMessage;
}> = ({ message }) => {
    const { t } = useTranslation();
    return (
        <>
            <h5>
                {message.recursion_desired
                    ? t("flowView.dnsMessages.recursiveQuestion")
                    : t("flowView.dnsMessages.question")}
            </h5>
            <table>
                <thead>
                    <tr>
                        <th>{t("flowView.dnsMessages.name")}</th>
                        <th>{t("flowView.dnsMessages.type")}</th>
                        <th>{t("flowView.dnsMessages.class")}</th>
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
};

const ResourceRecords: React.FC<{
    name: string;
    values: DNSResourceRecord[];
}> = ({ name, values }) => {
    const { t } = useTranslation();
    return (
        <>
            <h5>{name}</h5>
            {values.length > 0 ? (
                <table>
                    <thead>
                        <tr>
                            <th>{t("flowView.dnsMessages.name")}</th>
                            <th>{t("flowView.dnsMessages.type")}</th>
                            <th>{t("flowView.dnsMessages.class")}</th>
                            <th>{t("flowView.dnsMessages.ttl")}</th>
                            <th>{t("flowView.dnsMessages.data")}</th>
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
                                    {JSON.stringify(rr.data).replace(
                                        /^"|"$/g,
                                        "",
                                    )}
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
};

const Message: React.FC<{
    type: "request" | "response";
    message: DNSMessage;
}> = ({ type, message }) => {
    const { t } = useTranslation();
    return (
        <section className={"dns-" + type}>
            <div className={`first-line ${type}-line`}>
                <Summary message={message} />
            </div>
            <Questions message={message} />
            <hr />
            <ResourceRecords
                name={`${message.authoritative_answer ? t("flowView.dnsMessages.authoritativeAnswer") + " " : ""}${
                    message.recursion_available
                        ? t("flowView.dnsMessages.recursiveAnswer") + " "
                        : ""
                }${t("flowView.dnsMessages.answer")}`}
                values={message.answers}
            />
            <hr />
            <ResourceRecords
                name={t("flowView.dnsMessages.authority")}
                values={message.authorities}
            />
            <hr />
            <ResourceRecords
                name={t("flowView.dnsMessages.additional")}
                values={message.additionals}
            />
        </section>
    );
};

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

import { useEffect, useState } from "react";
import { fetchApi } from "../../utils";

export type ContentViewData = {
    lines: [style: string, text: string][][];
    description: string;
    from_client?: boolean;
    timestamp?: number;
};

export function useContent(url: string, hash?: string): string | undefined {
    const [content, setContent] = useState<string>();
    const [abort, setAbort] = useState<AbortController>();

    useEffect(() => {
        if (abort) {
            abort.abort();
        }

        const controller = new AbortController();
        fetchApi(url, { signal: controller.signal })
            .then((response) => {
                if (!response.ok)
                    throw `${response.status} ${response.statusText}`.trim();
                return response.text();
            })
            .then((text) => {
                setContent(text);
            })
            .catch((e) => {
                if (controller.signal.aborted) {
                    return;
                }
                setContent(`Error getting content: ${e}.`);
            });

        setAbort(controller);
        return () => {
            if (!controller.signal.aborted) controller.abort();
        };
    }, [url, hash]);

    return content;
}

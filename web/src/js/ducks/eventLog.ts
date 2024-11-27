import * as store from "./utils/store";

export const ADD = "EVENTS_ADD";
export const RECEIVE = "EVENTS_RECEIVE";
export const TOGGLE_VISIBILITY = "EVENTS_TOGGLE_VISIBILITY";
export const TOGGLE_FILTER = "EVENTS_TOGGLE_FILTER";

export enum LogLevel {
    debug = "debug",
    info = "info",
    web = "web",
    warn = "warn",
    error = "error",
}

export interface EventLogItem extends store.Item {
    message: string;
    level: LogLevel;
}

interface EventLogState extends store.State<EventLogItem> {
    visible: boolean;
    filters: { [level in LogLevel]: boolean };
}

const defaultState: EventLogState = {
    visible: false,
    filters: { debug: false, info: true, web: true, warn: true, error: true },
    ...store.defaultState,
};

export default function reduce(
    state: EventLogState = defaultState,
    action,
): EventLogState {
    switch (action.type) {
        case TOGGLE_VISIBILITY:
            return {
                ...state,
                visible: !state.visible,
            };

        case TOGGLE_FILTER: {
            const filters = {
                ...state.filters,
                [action.filter]: !state.filters[action.filter],
            };
            return {
                ...state,
                filters,
                ...store.reduce(
                    state,
                    store.setFilter<EventLogItem>((log) => filters[log.level]),
                ),
            };
        }
        case ADD:
        case RECEIVE:
            return {
                ...state,
                ...store.reduce(
                    state,
                    store[action.cmd](
                        action.data,
                        (log: EventLogItem) => state.filters[log.level],
                    ),
                ),
            };

        default:
            return state;
    }
}

export function toggleFilter(filter: LogLevel) {
    return { type: TOGGLE_FILTER, filter };
}

export function toggleVisibility() {
    return { type: TOGGLE_VISIBILITY };
}

export function add(message: string, level: LogLevel = LogLevel.web) {
    const data = {
        id: Math.random().toString(),
        message,
        level,
    };
    return {
        type: ADD,
        cmd: "add",
        data,
    };
}

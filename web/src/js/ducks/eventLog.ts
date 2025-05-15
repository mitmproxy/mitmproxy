import { createAction, UnknownAction } from "@reduxjs/toolkit";

export const EVENTS_ADD = createAction<EventLogItem>("EVENTS_ADD");
export const EVENTS_RECEIVE = createAction<EventLogItem[]>("EVENTS_RECEIVE");
export const toggleVisibility = createAction("events/toggleVisibility");
export const toggleFilter = createAction<LogLevel>("events/toggleFilter");

export enum LogLevel {
    debug = "debug",
    info = "info",
    web = "web",
    warn = "warn",
    error = "error",
}

export interface EventLogItem {
    id: string;
    message: string;
    level: LogLevel;
}

interface EventLogState {
    visible: boolean;
    filters: { [level in LogLevel]: boolean };
    list: EventLogItem[];
    view: EventLogItem[];
}

export const defaultState: EventLogState = {
    visible: false,
    filters: { debug: false, info: true, web: true, warn: true, error: true },
    list: [],
    view: [],
};

export default function eventLogReducer(
    state = defaultState,
    action: UnknownAction,
): EventLogState {
    if (EVENTS_ADD.match(action)) {
        const logItem = action.payload;
        return {
            ...state,
            list: [...state.list, logItem],
            view: state.filters[logItem.level]
                ? [...state.view, logItem]
                : state.view,
        };
    } else if (EVENTS_RECEIVE.match(action)) {
        return {
            ...state,
            list: action.payload,
            view: action.payload.filter((log) => state.filters[log.level]),
        };
    } else if (toggleVisibility.match(action)) {
        return {
            ...state,
            visible: !state.visible,
        };
    } else if (toggleFilter.match(action)) {
        const filters = {
            ...state.filters,
            [action.payload]: !state.filters[action.payload],
        };
        return {
            ...state,
            filters,
            view: state.list.filter((log) => filters[log.level]),
        };
    } else {
        return state;
    }
}

export function add(message: string, level: LogLevel = LogLevel.web) {
    return EVENTS_ADD({
        id: Math.random().toString(),
        message,
        level,
    });
}

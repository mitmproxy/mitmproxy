export const TOGGLE_EVENTLOG_FILTER = 'TOGGLE_EVENTLOG_FILTER';
export const HIDE_EVENTLOG = 'HIDE_EVENTLOG';
export const SHOW_EVENTLOG = 'SHOW_EVENTLOG';

export const EventLogFilters = {
    DEBUG: 'debug',
    INFO: 'info',
    WEB: 'web'
};

export function toggleEventLogFilter(filter) {
    return {type: TOGGLE_EVENTLOG_FILTER, filter}
}

import {combineReducers} from 'redux';
import eventLog from './eventlog'

const mitmproxyApp = combineReducers({
    eventLog
});

export default mitmproxyApp

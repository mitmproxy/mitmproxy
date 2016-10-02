import h2
import hyperframe


def h2_settings(message):
    names = {
        hyperframe.frame.SettingsFrame.HEADER_TABLE_SIZE: 'HEADER_TABLE_SIZE',
        hyperframe.frame.SettingsFrame.ENABLE_PUSH: 'ENABLE_PUSH',
        hyperframe.frame.SettingsFrame.MAX_CONCURRENT_STREAMS: 'MAX_CONCURRENT_STREAMS',
        hyperframe.frame.SettingsFrame.INITIAL_WINDOW_SIZE: 'INITIAL_WINDOW_SIZE',
        hyperframe.frame.SettingsFrame.MAX_FRAME_SIZE: 'MAX_FRAME_SIZE',
        hyperframe.frame.SettingsFrame.MAX_HEADER_LIST_SIZE: 'MAX_HEADER_LIST_SIZE',
    }

    side = 'server' if message.is_server else 'client'
    msg = ", ".join("{}: {} to {}".format(names[k], v.original_value, v.new_value) for k, v in message.changed_settings.items())
    print("{} updated its settings: {}".format(side, msg))

    # we can manipulate the settings now
    if h2.settings.ENABLE_PUSH in message.changed_settings:
        old = message.changed_settings[h2.settings.ENABLE_PUSH].original_value
        new = h2.settings.ChangedSetting(h2.settings.ENABLE_PUSH, old, 0)
        message.changed_settings[h2.settings.ENABLE_PUSH] = new
    if h2.settings.MAX_CONCURRENT_STREAMS in message.changed_settings:
        old = message.changed_settings[h2.settings.MAX_CONCURRENT_STREAMS].original_value
        new = h2.settings.ChangedSetting(h2.settings.MAX_CONCURRENT_STREAMS, old, 42)
        message.changed_settings[h2.settings.MAX_CONCURRENT_STREAMS] = new

palettes = {

# Default palette for dark background
  'dark': [
    # name, foreground, background, mono, foreground_high, background_high
    # For details on the meaning of the elements refer to
    # http://excess.org/urwid/reference.html#Screen-register_palette

    ('body', 'black', 'dark cyan'),
    ('foot', 'light gray', 'default'),
    ('title', 'white,bold', 'default',),
    ('editline', 'white', 'default',),

    # Status bar & heading
    ('heading', 'light gray', 'dark blue', None, 'g85', 'dark blue'),
    ('heading_key', 'light cyan', 'dark blue', None, 'light cyan', 'dark blue'),
    ('heading_inactive', 'white', 'dark gray', None, 'g58', 'g11'),

    # Help
    ('key', 'light cyan', 'default'),
    ('head', 'white,bold', 'default'),
    ('text', 'light gray', 'default'),

    # List and Connections
    ('method', 'dark cyan', 'default'),
    ('focus', 'yellow', 'default'),

    ('code_200', 'light green', 'default'),
    ('code_300', 'light blue', 'default'),
    ('code_400', 'light red', 'default', None, '#f60', 'default'),
    ('code_500', 'light red', 'default'),
    ('code_other', 'dark red', 'default'),

    ('error', 'light red', 'default'),

    ('header', 'dark cyan', 'default'),
    ('highlight', 'white,bold', 'default'),
    ('intercept', 'brown', 'default', None, '#f60', 'default'),
    ('replay', 'light green', 'default', None, '#0f0', 'default'),
    ('ack', 'light red', 'default'),

    # Hex view
    ('offset', 'dark cyan', 'default'),

    # Grid Editor
    ('focusfield', 'black', 'light gray'),
    ('focusfield_error', 'dark red', 'light gray'),
    ('field_error', 'dark red', 'black'),
    ('editfield', 'black', 'light cyan'),
  ],

# Palette for light background
  'light': [
    ('body', 'black', 'dark cyan'),
    ('foot', 'dark gray', 'default'),
    ('title', 'white,bold', 'light blue',),
    ('editline', 'white', 'default',),

    # Status bar & heading
    ('heading', 'white', 'light gray', None, 'g85', 'dark blue'),
    ('heading_key', 'dark blue', 'light gray', None, 'light cyan', 'dark blue'),
    ('heading_inactive', 'light gray', 'dark gray', None, 'dark gray', 'dark blue'),

    # Help
    ('key', 'dark blue,bold', 'default'),
    ('head', 'black,bold', 'default'),
    ('text', 'dark gray', 'default'),

    # List and Connections
    ('method', 'dark cyan', 'default'),
    ('focus', 'black', 'default'),

    ('code_200', 'dark green', 'default'),
    ('code_300', 'light blue', 'default'),
    ('code_400', 'dark red', 'default', None, '#f60', 'default'),
    ('code_500', 'dark red', 'default'),
    ('code_other', 'light red', 'default'),

    ('error', 'light red', 'default'),

    ('header', 'dark blue', 'default'),
    ('highlight', 'black,bold', 'default'),
    ('intercept', 'brown', 'default', None, '#f60', 'default'),
    ('replay', 'dark green', 'default', None, '#0f0', 'default'),
    ('ack', 'dark red', 'default'),

    # Hex view
    ('offset', 'dark blue', 'default'),

    # Grid Editor
    ('focusfield', 'black', 'light gray'),
    ('focusfield_error', 'dark red', 'light gray'),
    ('field_error', 'dark red', 'black'),
    ('editfield', 'black', 'light cyan'),
  ],

# Palettes for terminals that use the Solarized precision colors
# (http://ethanschoonover.com/solarized#the-values)

# For dark backgrounds
  'solarized_dark': [
    ('body', 'dark cyan', 'default'),
    ('foot', 'dark gray', 'default'),
    ('title', 'white,bold', 'default',),
    ('editline', 'white', 'default',),

    # Status bar & heading
    ('heading', 'light gray', 'light cyan',),
    ('heading_key', 'dark blue', 'white',),
    ('heading_inactive', 'light cyan', 'light gray',),

    # Help
    ('key', 'dark blue', 'default',),
    ('head', 'white,underline', 'default'),
    ('text', 'light cyan', 'default'),

    # List and Connections
    ('method', 'dark cyan', 'default'),
    ('focus', 'white', 'default'),

    ('code_200', 'dark green', 'default'),
    ('code_300', 'light blue', 'default'),
    ('code_400', 'dark red', 'default',),
    ('code_500', 'dark red', 'default'),
    ('code_other', 'light red', 'default'),

    ('error', 'light red', 'default'),

    ('header', 'yellow', 'default'),
    ('highlight', 'white', 'default'),
    ('intercept', 'brown', 'default',),
    ('replay', 'dark green', 'default',),
    ('ack', 'dark red', 'default'),

    # Hex view
    ('offset', 'yellow', 'default'),
    ('text', 'light cyan', 'default'),

    # Grid Editor
    ('focusfield', 'white', 'light cyan'),
    ('focusfield_error', 'dark red', 'light gray'),
    ('field_error', 'dark red', 'black'),
    ('editfield', 'black', 'light gray'),
  ],

# For light backgrounds
  'solarized_light': [
    ('body', 'dark cyan', 'default'),
    ('foot', 'dark gray', 'default'),
    ('title', 'white,bold', 'light cyan',),
    ('editline', 'white', 'default',),

    # Status bar & heading
    ('heading', 'light cyan', 'light gray',),
    ('heading_key', 'dark blue', 'white',),
    ('heading_inactive', 'white', 'light gray',),

    # Help
    ('key', 'dark blue', 'default',),
    ('head', 'black,underline', 'default'),
    ('text', 'light cyan', 'default'),

    # List and Connections
    ('method', 'dark cyan', 'default'),
    ('focus', 'black', 'default'),

    ('code_200', 'dark green', 'default'),
    ('code_300', 'light blue', 'default'),
    ('code_400', 'dark red', 'default',),
    ('code_500', 'dark red', 'default'),
    ('code_other', 'light red', 'default'),

    ('error', 'light red', 'default'),

    ('header', 'light cyan', 'default'),
    ('highlight', 'black,bold', 'default'),
    ('intercept', 'brown', 'default',),
    ('replay', 'dark green', 'default',),
    ('ack', 'dark red', 'default'),

    # Hex view
    ('offset', 'light cyan', 'default'),
    ('text', 'yellow', 'default'),

    # Grid Editor
    ('focusfield', 'black', 'light gray'),
    ('focusfield_error', 'dark red', 'light gray'),
    ('field_error', 'dark red', 'black'),
    ('editfield', 'white', 'light cyan'),
  ],

}

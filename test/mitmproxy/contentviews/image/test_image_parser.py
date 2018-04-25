import pytest

from mitmproxy.contentviews.image import image_parser


@pytest.mark.parametrize("filename, metadata", {
    # no textual data
    "mitmproxy/data/image_parser/ct0n0g04.png": [
        ('Format', 'Portable network graphics'),
        ('Size', '32 x 32 px'),
        ('gamma', '1.0')
    ],
    # with textual data
    "mitmproxy/data/image_parser/ct1n0g04.png": [
        ('Format', 'Portable network graphics'),
        ('Size', '32 x 32 px'),
        ('gamma', '1.0'),
        ('Title', 'PngSuite'),
        ('Author', 'Willem A.J. van Schaik\n(willem@schaik.com)'),
        ('Copyright', 'Copyright Willem van Schaik, Singapore 1995-96'),
        ('Description', 'A compilation of a set of images created to test the\n'
         'various color-types of the PNG format. Included are\nblack&white, color,'
         ' paletted, with alpha channel, with\ntransparency formats. All bit-depths'
         ' allowed according\nto the spec are present.'),
        ('Software', 'Created on a NeXTstation color using "pnmtopng".'),
        ('Disclaimer', 'Freeware.')
    ],
    # with compressed textual data
    "mitmproxy/data/image_parser/ctzn0g04.png": [
        ('Format', 'Portable network graphics'),
        ('Size', '32 x 32 px'),
        ('gamma', '1.0'),
        ('Title', 'PngSuite'),
        ('Author', 'Willem A.J. van Schaik\n(willem@schaik.com)'),
        ('Copyright', 'Copyright Willem van Schaik, Singapore 1995-96'),
        ('Description', 'A compilation of a set of images created to test the\n'
         'various color-types of the PNG format. Included are\nblack&white, color,'
         ' paletted, with alpha channel, with\ntransparency formats. All bit-depths'
         ' allowed according\nto the spec are present.'),
        ('Software', 'Created on a NeXTstation color using "pnmtopng".'),
        ('Disclaimer', 'Freeware.')
    ],
    # UTF-8 international text - english
    "mitmproxy/data/image_parser/cten0g04.png": [
        ('Format', 'Portable network graphics'),
        ('Size', '32 x 32 px'),
        ('gamma', '1.0'),
        ('Title', 'PngSuite'),
        ('Author', 'Willem van Schaik (willem@schaik.com)'),
        ('Copyright', 'Copyright Willem van Schaik, Canada 2011'),
        ('Description', 'A compilation of a set of images created to test the '
         'various color-types of the PNG format. Included are black&white, color,'
         ' paletted, with alpha channel, with transparency formats. All bit-depths'
         ' allowed according to the spec are present.'),
        ('Software', 'Created on a NeXTstation color using "pnmtopng".'),
        ('Disclaimer', 'Freeware.')
    ],
    # check gamma value
    "mitmproxy/data/image_parser/g07n0g16.png": [
        ('Format', 'Portable network graphics'),
        ('Size', '32 x 32 px'),
        ('gamma', '0.7')
    ],
    # check aspect value
    "mitmproxy/data/image_parser/aspect.png": [
        ('Format', 'Portable network graphics'),
        ('Size', '1280 x 798 px'),
        ('aspect', '72 x 72'),
        ('date:create', '2012-07-11T14:04:52-07:00'),
        ('date:modify', '2012-07-11T14:04:52-07:00')
    ],
}.items())
def test_parse_png(filename, metadata, tdata):
    with open(tdata.path(filename), "rb") as f:
        assert metadata == image_parser.parse_png(f.read())


@pytest.mark.parametrize("filename, metadata", {
    # check comment
    "mitmproxy/data/image_parser/hopper.gif": [
        ('Format', 'Compuserve GIF'),
        ('Version', 'GIF89a'),
        ('Size', '128 x 128 px'),
        ('background', '0'),
        ('comment', "b'File written by Adobe Photoshop\\xa8 4.0'")
    ],
    # check background
    "mitmproxy/data/image_parser/chi.gif": [
        ('Format', 'Compuserve GIF'),
        ('Version', 'GIF89a'),
        ('Size', '320 x 240 px'),
        ('background', '248'),
        ('comment', "b'Created with GIMP'")
    ],
    # check working with color table
    "mitmproxy/data/image_parser/iss634.gif": [
        ('Format', 'Compuserve GIF'),
        ('Version', 'GIF89a'),
        ('Size', '245 x 245 px'),
        ('background', '0')
    ],
}.items())
def test_parse_gif(filename, metadata, tdata):
    with open(tdata.path(filename), 'rb') as f:
        assert metadata == image_parser.parse_gif(f.read())


@pytest.mark.parametrize("filename, metadata", {
    # check app0
    "mitmproxy/data/image_parser/example.jpg": [
        ('Format', 'JPEG (ISO 10918)'),
        ('jfif_version', '(1, 1)'),
        ('jfif_density', '(96, 96)'),
        ('jfif_unit', '1'),
        ('Size', '256 x 256 px')
    ],
    # check com
    "mitmproxy/data/image_parser/comment.jpg": [
        ('Format', 'JPEG (ISO 10918)'),
        ('jfif_version', '(1, 1)'),
        ('jfif_density', '(96, 96)'),
        ('jfif_unit', '1'),
        ('comment', "b'mitmproxy test image'"),
        ('Size', '256 x 256 px')
    ],
    # check app1
    "mitmproxy/data/image_parser/app1.jpeg": [
        ('Format', 'JPEG (ISO 10918)'),
        ('jfif_version', '(1, 1)'),
        ('jfif_density', '(72, 72)'),
        ('jfif_unit', '1'),
        ('make', 'Canon'),
        ('model', 'Canon PowerShot A60'),
        ('modify_date', '2004:07:16 18:46:04'),
        ('Size', '717 x 558 px')
    ],
    # check multiple segments
    "mitmproxy/data/image_parser/all.jpeg": [
        ('Format', 'JPEG (ISO 10918)'),
        ('jfif_version', '(1, 1)'),
        ('jfif_density', '(300, 300)'),
        ('jfif_unit', '1'),
        ('comment', 'b\'BARTOLOMEO DI FRUOSINO\\r\\n(b. ca. 1366, Firenze, d. 1441, '
         'Firenze)\\r\\n\\r\\nInferno, from the Divine Comedy by Dante (Folio 1v)'
         '\\r\\n1430-35\\r\\nTempera, gold, and silver on parchment, 365 x 265 mm'
         '\\r\\nBiblioth\\xe8que Nationale, Paris\\r\\n\\r\\nThe codex in Paris '
         'contains the text of the Inferno, the first of three books of the Divine '
         'Comedy, the masterpiece of the Florentine poet Dante Alighieri (1265-1321).'
         ' The codex begins with two full-page illuminations. On folio 1v Dante and '
         'Virgil stand within the doorway of Hell at the upper left and observe its '
         'nine different zones. Dante and Virgil are to wade through successive '
         'circles teeming with images of the damned. The gates of Hell appear  in '
         'the middle, a scarlet row of open sarcophagi before them. Devils orchestrate'
         ' the movements of the wretched souls.\\r\\n\\r\\nThe vision of the fiery '
         'inferno follows a convention established by <A onclick="return OpenOther'
         '(\\\'/html/n/nardo/strozzi3.html\\\')" HREF="/html/n/nardo/strozzi3.html">'
         'Nardo di Cione\\\'s fresco</A> in the church of Santa Maria Novella, Florence.'
         ' Of remarkable vivacity and intensity of expression, the illumination is '
         'executed in Bartolomeo\\\'s late style.\\r\\n\\r\\n\\r\\n\\r\\n\\r\\n\\r\\n\\r\\n'
         '--- Keywords: --------------\\r\\n\\r\\nAuthor: BARTOLOMEO DI FRUOSINO'
         '\\r\\nTitle: Inferno, from the Divine Comedy by Dante (Folio 1v)\\r\\nTime-line:'
         ' 1401-1450\\r\\nSchool: Italian\\r\\nForm: illumination\\r\\nType: other\\r\\n\''),
        ('Size', '750 x 1055 px')
    ],
}.items())
def test_parse_jpeg(filename, metadata, tdata):
    with open(tdata.path(filename), 'rb') as f:
        assert metadata == image_parser.parse_jpeg(f.read())


@pytest.mark.parametrize("filename, metadata", {
    "mitmproxy/data/image.ico": [
        ('Format', 'ICO'),
        ('Number of images', '3'),
        ('Image 1', "Size: {} x {}\n"
                    "{: >18}Bits per pixel: {}\n"
                    "{: >18}PNG: {}".format(48, 48, '', 24, '', False)
         ),
        ('Image 2', "Size: {} x {}\n"
                    "{: >18}Bits per pixel: {}\n"
                    "{: >18}PNG: {}".format(32, 32, '', 24, '', False)
         ),
        ('Image 3', "Size: {} x {}\n"
                    "{: >18}Bits per pixel: {}\n"
                    "{: >18}PNG: {}".format(16, 16, '', 24, '', False)
         )
    ]
}.items())
def test_ico(filename, metadata, tdata):
    with open(tdata.path(filename), 'rb') as f:
        assert metadata == image_parser.parse_ico(f.read())

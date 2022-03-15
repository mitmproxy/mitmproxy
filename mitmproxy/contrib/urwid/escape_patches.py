# monkeypatch https://github.com/urwid/urwid/commit/e2423b5069f51d318ea1ac0f355a0efe5448f7eb into the urwid sources.
import urwid.escape

if urwid.__version__ in ("2.1.1", "2.1.2"):
    # fmt: off
    urwid.escape.input_sequences = [
        ('[A','up'),('[B','down'),('[C','right'),('[D','left'),
        ('[E','5'),('[F','end'),('[G','5'),('[H','home'),

        ('[1~','home'),('[2~','insert'),('[3~','delete'),('[4~','end'),
        ('[5~','page up'),('[6~','page down'),
        ('[7~','home'),('[8~','end'),

        ('[[A','f1'),('[[B','f2'),('[[C','f3'),('[[D','f4'),('[[E','f5'),

        ('[11~','f1'),('[12~','f2'),('[13~','f3'),('[14~','f4'),
        ('[15~','f5'),('[17~','f6'),('[18~','f7'),('[19~','f8'),
        ('[20~','f9'),('[21~','f10'),('[23~','f11'),('[24~','f12'),
        ('[25~','f13'),('[26~','f14'),('[28~','f15'),('[29~','f16'),
        ('[31~','f17'),('[32~','f18'),('[33~','f19'),('[34~','f20'),

        ('OA','up'),('OB','down'),('OC','right'),('OD','left'),
        ('OH','home'),('OF','end'),
        ('OP','f1'),('OQ','f2'),('OR','f3'),('OS','f4'),
        ('Oo','/'),('Oj','*'),('Om','-'),('Ok','+'),

        ('[Z','shift tab'),
        ('On', '.'),

        ('[200~', 'begin paste'), ('[201~', 'end paste'),
    ] + [
        (prefix + letter, modifier + key)
        for prefix, modifier in zip('O[', ('meta ', 'shift '))
        for letter, key in zip('abcd', ('up', 'down', 'right', 'left'))
    ] + [
        ("[" + digit + symbol, modifier + key)
        for modifier, symbol in zip(('shift ', 'meta '), '$^')
        for digit, key in zip('235678',
            ('insert', 'delete', 'page up', 'page down', 'home', 'end'))
    ] + [
        ('O' + chr(ord('p')+n), str(n)) for n in range(10)
    ] + [
        # modified cursor keys + home, end, 5 -- [#X and [1;#X forms
        (prefix+digit+letter, urwid.escape.escape_modifier(digit) + key)
        for prefix in ("[", "[1;")
        for digit in "12345678"
        for letter,key in zip("ABCDEFGH",
            ('up','down','right','left','5','end','5','home'))
    ] + [
        # modified F1-F4 keys -- O#X form
        ("O"+digit+letter, urwid.escape.escape_modifier(digit) + key)
        for digit in "12345678"
        for letter,key in zip("PQRS",('f1','f2','f3','f4'))
    ] + [
        # modified F1-F13 keys -- [XX;#~ form
        ("["+str(num)+";"+digit+"~", urwid.escape.escape_modifier(digit) + key)
        for digit in "12345678"
        for num,key in zip(
            (3,5,6,11,12,13,14,15,17,18,19,20,21,23,24,25,26,28,29,31,32,33,34),
            ('delete', 'page up', 'page down',
            'f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11',
            'f12','f13','f14','f15','f16','f17','f18','f19','f20'))
    ] + [
        # mouse reporting (special handling done in KeyqueueTrie)
        ('[M', 'mouse'),

        # mouse reporting for SGR 1006
        ('[<', 'sgrmouse'),

        # report status response
        ('[0n', 'status ok')
    ]


    class KeyqueueTrie(object):
        def __init__( self, sequences ):
            self.data = {}
            for s, result in sequences:
                assert type(result) != dict
                self.add(self.data, s, result)

        def add(self, root, s, result):
            assert type(root) == dict, "trie conflict detected"
            assert len(s) > 0, "trie conflict detected"

            if ord(s[0]) in root:
                return self.add(root[ord(s[0])], s[1:], result)
            if len(s)>1:
                d = {}
                root[ord(s[0])] = d
                return self.add(d, s[1:], result)
            root[ord(s)] = result

        def get(self, keys, more_available):
            result = self.get_recurse(self.data, keys, more_available)
            if not result:
                result = self.read_cursor_position(keys, more_available)
            return result

        def get_recurse(self, root, keys, more_available):
            if type(root) != dict:
                if root == "mouse":
                    return self.read_mouse_info(keys,
                        more_available)
                elif root == "sgrmouse":
                    return self.read_sgrmouse_info (keys, more_available)
                return (root, keys)
            if not keys:
                # get more keys
                if more_available:
                    raise urwid.escape.MoreInputRequired()
                return None
            if keys[0] not in root:
                return None
            return self.get_recurse(root[keys[0]], keys[1:], more_available)

        def read_mouse_info(self, keys, more_available):
            if len(keys) < 3:
                if more_available:
                    raise urwid.escape.MoreInputRequired()
                return None

            b = keys[0] - 32
            x, y = (keys[1] - 33)%256, (keys[2] - 33)%256  # supports 0-255

            prefix = ""
            if b & 4:    prefix = prefix + "shift "
            if b & 8:    prefix = prefix + "meta "
            if b & 16:    prefix = prefix + "ctrl "
            if (b & urwid.escape.MOUSE_MULTIPLE_CLICK_MASK)>>9 == 1:    prefix = prefix + "double "
            if (b & urwid.escape.MOUSE_MULTIPLE_CLICK_MASK)>>9 == 2:    prefix = prefix + "triple "

            # 0->1, 1->2, 2->3, 64->4, 65->5
            button = ((b&64)//64*3) + (b & 3) + 1

            if b & 3 == 3:
                action = "release"
                button = 0
            elif b & urwid.escape.MOUSE_RELEASE_FLAG:
                action = "release"
            elif b & urwid.escape.MOUSE_DRAG_FLAG:
                action = "drag"
            elif b & urwid.escape.MOUSE_MULTIPLE_CLICK_MASK:
                action = "click"
            else:
                action = "press"

            return ( (prefix + "mouse " + action, button, x, y), keys[3:] )

        def read_sgrmouse_info(self, keys, more_available):
            # Helpful links:
            # https://stackoverflow.com/questions/5966903/how-to-get-mousemove-and-mouseclick-in-bash
            # http://invisible-island.net/xterm/ctlseqs/ctlseqs.pdf

            if not keys:
                if more_available:
                    raise urwid.escape.MoreInputRequired()
                return None

            value = ''
            pos_m = 0
            found_m = False
            for k in keys:
                value = value + chr(k);
                if ((k is ord('M')) or (k is ord('m'))):
                    found_m = True
                    break;
                pos_m += 1
            if not found_m:
                if more_available:
                    raise urwid.escape.MoreInputRequired()
                return None

            (b, x, y) = value[:-1].split(';')

            # shift, meta, ctrl etc. is not communicated on my machine, so I
            # can't and won't be able to add support for it.
            # Double and triple clicks are not supported as well. They can be
            # implemented by using a timer. This timer can check if the last
            # registered click is below a certain threshold. This threshold
            # is normally set in the operating system itself, so setting one
            # here will cause an inconsistent behaviour. I do not plan to use
            # that feature, so I won't implement it.

            button = ((int(b) & 64) // 64 * 3) + (int(b) & 3) + 1
            x = int(x) - 1
            y = int(y) - 1

            if (value[-1] == 'M'):
                if int(b) & urwid.escape.MOUSE_DRAG_FLAG:
                    action = "drag"
                else:
                    action = "press"
            else:
                action = "release"

            return ( ("mouse " + action, button, x, y), keys[pos_m + 1:] )


        def read_cursor_position(self, keys, more_available):
            """
            Interpret cursor position information being sent by the
            user's terminal.  Returned as ('cursor position', x, y)
            where (x, y) == (0, 0) is the top left of the screen.
            """
            if not keys:
                if more_available:
                    raise urwid.escape.MoreInputRequired()
                return None
            if keys[0] != ord('['):
                return None
            # read y value
            y = 0
            i = 1
            for k in keys[i:]:
                i += 1
                if k == ord(';'):
                    if not y:
                        return None
                    break
                if k < ord('0') or k > ord('9'):
                    return None
                if not y and k == ord('0'):
                    return None
                y = y * 10 + k - ord('0')
            if not keys[i:]:
                if more_available:
                    raise urwid.escape.MoreInputRequired()
                return None
            # read x value
            x = 0
            for k in keys[i:]:
                i += 1
                if k == ord('R'):
                    if not x:
                        return None
                    return (("cursor position", x-1, y-1), keys[i:])
                if k < ord('0') or k > ord('9'):
                    return None
                if not x and k == ord('0'):
                    return None
                x = x * 10 + k - ord('0')
            if not keys[i:]:
                if more_available:
                    raise urwid.escape.MoreInputRequired()
            return None

    urwid.escape.KeyqueueTrie = KeyqueueTrie
    urwid.escape.input_trie = KeyqueueTrie(urwid.escape.input_sequences)


    ESC = urwid.escape.ESC
    urwid.escape.MOUSE_TRACKING_ON = ESC+"[?1000h"+ESC+"[?1002h"+ESC+"[?1006h"
    urwid.escape.MOUSE_TRACKING_OFF = ESC+"[?1006l"+ESC+"[?1002l"+ESC+"[?1000l"

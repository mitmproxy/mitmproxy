import re, copy


def safe_subn(pattern, repl, target, *args, **kwargs):
    """
        There are Unicode conversion problems with re.subn. We try to smooth
        that over by casting the pattern and replacement to strings. We really
        need a better solution that is aware of the actual content ecoding.
    """
    return re.subn(str(pattern), str(repl), target, *args, **kwargs)


class ODict:
    """
        A dictionary-like object for managing ordered (key, value) data.
    """
    def __init__(self, lst=None):
        self.lst = lst or []

    def _kconv(self, s):
        return s

    def __eq__(self, other):
        return self.lst == other.lst

    def __iter__(self):
        return self.lst.__iter__()

    def __getitem__(self, k):
        """
            Returns a list of values matching key.
        """
        ret = []
        k = self._kconv(k)
        for i in self.lst:
            if self._kconv(i[0]) == k:
                ret.append(i[1])
        return ret

    def keys(self):
        return list(set([self._kconv(i[0]) for i in self.lst]))

    def _filter_lst(self, k, lst):
        k = self._kconv(k)
        new = []
        for i in lst:
            if self._kconv(i[0]) != k:
                new.append(i)
        return new

    def __len__(self):
        """
            Total number of (key, value) pairs.
        """
        return len(self.lst)

    def __setitem__(self, k, valuelist):
        """
            Sets the values for key k. If there are existing values for this
            key, they are cleared.
        """
        if isinstance(valuelist, basestring):
            raise ValueError("ODict valuelist should be lists.")
        new = self._filter_lst(k, self.lst)
        for i in valuelist:
            new.append([k, i])
        self.lst = new

    def __delitem__(self, k):
        """
            Delete all items matching k.
        """
        self.lst = self._filter_lst(k, self.lst)

    def __contains__(self, k):
        for i in self.lst:
            if self._kconv(i[0]) == self._kconv(k):
                return True
        return False

    def add(self, key, value):
        self.lst.append([key, str(value)])

    def get(self, k, d=None):
        if k in self:
            return self[k]
        else:
            return d

    def get_first(self, k, d=None):
        if k in self:
            return self[k][0]
        else:
            return d

    def items(self):
        return self.lst[:]

    def _get_state(self):
        return [tuple(i) for i in self.lst]

    def _load_state(self, state):
        self.list = [list(i) for i in state]

    @classmethod
    def _from_state(klass, state):
        return klass([list(i) for i in state])

    def copy(self):
        """
            Returns a copy of this object.
        """
        lst = copy.deepcopy(self.lst)
        return self.__class__(lst)

    def __repr__(self):
        elements = []
        for itm in self.lst:
            elements.append(itm[0] + ": " + itm[1])
        elements.append("")
        return "\r\n".join(elements)

    def in_any(self, key, value, caseless=False):
        """
            Do any of the values matching key contain value?

            If caseless is true, value comparison is case-insensitive.
        """
        if caseless:
            value = value.lower()
        for i in self[key]:
            if caseless:
                i = i.lower()
            if value in i:
                return True
        return False

    def match_re(self, expr):
        """
            Match the regular expression against each (key, value) pair. For
            each pair a string of the following format is matched against:

            "key: value"
        """
        for k, v in self.lst:
            s = "%s: %s"%(k, v)
            if re.search(expr, s):
                return True
        return False

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both keys and
            values. Encoded content will be decoded before replacement, and
            re-encoded afterwards.

            Returns the number of replacements made.
        """
        nlst, count = [], 0
        for i in self.lst:
            k, c = safe_subn(pattern, repl, i[0], *args, **kwargs)
            count += c
            v, c = safe_subn(pattern, repl, i[1], *args, **kwargs)
            count += c
            nlst.append([k, v])
        self.lst = nlst
        return count


class ODictCaseless(ODict):
    """
        A variant of ODict with "caseless" keys. This version _preserves_ key
        case, but does not consider case when setting or getting items.
    """
    def _kconv(self, s):
        return s.lower()

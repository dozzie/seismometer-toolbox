#!/usr/bin/python
'''
Tag matcher for Graphite-like monitoring input. Intended to make location and
aspect name out of metric path.

.. autoclass:: TagMatcher
   :members:

'''
#-----------------------------------------------------------------------------

import re
import os

#-----------------------------------------------------------------------------
# pattern {{{

class Pattern:
    def __init__(self):
        self.fields = []
        self.slurp = False

    def add(self, field):
        if self.slurp:
            raise ValueError("slurp in the middle of pattern is not supported")
        if isinstance(field, SlurpField):
            self.slurp = True
        self.fields.append(field)

    def match(self, tag):
        tag_fields = tag.split(".")
        if (self.slurp and len(tag_fields) < len(self.fields)) or \
           (not self.slurp and len(tag_fields) != len(self.fields)):
            return None

        # XXX: if slurp field is present (it will be at the end of
        # self.fields), it's OK to allow it to match and even set the returned
        # field, since the field will be replaced after this loop
        fields = {
            "aspect": tag,
            "host": os.uname()[1],
        }
        for i in xrange(len(self.fields)):
            if tag_fields[i] in self.fields[i]:
                name = self.fields[i].field_name
                if name is not None:
                    fields[name] = tag_fields[i]
            else:
                return None

        if self.slurp and self.fields[-1].field_name is not None:
            name = self.fields[-1].field_name
            # get all the fields from tag that match slurp (i.e. from the
            # slurp position to the end of tag) and join them back with period
            last_field_idx = len(self.fields) - 1
            value = ".".join(tag_fields[last_field_idx:])
            fields[name] = value

        return fields

# }}}
#-----------------------------------------------------------------------------
# definition {{{

class Definition:
    def __init__(self):
        self.words = set()
        self.regexps = []

    def __contains__(self, thing):
        if thing in self.words:
            return True
        for regexp in self.regexps:
            match = regexp.match(thing)
            if match and match.end() == len(thing):
                return True
        return False

    def add_word(self, word):
        self.words.add(word)

    def add_regexp(self, regexp):
        # strip leading and trailing slashes
        regexp = regexp[1:-1]
        # this surely renders correct pattern, since every "/" needed to be
        # prefixed with backslash (not to mention that slash has no use in
        # this config anyway)
        regexp = regexp.replace('\\/', '/')
        try:
            self.regexps.append(re.compile(regexp))
        except Exception, e:
            raise ValueError("invalid regexp: %s" % (e.args[0],))

# }}}
#-----------------------------------------------------------------------------
# fields {{{

class Field(object):
    def __init__(self):
        self.field_name = None

    def set_name(self, name):
        self.field_name = name

    def __contains__(self, thing):
        raise NotImplementedError("<foo> in <%s> not implemented" % (self.__class__.__name__))

class WildcardField(Field):
    def __contains__(self, thing):
        return True

class SlurpField(Field):
    def __contains__(self, thing):
        return True

class DefinitionField(Field):
    def __init__(self, defn):
        super(DefinitionField, self).__init__()
        self.defn = defn

    def __contains__(self, thing):
        return (thing in self.defn)

class ListField(Field):
    def __init__(self, words):
        super(ListField, self).__init__()
        self.words = set(words)

    def __contains__(self, thing):
        return (thing in self.words)

class RegexpField(Field):
    def __init__(self, regexp):
        super(RegexpField, self).__init__()
        # strip leading and trailing slashes
        regexp = regexp[1:-1]
        # this surely renders correct pattern, since every "/" needed to be
        # prefixed with backslash (not to mention that slash has no use in
        # this config anyway)
        regexp = regexp.replace('\\/', '/')
        try:
            self.regexp = re.compile(regexp)
        except Exception, e:
            raise ValueError("invalid regexp: %s" % (e.args[0],))

    def __contains__(self, thing):
        match = self.regexp.match(thing)
        return (match and match.end() == len(thing))

class LiteralField(Field):
    def __init__(self, word):
        super(LiteralField, self).__init__()
        self.word = word

    def __contains__(self, thing):
        return (thing == self.word)

# }}}
#-----------------------------------------------------------------------------

class TagMatcher:
    '''
    Tag matcher class.
    '''
    _DEFINITION   = re.compile(r'[a-zA-Z0-9_]+[ \t]*=')
    _DEF_NAME     = re.compile(r'[a-zA-Z0-9_]+')
    _FIELD_NAME   = re.compile(r'[a-zA-Z0-9_]+')
    _TAG_FRAGMENT = re.compile(r'[a-zA-Z0-9_-]+')
    _SPACE        = re.compile(r'[ \t]+')
    _CONTINUATION = re.compile(r'[ \t]+') # at the beginning of line
    _SEPARATOR    = re.compile(r'[ \t,]+')
    _REGEXP       = re.compile(r'/([^\\/]|\\.)+/')

    def __init__(self, config = None):
        '''
        :param config: configuration file with tag patterns
        '''
        self.config = config
        self.patterns = []
        self.reload()

    def match(self, tag):
        '''
        :return: location and aspect name
        :rtype: tuple (string, dict)

        Match tag against patterns from configuration file.
        '''
        for pat in self.patterns:
            location = pat.match(tag)
            if location is not None:
                aspect = location.pop("aspect")
                return (aspect, location)
        # none of the patterns matched
        location = { "host": os.uname()[1] }
        aspect = tag
        return (aspect, location)

    def reload(self):
        '''
        Reload configuration file.
        '''
        if self.config is None:
            return

        definitions = {}
        patterns = []
        def process_line(line):
            # no previous line, just ignore it
            if line is None:
                return

            if TagMatcher._DEFINITION.match(line):
                (defn, value) = line.split("=", 1)
                defn = defn.strip()
                definitions[defn] = parse_definition(value)
            else:
                # it should be a pattern definition
                patterns.append(parse_pattern(line))

        #--------------------------------------------------
        # parsing line types {{{

        def parse_definition(line):
            defn = Definition()
            while True:
                (_skip, line) = re_consume(TagMatcher._SEPARATOR, line)
                if line == "":
                    break
                (word, line) = re_consume(TagMatcher._DEF_NAME, line)
                if word:
                    defn.add_word(word)
                    continue
                (regexp, line) = re_consume(TagMatcher._REGEXP, line)
                if regexp:
                    defn.add_regexp(regexp)
                    continue
                raise ValueError("unrecognized thing: %s" % (line,))
            return defn

        def parse_pattern(line):
            pattern = Pattern()
            while True:
                field = None
                if line.startswith("(*)"):
                    # TODO: move this two conditions lower
                    field = WildcardField()
                    line = line[3:]
                elif line.startswith("(**)"):
                    # TODO: move this one condition lower
                    field = SlurpField()
                    line = line[4:]
                elif line.startswith("("):
                    # definition recall, uses _DEF_NAME for definition name
                    line = line[1:]
                    (word, line) = re_consume(TagMatcher._DEF_NAME, line)
                    if not word:
                        raise ValueError("invalid definition reference: %s" % (line,))
                    (_skip, line) = re_consume(TagMatcher._SPACE, line)
                    if not line.startswith(")"):
                        raise ValueError("unclosed definition reference")
                    line = line[1:]
                    if word in definitions:
                        field = DefinitionField(definitions[word])
                    else:
                        raise ValueError("unknown definition: %s" % (word,))
                elif line.startswith("["):
                    # in-line word set, uses multiple _TAG_FRAGMENTs separated
                    # with _SEPARATOR
                    line = line[1:]
                    (_skip, line) = re_consume(TagMatcher._SEPARATOR, line)
                    words = []
                    while not line.startswith("]"):
                        (word, line) = re_consume(TagMatcher._TAG_FRAGMENT, line)
                        if not word and line == "":
                            raise ValueError("unclosed definition")
                        elif not word:
                            raise ValueError("invalid definition: %s" % (line,))
                        words.append(word)
                        (_skip, line) = re_consume(TagMatcher._SEPARATOR, line)
                    # line.startswith("]")
                    line = line[1:]
                    field = ListField(words)
                elif line.startswith("/"):
                    # in-line regexp definition
                    (regexp, line) = re_consume(TagMatcher._REGEXP, line)
                    if not regexp:
                        raise ValueError("invalid regexp: %s" % (line,))
                    field = RegexpField(regexp)
                else:
                    (word, line) = re_consume(TagMatcher._TAG_FRAGMENT, line)
                    if not word:
                        raise ValueError("unrecognized thing: %s" % (line,))
                    field = LiteralField(word)

                # there could be space after recent token
                (_skip, line) = re_consume(TagMatcher._SPACE, line)

                # now either ": _FIELD_NAME ." for location field name or just
                # "." to terminate the field
                if line.startswith(":"):
                    line = line[1:]
                    (_skip, line) = re_consume(TagMatcher._SPACE, line)
                    (word, line) = re_consume(TagMatcher._FIELD_NAME, line)
                    if not word:
                        raise ValueError("invalid location field name: %s" % (line,))
                    field.set_name(word)
                    (_skip, line) = re_consume(TagMatcher._SPACE, line)

                pattern.add(field)

                if line == "":
                    break
                if not line.startswith("."):
                    raise ValueError("unrecognized thing: %s" % (line,))
                # skip the period and any space after it
                line = line[1:]
                (_skip, line) = re_consume(TagMatcher._SPACE, line)
            return pattern

        # }}}
        #--------------------------------------------------
        # common useful functions for parsing {{{

        def re_consume(regexp, line):
            match = regexp.match(line)
            if match:
                s = match.start() # should be 0
                e = match.end()
                return (line[s:e], line[e:])
            else:
                return (None, line)

        # }}}
        #--------------------------------------------------

        prev_line = None
        for line in open(self.config):
            line = line.rstrip()
            if line == "" or line.startswith("#"):
                continue
            if TagMatcher._CONTINUATION.match(line):
                if prev_line is None:
                    raise ValueError("continuation can't be the first line")
                prev_line += line
                continue
            # not a continuation; process what we have and set prev_line
            # to current one
            process_line(prev_line)
            prev_line = line
        process_line(prev_line)

        self.patterns = patterns

#-----------------------------------------------------------------------------
# vim:ft=python:foldmethod=marker

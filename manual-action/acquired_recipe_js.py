"""Inert, bounded parser for the supported ForkRecipe JavaScript data subset.

This is not a JavaScript interpreter or an AST evaluation facility. It recognizes
only literal objects/arrays and a small set of exact export wrappers. Every byte
must belong to that grammar. Unsupported members must be quarantined by the
archive adapter, not repaired, executed, imported, or passed to a JS runtime.

Original JavaScript remains the provenance authority; parsed numeric values do
not replace original numeric lexemes, source ratios, licenses or author credits.
"""
from __future__ import annotations

import math
import re


VERSION = 'offmenu-acquired-static-javascript/1'
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 64
MAX_TOKENS = 250000
_IDENTIFIER = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
_NUMBER = re.compile(r'-?(?:(?:0|[1-9][0-9]*)(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?')
_LINE_END = re.compile(r'[\r\n\u2028\u2029]')
_PROTOTYPE_KEYS = frozenset(('__proto__', 'prototype', 'constructor'))
_PUNCTUATION = frozenset('{}[]:;,=.')
_ESCAPES = {'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t',
            'v': '\v', '0': '\0', '\\': '\\', '/': '/', '"': '"',
            "'": "'", '`': '`', '$': '$'}


class UnsupportedJavaScript(ValueError):
    """Input is outside the supported data grammar (messages contain no input)."""


def _reject(reason):
    raise UnsupportedJavaScript(reason)


class _Parser:
    def __init__(self, text, max_source_bytes, max_depth, max_tokens):
        if not isinstance(text, str):
            _reject('javascript_input_not_text')
        if len(text) > max_source_bytes:
            _reject('javascript_size_cap')
        try:
            size = len(text.encode('utf-8'))
        except UnicodeError:
            _reject('javascript_invalid_unicode')
        if size > max_source_bytes:
            _reject('javascript_size_cap')
        self.text = text.removeprefix('\ufeff')
        self.offset = self.tokens = 0
        self.max_depth, self.max_tokens = max_depth, max_tokens
        self.cached = None

    def _space(self):
        while self.offset < len(self.text):
            if self.text[self.offset].isspace():
                self.offset += 1
            elif self.text.startswith('//', self.offset):
                end = _LINE_END.search(self.text, self.offset + 2)
                self.offset = end.end() if end else len(self.text)
            elif self.text.startswith('/*', self.offset):
                end = self.text.find('*/', self.offset + 2)
                if end == -1:
                    _reject('javascript_unterminated_comment')
                self.offset = end + 2
            else:
                return

    def _unicode_escape(self, width):
        if width == 4 and self.text[self.offset:self.offset + 1] == '{':
            end = self.text.find('}', self.offset + 1, self.offset + 9)
            if end == -1:
                _reject('javascript_invalid_unicode_escape')
            digits = self.text[self.offset + 1:end]
            self.offset = end + 1
            if not 1 <= len(digits) <= 6:
                _reject('javascript_invalid_unicode_escape')
        else:
            digits = self.text[self.offset:self.offset + width]
            self.offset += width
            if len(digits) != width:
                _reject('javascript_invalid_unicode_escape')
        if re.fullmatch(r'[0-9a-fA-F]+', digits) is None:
            _reject('javascript_invalid_unicode_escape')
        value = int(digits, 16)
        if value > 0x10ffff:
            _reject('javascript_invalid_unicode_escape')
        return chr(value)

    def _string(self, quote):
        self.offset += 1
        parts = []
        while self.offset < len(self.text):
            char = self.text[self.offset]
            self.offset += 1
            if char == quote:
                result = ''.join(parts)
                # JS \uXXXX permits surrogate pairs. Combine valid pairs and
                # reject lone surrogates so downstream UTF-8 JSON stays valid.
                if any(0xd800 <= ord(c) <= 0xdfff for c in result):
                    try:
                        result = result.encode('utf-16-le', 'surrogatepass').decode('utf-16-le')
                    except UnicodeError:
                        _reject('javascript_unpaired_surrogate')
                return result
            if quote == '`' and char == '$' and self.text[self.offset:self.offset + 1] == '{':
                _reject('javascript_template_interpolation')
            if char in '\r\n' and quote != '`':
                _reject('javascript_string_linebreak')
            if char == '\r' and quote == '`':
                # ECMAScript normalizes template CR/CRLF to LF.
                if self.text[self.offset:self.offset + 1] == '\n':
                    self.offset += 1
                parts.append('\n')
            elif char != '\\':
                parts.append(char)
            else:
                if self.offset >= len(self.text):
                    _reject('javascript_unterminated_string')
                escaped = self.text[self.offset]
                self.offset += 1
                if escaped in ('\n', '\r', '\u2028', '\u2029'):
                    if escaped == '\r' and self.text[self.offset:self.offset + 1] == '\n':
                        self.offset += 1
                elif escaped in ('u', 'x'):
                    parts.append(self._unicode_escape(4 if escaped == 'u' else 2))
                elif escaped in _ESCAPES:
                    if escaped == '0' and self.text[self.offset:self.offset + 1].isdigit():
                        _reject('javascript_legacy_octal_escape')
                    parts.append(_ESCAPES[escaped])
                else:
                    _reject('javascript_unsupported_escape')
        _reject('javascript_unterminated_string')

    def _next(self):
        self._space()
        self.tokens += 1
        if self.tokens > self.max_tokens:
            _reject('javascript_token_cap')
        if self.offset == len(self.text):
            return ('eof', None)
        char = self.text[self.offset]
        if char in ('"', "'", '`'):
            return ('string', self._string(char))
        number = _NUMBER.match(self.text, self.offset)
        if number:
            lexeme = number.group()
            self.offset = number.end()
            if len(lexeme) > 256:
                _reject('javascript_numeric_limit')
            try:
                value = float(lexeme) if any(c in lexeme for c in '.eE') else int(lexeme)
            except (ValueError, OverflowError):
                _reject('javascript_numeric_limit')
            if isinstance(value, float) and not math.isfinite(value):
                _reject('javascript_nonfinite_number')
            return ('number', value)
        identifier = _IDENTIFIER.match(self.text, self.offset)
        if identifier:
            self.offset = identifier.end()
            return ('identifier', identifier.group())
        if char in _PUNCTUATION:
            self.offset += 1
            return (char, char)
        _reject('javascript_unsupported_token')

    def peek(self):
        if self.cached is None:
            self.cached = self._next()
        return self.cached

    def pop(self):
        token = self.peek()
        self.cached = None
        return token

    def take(self, kind, value=None):
        token = self.pop()
        if token[0] != kind or value is not None and token[1] != value:
            _reject('javascript_unsupported_structure')
        return token[1]

    def optional(self, kind):
        if self.peek()[0] == kind:
            self.pop()
            return True
        return False

    def value(self, depth=0):
        if depth > self.max_depth:
            _reject('javascript_depth_cap')
        kind, value = self.peek()
        if kind in ('string', 'number'):
            self.pop()
            return value
        if kind == 'identifier' and value in ('true', 'false', 'null'):
            self.pop()
            return {'true': True, 'false': False, 'null': None}[value]
        if kind == '{':
            self.pop()
            result = {}
            if not self.optional('}'):
                while True:
                    key_type, key = self.pop()
                    if key_type not in ('string', 'identifier'):
                        _reject('javascript_object_key_not_literal')
                    if key in _PROTOTYPE_KEYS:
                        _reject('javascript_prototype_key')
                    if key in result:
                        _reject('javascript_duplicate_key')
                    self.take(':')
                    result[key] = self.value(depth + 1)
                    if self.optional('}'):
                        break
                    self.take(',')
                    if self.optional('}'):
                        break
            return result
        if kind == '[':
            self.pop()
            result = []
            if not self.optional(']'):
                while True:
                    result.append(self.value(depth + 1))
                    if self.optional(']'):
                        break
                    self.take(',')
                    if self.optional(']'):
                        break
            return result
        _reject('javascript_nonliteral_value')

    def export(self, name=None):
        kind, value = self.peek()
        if (kind, value) == ('identifier', 'export'):
            self.pop()
            self.take('identifier', 'default')
        elif (kind, value) == ('identifier', 'module'):
            self.pop()
            self.take('.')
            self.take('identifier', 'exports')
            self.take('=')
        else:
            _reject('javascript_unsupported_export')
        if name is not None:
            self.take('identifier', name)
            return None
        return self.value()

    def document(self):
        if self.peek() == ('identifier', 'const'):
            self.pop()
            name = self.take('identifier')
            if name in _PROTOTYPE_KEYS or name in ('true', 'false', 'null'):
                _reject('javascript_invalid_binding')
            self.take('=')
            result = self.value()
            self.optional(';')
            self.export(name)
        elif self.peek()[0] == '{':
            # A file containing one bare data object is also inert. This is not
            # a JavaScript block statement: the same literal grammar applies.
            result = self.value()
        else:
            result = self.export()
        self.optional(';')
        self.take('eof')
        if not isinstance(result, dict):
            _reject('javascript_recipe_root_not_object')
        return result


def parse_recipe_javascript(text, *, max_source_bytes=MAX_SOURCE_BYTES,
                            max_depth=MAX_DEPTH, max_tokens=MAX_TOKENS):
    """Parse one literal recipe object or raise sanitized ``ValueError``.

    Supported wrappers are a bare object, ``export default OBJECT``,
    ``module.exports = OBJECT``, or a single ``const NAME = OBJECT`` followed by
    either export form referring to exactly NAME. Semicolons are optional. No
    other statements, bindings, identifier values, computed keys, method/getter
    definitions, import syntax, spreads, calls, or interpolation are supported.
    """
    if not all(isinstance(x, int) and not isinstance(x, bool) and x > 0
               for x in (max_source_bytes, max_depth, max_tokens)):
        raise ValueError('javascript_invalid_parser_limit')
    # A caller can tighten limits, never disable the reviewed hard bounds.
    parser = _Parser(text, min(max_source_bytes, MAX_SOURCE_BYTES),
                     min(max_depth, MAX_DEPTH), min(max_tokens, MAX_TOKENS))
    return parser.document()

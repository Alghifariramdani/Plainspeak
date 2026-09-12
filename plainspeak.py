#!/usr/bin/env python3
"""
Plainspeak
==========

An esoteric programming language where every single line of code must be
a grammatically plausible English sentence, and (just like English prose)
every sentence must end with a period "." — no period, no valid line.

Run a program with:

    python3 plainspeak.py yourprogram.eng

See README section at the bottom of this file (or run with no script and
read the module docstring) for the full sentence reference: variables,
arithmetic, printing, input, conditionals, loops, lists, and functions.
"""

import random
import re
import sys


class PlainspeakError(Exception):
    """Raised for anything that isn't a properly-formed Plainspeak sentence."""


class ReturnSignal(Exception):
    """Internal control-flow signal used to unwind out of a function call
    when a 'Return ...' sentence runs."""

    def __init__(self, value):
        super().__init__()
        self.value = value


# ---------------------------------------------------------------------------
# Sentence patterns
#
# Every pattern below is matched against a line with its trailing "."
# already removed. Where phrases could overlap (e.g. comparison operators),
# the more specific / longer phrase is listed first.
# ---------------------------------------------------------------------------

NOTE_RE = re.compile(r'^Note that .+$', re.IGNORECASE)

LET_RE = re.compile(r'^Let (.+?) be (.+)$', re.IGNORECASE)
SET_RE = re.compile(r'^Set (.+?) to (.+)$', re.IGNORECASE)

INCREASE_RE = re.compile(r'^Increase (.+?) by (.+)$', re.IGNORECASE)
DECREASE_RE = re.compile(r'^Decrease (.+?) by (.+)$', re.IGNORECASE)

PRINT_RE = re.compile(r'^(?:Print|Say) (.+)$', re.IGNORECASE)
ASK_RE = re.compile(r'^Ask (?:the user )?for (.+?) and call it (.+)$', re.IGNORECASE)

IF_START_RE = re.compile(r'^If (.+?), start doing the following$', re.IGNORECASE)
ELSE_RE = re.compile(r'^Otherwise, start doing the following$', re.IGNORECASE)
REPEAT_START_RE = re.compile(r'^Repeat (.+?) times, start doing the following$', re.IGNORECASE)
WHILE_START_RE = re.compile(r'^While (.+?), start doing the following$', re.IGNORECASE)
FOR_EACH_RE = re.compile(r'^For each (.+?) in (.+?), start doing the following$', re.IGNORECASE)
STOP_RE = re.compile(r'^Stop doing that$', re.IGNORECASE)

FUNC_DEF_WITH_PARAMS_RE = re.compile(r'^To (.+?) with (.+?), do the following$', re.IGNORECASE)
FUNC_DEF_NOARGS_RE = re.compile(r'^To (.+?), do the following$', re.IGNORECASE)
FUNC_END_RE = re.compile(r'^That is the end of (.+?)$', re.IGNORECASE)
RETURN_RE = re.compile(r'^Return (.+)$', re.IGNORECASE)

CALL_WITH_TARGET_RE = re.compile(r'^Call (.+?) with (.+?) and call it (.+)$', re.IGNORECASE)
CALL_NOARGS_WITH_TARGET_RE = re.compile(r'^Call (.+?) and call it (.+)$', re.IGNORECASE)
CALL_WITH_NO_TARGET_RE = re.compile(r'^Call (.+?) with (.+)$', re.IGNORECASE)
CALL_PLAIN_RE = re.compile(r'^Call (.+)$', re.IGNORECASE)

ADD_TO_LIST_RE = re.compile(r'^Add (.+?) to (.+)$', re.IGNORECASE)
REMOVE_ITEM_RE = re.compile(r'^Remove (?:the )?item (?:at position|number) (.+?) from (.+)$', re.IGNORECASE)

# Block terminators that end a parse_block early without being consumed by it.
_BLOCK_ENDERS = (STOP_RE, ELSE_RE, FUNC_END_RE)

# Two-operand "X and Y and call it Z" style operations, tried in order.
# Each entry is (regex, arity, function, literal_fallback). Regex capture
# groups are the raw, not-yet-evaluated operand text; 'target' is always
# the last group. When literal_fallback is True, an operand that isn't a
# known variable/number/string falls back to its raw text (so e.g.
# "Make hello uppercase..." works without quoting "hello").
CALL_OPS = [
    (re.compile(r'^Add (.+?) and (.+?) and call it (.+)$', re.IGNORECASE), 2, lambda a, b: a + b, False),
    (re.compile(r'^Subtract (.+?) from (.+?) and call it (.+)$', re.IGNORECASE), 2, lambda a, b: b - a, False),
    (re.compile(r'^Multiply (.+?) and (.+?) and call it (.+)$', re.IGNORECASE), 2, lambda a, b: a * b, False),
    (re.compile(r'^Divide (.+?) by (.+?) and call it (.+)$', re.IGNORECASE), 2, lambda a, b: a / b, False),
    (re.compile(r'^Find the remainder of (.+?) divided by (.+?) and call it (.+)$', re.IGNORECASE), 2, lambda a, b: a % b, False),
    (re.compile(r'^Raise (.+?) to the power of (.+?) and call it (.+)$', re.IGNORECASE), 2, lambda a, b: a ** b, False),
    (re.compile(r'^Find the larger of (.+?) and (.+?) and call it (.+)$', re.IGNORECASE), 2, lambda a, b: max(a, b), False),
    (re.compile(r'^Find the smaller of (.+?) and (.+?) and call it (.+)$', re.IGNORECASE), 2, lambda a, b: min(a, b), False),
    (re.compile(r'^Round (.+?) and call it (.+)$', re.IGNORECASE), 1, lambda a: round(a), False),
    (re.compile(r'^Make (.+?) uppercase and call it (.+)$', re.IGNORECASE), 1, lambda a: str(a).upper(), True),
    (re.compile(r'^Make (.+?) lowercase and call it (.+)$', re.IGNORECASE), 1, lambda a: str(a).lower(), True),
]

# Value-expression patterns, checked inside parse_value (before number/
# string/variable resolution) so they can appear anywhere a value can:
# "Let the size be the length of fruits.", "Print the item at position 2 in fruits."
RANDOM_RE = re.compile(r'^a random number between (.+?) and (.+?)$', re.IGNORECASE)
LENGTH_RE = re.compile(r'^(?:the )?length of (.+)$', re.IGNORECASE)
ITEM_AT_RE = re.compile(r'^(?:the )?item (?:at position|number) (.+?) (?:in|of) (.+)$', re.IGNORECASE)

# Comparison operators, longest phrase first so e.g. "less than or equal to"
# isn't cut short by the plain "less than" branch.
COND_RE = re.compile(
    r'^(.+?) is (greater than or equal to|less than or equal to|not equal to'
    r'|greater than|less than|equal to) (.+)$',
    re.IGNORECASE,
)
BOOL_COND_RE = re.compile(r'^(.+?) is (true|false)$', re.IGNORECASE)

# Phrases containing "and"/"or" that must not be split when breaking a
# compound condition into its "and"/"or" parts.
_PROTECTED_PHRASES = ('greater than or equal to', 'less than or equal to')
_OR_SPLIT_RE = re.compile(r'\s+or\s+', re.IGNORECASE)
_AND_SPLIT_RE = re.compile(r'\s+and\s+', re.IGNORECASE)
_PLACEHOLDER = '\x00'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ARTICLES = ('the ', 'a ', 'an ')


def normalize_var(name):
    """Turn a natural-language name into a plain identifier.

    "the score" -> "score", "the total" -> "total", "Counter" -> "counter"
    """
    name = name.strip().lower()
    for article in _ARTICLES:
        if name.startswith(article):
            name = name[len(article):]
            break
    return re.sub(r'\s+', '_', name.strip())


def split_list(text):
    """Split a natural-language list like 'x, y and z' or 'x and y' into
    ['x', 'y', 'z'], used for function parameter/argument lists."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r'\s*,\s*|\s+and\s+', text)
    return [p.strip() for p in parts if p.strip()]


def parse_value(token, env):
    """Resolve a token to a Python value: a special expression (length,
    random number, list item...), a quoted string, a number, an empty
    list, or a variable already present in the environment."""
    token = token.strip()

    m = RANDOM_RE.match(token)
    if m:
        lo, hi = m.groups()
        return random.randint(int(parse_value(lo, env)), int(parse_value(hi, env)))

    m = LENGTH_RE.match(token)
    if m:
        return len(parse_value(m.group(1), env))

    m = ITEM_AT_RE.match(token)
    if m:
        idx_tok, list_tok = m.groups()
        lst = parse_value(list_tok, env)
        idx = int(parse_value(idx_tok, env))
        try:
            return lst[idx - 1]
        except (IndexError, TypeError):
            raise PlainspeakError(f"There is no item at position {idx} in '{list_tok}'.")

    if token.lower() in ('an empty list', 'empty list'):
        return []

    if token.lower() == 'true':
        return True
    if token.lower() == 'false':
        return False

    # Quoted string literal: "like this" or 'like this'
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        return token[1:-1]

    # Number (int first, then float)
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass

    # Variable lookup
    key = normalize_var(token)
    if key in env:
        return env[key]

    raise PlainspeakError(f"I don't know what '{token}' refers to.")


def _protect(text):
    for phrase in _PROTECTED_PHRASES:
        text = re.sub(phrase, phrase.replace(' ', _PLACEHOLDER), text, flags=re.IGNORECASE)
    return text


def _unprotect(text):
    return text.replace(_PLACEHOLDER, ' ')


def _compare(lv, op, rv):
    op = op.lower()
    if op == 'greater than':
        return lv > rv
    if op == 'less than':
        return lv < rv
    if op == 'equal to':
        return lv == rv
    if op == 'not equal to':
        return lv != rv
    if op == 'greater than or equal to':
        return lv >= rv
    if op == 'less than or equal to':
        return lv <= rv
    raise PlainspeakError(f"Unknown comparison: '{op}'.")  # pragma: no cover


def eval_condition(text, env):
    """Evaluate a condition, including compound 'X and Y' / 'X or Y' forms.

    A single comparison is tried first (against the *whole* string); only
    if that doesn't cleanly resolve do we fall back to splitting on a
    top-level 'and'/'or', so operator phrases like 'less than or equal to'
    are never mistaken for a logical 'or'.
    """
    text = text.strip()

    m = COND_RE.match(text)
    if m:
        left, op, right = m.groups()
        try:
            return _compare(parse_value(left, env), op, parse_value(right, env))
        except PlainspeakError:
            pass  # might actually be a compound condition; fall through

    m = BOOL_COND_RE.match(text)
    if m:
        subject, truthiness = m.groups()
        try:
            return bool(parse_value(subject, env)) == (truthiness.lower() == 'true')
        except PlainspeakError:
            pass

    protected = _protect(text)
    or_parts = _OR_SPLIT_RE.split(protected)
    if len(or_parts) > 1:
        return any(eval_condition(_unprotect(p), env) for p in or_parts)
    and_parts = _AND_SPLIT_RE.split(protected)
    if len(and_parts) > 1:
        return all(eval_condition(_unprotect(p), env) for p in and_parts)

    raise PlainspeakError(f"I can't understand this condition: '{text}'.")


# ---------------------------------------------------------------------------
# Parsing: lines -> a tree of statement dicts
# ---------------------------------------------------------------------------

def load_sentences(path):
    """Read the file and return a list of (line_number, sentence_without_period)."""
    sentences = []
    with open(path, encoding='utf-8') as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            if not line.endswith('.'):
                raise PlainspeakError(
                    f"Line {lineno}: every sentence must end with a period. "
                    f"Offending line: '{line}'"
                )
            sentences.append((lineno, line[:-1]))
    return sentences


def parse_simple(lineno, text):
    """Parse a single, non-block sentence into a leaf statement node."""
    if NOTE_RE.match(text):
        return {'type': 'noop'}

    for regex, arity, func, literal_fallback in CALL_OPS:
        m = regex.match(text)
        if m:
            groups = m.groups()
            args, target = groups[:arity], groups[-1]
            return {
                'type': 'call_op', 'func': func, 'args': args, 'target': target,
                'literal_fallback': literal_fallback, 'line': lineno,
            }

    m = INCREASE_RE.match(text)
    if m:
        var, amount = m.groups()
        return {'type': 'nudge', 'sign': 1, 'var': var, 'amount': amount, 'line': lineno}

    m = DECREASE_RE.match(text)
    if m:
        var, amount = m.groups()
        return {'type': 'nudge', 'sign': -1, 'var': var, 'amount': amount, 'line': lineno}

    m = ASK_RE.match(text)
    if m:
        prompt, target = m.groups()
        return {'type': 'ask', 'prompt': prompt, 'target': target, 'line': lineno}

    m = RETURN_RE.match(text)
    if m:
        return {'type': 'return', 'value': m.group(1), 'line': lineno}

    m = REMOVE_ITEM_RE.match(text)
    if m:
        idx_tok, list_tok = m.groups()
        return {'type': 'list_remove', 'index': idx_tok, 'list': list_tok, 'line': lineno}

    m = CALL_WITH_TARGET_RE.match(text)
    if m:
        name, args, target = m.groups()
        return {'type': 'call', 'name': name, 'args': args, 'target': target, 'line': lineno}

    m = CALL_NOARGS_WITH_TARGET_RE.match(text)
    if m:
        name, target = m.groups()
        return {'type': 'call', 'name': name, 'args': '', 'target': target, 'line': lineno}

    m = CALL_WITH_NO_TARGET_RE.match(text)
    if m:
        name, args = m.groups()
        return {'type': 'call', 'name': name, 'args': args, 'target': None, 'line': lineno}

    m = CALL_PLAIN_RE.match(text)
    if m:
        return {'type': 'call', 'name': m.group(1), 'args': '', 'target': None, 'line': lineno}

    # "Add X to the list." must be tried only after the CALL_OPS "Add A and
    # B and call it C." pattern above, since that one is more specific.
    m = ADD_TO_LIST_RE.match(text)
    if m:
        item, list_name = m.groups()
        return {'type': 'list_add', 'item': item, 'list': list_name, 'line': lineno}

    m = PRINT_RE.match(text)
    if m:
        return {'type': 'print', 'value': m.group(1), 'line': lineno}

    m = LET_RE.match(text)
    if m:
        var, val = m.groups()
        return {'type': 'assign', 'var': var, 'value': val, 'line': lineno}

    m = SET_RE.match(text)
    if m:
        var, val = m.groups()
        return {'type': 'assign', 'var': var, 'value': val, 'line': lineno}

    raise PlainspeakError(
        f"Line {lineno}: I don't understand this sentence: '{text}.'"
    )


def _is_block_ender(text):
    return any(pattern.match(text) for pattern in _BLOCK_ENDERS)


def parse_block(sentences, i):
    """Parse sentences into a list of statement nodes until a block
    terminator (Stop / Otherwise / That is the end of...) is seen, without
    consuming that terminator, or input runs out."""
    body = []
    while i < len(sentences):
        lineno, text = sentences[i]
        if _is_block_ender(text):
            return body, i
        node, i = parse_statement(sentences, i)
        body.append(node)
    return body, i


def parse_statement(sentences, i):
    lineno, text = sentences[i]

    m = IF_START_RE.match(text)
    if m:
        cond = m.group(1)
        i += 1
        then_body, i = parse_block(sentences, i)
        else_body = []
        if i < len(sentences) and ELSE_RE.match(sentences[i][1]):
            i += 1
            else_body, i = parse_block(sentences, i)
        if i >= len(sentences) or not STOP_RE.match(sentences[i][1]):
            raise PlainspeakError(f"Line {lineno}: this 'If' never gets a matching 'Stop doing that.' sentence.")
        i += 1
        return {'type': 'if', 'cond': cond, 'then': then_body, 'else': else_body, 'line': lineno}, i

    m = REPEAT_START_RE.match(text)
    if m:
        count = m.group(1)
        i += 1
        body, i = parse_block(sentences, i)
        if i >= len(sentences) or not STOP_RE.match(sentences[i][1]):
            raise PlainspeakError(f"Line {lineno}: this 'Repeat' never gets a matching 'Stop doing that.' sentence.")
        i += 1
        return {'type': 'repeat', 'count': count, 'body': body, 'line': lineno}, i

    m = WHILE_START_RE.match(text)
    if m:
        cond = m.group(1)
        i += 1
        body, i = parse_block(sentences, i)
        if i >= len(sentences) or not STOP_RE.match(sentences[i][1]):
            raise PlainspeakError(f"Line {lineno}: this 'While' never gets a matching 'Stop doing that.' sentence.")
        i += 1
        return {'type': 'while', 'cond': cond, 'body': body, 'line': lineno}, i

    m = FOR_EACH_RE.match(text)
    if m:
        var, iterable = m.groups()
        i += 1
        body, i = parse_block(sentences, i)
        if i >= len(sentences) or not STOP_RE.match(sentences[i][1]):
            raise PlainspeakError(f"Line {lineno}: this 'For each' never gets a matching 'Stop doing that.' sentence.")
        i += 1
        return {'type': 'foreach', 'var': var, 'iterable': iterable, 'body': body, 'line': lineno}, i

    m = FUNC_DEF_WITH_PARAMS_RE.match(text)
    if not m:
        m = FUNC_DEF_NOARGS_RE.match(text)
        params_text = ''
    else:
        params_text = m.group(2)
    if m:
        name = m.group(1)
        params = split_list(params_text)
        i += 1
        body, i = parse_block(sentences, i)
        if i >= len(sentences) or not FUNC_END_RE.match(sentences[i][1]):
            raise PlainspeakError(
                f"Line {lineno}: the procedure '{name}' never gets a matching "
                f"'That is the end of {name}.' sentence."
            )
        i += 1
        return {'type': 'funcdef', 'name': name, 'params': params, 'body': body, 'line': lineno}, i

    if _is_block_ender(text):
        raise PlainspeakError(f"Line {lineno}: found '{text}.' with nothing open to close.")

    node = parse_simple(lineno, text)
    return node, i + 1


def parse_program(path):
    sentences = load_sentences(path)
    program, i = parse_block(sentences, 0)
    if i < len(sentences):
        lineno, text = sentences[i]
        raise PlainspeakError(f"Line {lineno}: unexpected sentence '{text}.'")
    return program


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run(nodes, env, functions):
    for node in nodes:
        exec_node(node, env, functions)


def call_function(name_token, args_text, functions, caller_env):
    key = normalize_var(name_token)
    if key not in functions:
        raise PlainspeakError(f"There's no procedure called '{name_token}'.")
    fn = functions[key]
    arg_values = [parse_value(a, caller_env) for a in split_list(args_text)]
    if len(arg_values) != len(fn['params']):
        raise PlainspeakError(
            f"'{name_token}' expects {len(fn['params'])} value(s) but got {len(arg_values)}."
        )
    local_env = dict(caller_env)
    for param, value in zip(fn['params'], arg_values):
        local_env[param] = value
    try:
        run(fn['body'], local_env, functions)
    except ReturnSignal as r:
        return r.value
    return None


def exec_node(node, env, functions):
    kind = node['type']

    if kind == 'noop':
        return

    if kind == 'funcdef':
        functions[normalize_var(node['name'])] = {
            'params': [normalize_var(p) for p in node['params']],
            'body': node['body'],
        }
        return

    if kind == 'return':
        raise ReturnSignal(parse_value(node['value'], env))

    if kind == 'call':
        result = call_function(node['name'], node['args'], functions, env)
        if node['target'] is not None:
            env[normalize_var(node['target'])] = result
        return

    if kind == 'assign':
        env[normalize_var(node['var'])] = parse_value(node['value'], env)
        return

    if kind == 'call_op':
        values = []
        for a in node['args']:
            try:
                values.append(parse_value(a, env))
            except PlainspeakError:
                if node['literal_fallback']:
                    values.append(a.strip())
                else:
                    raise
        env[normalize_var(node['target'])] = node['func'](*values)
        return

    if kind == 'nudge':
        key = normalize_var(node['var'])
        if key not in env:
            raise PlainspeakError(
                f"Line {node['line']}: '{node['var']}' hasn't been introduced with 'Let' or 'Set' yet."
            )
        env[key] = env[key] + node['sign'] * parse_value(node['amount'], env)
        return

    if kind == 'ask':
        answer = input(f"{node['prompt'].strip()}? ")
        try:
            value = int(answer)
        except ValueError:
            try:
                value = float(answer)
            except ValueError:
                value = answer
        env[normalize_var(node['target'])] = value
        return

    if kind == 'list_add':
        key = normalize_var(node['list'])
        if key not in env or not isinstance(env[key], list):
            raise PlainspeakError(f"Line {node['line']}: '{node['list']}' isn't a list yet.")
        try:
            value = parse_value(node['item'], env)
        except PlainspeakError:
            # Not a known variable/number/string -> treat the bare word(s)
            # as a literal item, e.g. "Add apple to the fruits."
            value = node['item'].strip()
        env[key].append(value)
        return

    if kind == 'list_remove':
        key = normalize_var(node['list'])
        if key not in env or not isinstance(env[key], list):
            raise PlainspeakError(f"Line {node['line']}: '{node['list']}' isn't a list yet.")
        idx = int(parse_value(node['index'], env))
        try:
            del env[key][idx - 1]
        except IndexError:
            raise PlainspeakError(f"Line {node['line']}: there is no item at position {idx} in '{node['list']}'.")
        return

    if kind == 'print':
        text = node['value']
        try:
            value = parse_value(text, env)
        except PlainspeakError:
            # Not a known variable/number/string -> treat as a literal
            # sentence fragment, e.g. "Print The score is high."
            value = text
        print(value)
        return

    if kind == 'if':
        run(node['then'] if eval_condition(node['cond'], env) else node['else'], env, functions)
        return

    if kind == 'repeat':
        count = parse_value(node['count'], env)
        for _ in range(int(count)):
            run(node['body'], env, functions)
        return

    if kind == 'while':
        while eval_condition(node['cond'], env):
            run(node['body'], env, functions)
        return

    if kind == 'foreach':
        iterable = parse_value(node['iterable'], env)
        var_key = normalize_var(node['var'])
        for item in iterable:
            env[var_key] = item
            run(node['body'], env, functions)
        return

    raise PlainspeakError(f"Unknown statement type '{kind}'.")  # pragma: no cover


def main(argv):
    if len(argv) != 2:
        print("Usage: python3 plainspeak.py <program.eng>", file=sys.stderr)
        return 1
    path = argv[1]
    try:
        program = parse_program(path)
        run(program, {}, {})
    except PlainspeakError as e:
        print(f"Plainspeak error: {e}", file=sys.stderr)
        return 1
    except ReturnSignal:
        print("Plainspeak error: 'Return' can only be used inside a procedure.", file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
# The Plainspeak Manual

Plainspeak is a programming language where every line of code has to be a
plausible English sentence, and — exactly like English prose — every
sentence has to end with a period (`.`). No period, no valid line. That's
the one rule everything else is built on.

This manual walks through every sentence form Plainspeak understands, what
it does, and the plain Python it's equivalent to under the hood (the
interpreter, `plainspeak.py`, is itself a Python program that reads your
`.eng` file and executes it).

Run a program with:
```
python3 plainspeak.py yourprogram.eng
```

---

## 1. The one hard rule: periods

Every non-blank line must end with `.`. The interpreter checks this before
it tries to understand anything else about the line.

```
Let x be 5          <- syntax error: no period
Let x be 5.          <- fine
```

Python equivalent: there isn't one — this is Plainspeak's own lexer rule,
checked line-by-line before parsing begins.

---

## 2. Comments

```
Note that this program calculates a total.
```

Any sentence starting with `Note that ...` is ignored entirely.

**Python equivalent:**
```python
# this program calculates a total
```

---

## 3. Variable names

Variable names in Plainspeak can be natural phrases: `the score`, `the
total`, `my counter`. Behind the scenes every name is *normalized*:

1. Lowercased.
2. A leading article (`the `, `a `, `an `) is stripped.
3. Remaining spaces become underscores.

So `the score`, `The Score`, and `score` all refer to the exact same
variable.

**Python equivalent:**
```python
def normalize_var(name):
    name = name.strip().lower()
    for article in ("the ", "a ", "an "):
        if name.startswith(article):
            name = name[len(article):]
            break
    return name.replace(" ", "_")
```
All variables live in one flat dictionary (`env`) — there are no separate
scopes at the top level, and no static typing.

---

## 4. Values

Anywhere a sentence expects a value, you can write:

| Plainspeak | Meaning | Python equivalent |
|---|---|---|
| `5`, `3.14` | a number | `5`, `3.14` |
| `"hello"` or `'hello'` | a string | `"hello"` |
| `true` / `false` | a boolean | `True` / `False` |
| `an empty list` | a new empty list | `[]` |
| `the score` | a variable's current value | `env["score"]` |
| `the length of the fruits` | the size of a list/string | `len(env["fruits"])` |
| `the item at position 2 in the fruits` | 1-based list indexing | `env["fruits"][2 - 1]` |
| `a random number between 1 and 6` | random integer, inclusive | `random.randint(1, 6)` |

Note list/index access is **1-based** ("position 1" is the first item),
unlike Python's 0-based indexing — the interpreter does the `- 1`
conversion for you.

---

## 5. Printing

```
Print the score.
Say the score.
```
`Print` and `Say` are interchangeable.

**Python equivalent:**
```python
print(env["score"])
```

If what follows isn't a known variable, number, or string, Plainspeak
doesn't error — it just prints the sentence fragment itself as literal
text:

```
Print The score is high.
```
→ prints `The score is high` (there's no variable called `the_score_is_high`,
so the raw text is printed instead).

**Gotcha:** if your literal text happens to exactly match an existing
variable name, Plainspeak will print that variable's *value*, not your
text. `Print score.` will print the number in `score`, not the word
"score".

---

## 6. Getting input

```
Ask for your name and call it the name.
```

**Python equivalent:**
```python
answer = input("your name? ")
try:
    value = int(answer)
except ValueError:
    try:
        value = float(answer)
    except ValueError:
        value = answer
env["name"] = value
```
The prompt text is whatever comes between `Ask for` and `and call it`; a
`?` is appended automatically. The typed answer is auto-converted to an
int or float when possible, otherwise kept as a string.

---

## 7. Assignment

```
Let the score be 0.
Set the score to 0.
```
`Let ... be ...` and `Set ... to ...` do exactly the same thing.

**Python equivalent:**
```python
env["score"] = 0
```

---

## 8. Arithmetic and other "call it" operations

These all follow the same shape: **do something to some value(s), and
name the result.**

| Plainspeak | Python equivalent |
|---|---|
| `Add 10 and 5 and call it the score.` | `score = 10 + 5` |
| `Subtract 3 from 10 and call it z.` | `z = 10 - 3` (note the order!) |
| `Multiply 4 and 6 and call it z.` | `z = 4 * 6` |
| `Divide 10 by 4 and call it z.` | `z = 10 / 4` (always true division) |
| `Find the remainder of 17 divided by 5 and call it r.` | `r = 17 % 5` |
| `Raise 2 to the power of 8 and call it p.` | `p = 2 ** 8` |
| `Find the larger of a and b and call it big.` | `big = max(a, b)` |
| `Find the smaller of a and b and call it small.` | `small = min(a, b)` |
| `Round 3.7 and call it rounded.` | `rounded = round(3.7)` |
| `Make hello uppercase and call it shout.` | `shout = "hello".upper()` |
| `Make WORLD lowercase and call it quiet.` | `quiet = "WORLD".lower()` |

**Important — `Subtract`'s word order:** "Subtract A from B" means
*take A away from B*, so the result is `B - A`, matching how you'd say
it out loud ("subtract 3 from 10" = 7, not -7).

**Bonus (no special syntax needed):** because Python's `+` and `*` work
on strings too, `Add` will concatenate strings and `Multiply` will repeat
them:
```
Let the greeting be "Hello, ".
Let the name be "Al".
Add the greeting and the name and call it the message.
```
→ `the message` becomes `"Hello, Al"` — same as Python's `"Hello, " + "Al"`.

For `Make ... uppercase/lowercase`, if the value you name isn't a known
variable/number/string, Plainspeak treats the bare word(s) as literal text
(same fallback trick as `Print`), so `Make hello uppercase and call it
shout.` works without needing quotes.

---

## 9. Increase / decrease

```
Increase the counter by 1.
Decrease the counter by 1.
```
**Python equivalent:**
```python
env["counter"] += 1
env["counter"] -= 1
```
The variable must already exist (created with `Let`/`Set`) — Plainspeak
errors out otherwise, since there's nothing to increase.

---

## 10. Conditions

### Comparisons
```
the score is greater than 10
the score is less than 10
the score is equal to 10
the score is not equal to 10
the score is greater than or equal to 10
the score is less than or equal to 10
```
**Python equivalent:** `score > 10`, `score < 10`, `score == 10`,
`score != 10`, `score >= 10`, `score <= 10`.

### Boolean checks
```
the flag is true
the flag is false
```
**Python equivalent:** `bool(flag) == True`, `bool(flag) == False`.

### Combining conditions
```
If a is greater than 5 and b is less than 10, start doing the following.
If a is less than 5 or b is less than 10, start doing the following.
```
**Python equivalent:**
```python
if a > 5 and b < 10:
    ...
if a < 5 or b < 10:
    ...
```
`and` binds tighter than `or`, same as in Python — but there's **no
support for parentheses**, so conditions with more than two clauses should
be tested carefully or broken into nested `If` statements.

---

## 11. If / Otherwise

```
If the score is greater than 10, start doing the following.
Print The score is high.
Otherwise, start doing the following.
Print The score is low.
Stop doing that.
```
`Otherwise, start doing the following.` (the "else" branch) is optional.
Every `If` block must be closed with exactly one `Stop doing that.`.

**Python equivalent:**
```python
if score > 10:
    print("The score is high")
else:
    print("The score is low")
```

---

## 12. Repeat loop (fixed count)

```
Repeat 5 times, start doing the following.
Print the counter.
Stop doing that.
```
**Python equivalent:**
```python
for _ in range(5):
    print(counter)
```

---

## 13. While loop

```
While the n is less than or equal to 5, start doing the following.
Increase the n by 1.
Stop doing that.
```
**Python equivalent:**
```python
while n <= 5:
    n += 1
```

---

## 14. Lists

```
Let the fruits be an empty list.
Add apple to the fruits.
Add banana to the fruits.
Remove the item at position 1 from the fruits.
Let the size be the length of the fruits.
Let the second fruit be the item at position 2 in the fruits.
```

**Python equivalent:**
```python
fruits = []
fruits.append("apple")
fruits.append("banana")
del fruits[1 - 1]
size = len(fruits)
second_fruit = fruits[2 - 1]
```

Bare, unquoted items (like `apple` above) are stored as literal text if
they aren't a known variable/number — same fallback behavior as `Print`.
Quoted items (`Add "apple" to the fruits.`) and variables both work too.

Printing a list prints Python's own representation of it, e.g.
`['apple', 'banana']` — Plainspeak doesn't reformat it.

---

## 15. For each (looping over a list)

```
For each fruit in the fruits, start doing the following.
Print fruit.
Stop doing that.
```
**Python equivalent:**
```python
for fruit in fruits:
    print(fruit)
```
The loop variable (`fruit`) is a normal variable for the duration of the
loop — it isn't cleaned up afterward, so it'll still hold its last value
once the loop ends.

---

## 16. Functions (procedures)

### Defining one
```
To find the square with n, do the following.
Multiply n and n and call it the result.
Return the result.
That is the end of find the square.
```
- Parameters go after `with`, separated by `and`/commas:
  `To combine with x and y, do the following.`
- No parameters: `To greet, do the following.`
- Every definition must be closed with `That is the end of <name>.`
- `Return ...` immediately exits the function with a value.

**Python equivalent:**
```python
def find_the_square(n):
    result = n * n
    return result
```

### Calling one
```
Call find the square with 5 and call it y.      # with args, keep result
Call greet and call it y.                        # no args, keep result
Call greet with "Al".                            # with args, discard result
Call greet.                                       # no args, discard result
```
**Python equivalent:**
```python
y = find_the_square(5)
y = greet()
greet("Al")
greet()
```

### Scoping — the important gotcha
When a function runs, it gets its own private copy of every variable that
existed at the point of the call, plus its parameters. It can **read**
outer variables, but any assignment it makes disappears once the function
returns — the only way to get a value back out is `Return`.

**Python equivalent (roughly):**
```python
def call_function(name, args, functions, caller_env):
    fn = functions[name]
    local_env = dict(caller_env)          # a *copy*, not a reference
    local_env.update(zip(fn["params"], args))
    try:
        run(fn["body"], local_env, functions)
    except ReturnSignal as r:
        return r.value
    return None
```
Recursion works fine, since each call gets its own fresh copy of the
environment:
```
To find the factorial with n, do the following.
If n is less than or equal to 1, start doing the following.
Return 1.
Stop doing that.
Subtract 1 from n and call it m.
Call find the factorial with m and call it sub_result.
Multiply n and sub_result and call it the result.
Return the result.
That is the end of find the factorial.
```

---

## 17. Block terminators at a glance

| Opens with... | Closes with... |
|---|---|
| `If ..., start doing the following.` | `Stop doing that.` (with optional `Otherwise, start doing the following.` in between) |
| `Repeat N times, start doing the following.` | `Stop doing that.` |
| `While ..., start doing the following.` | `Stop doing that.` |
| `For each X in Y, start doing the following.` | `Stop doing that.` |
| `To NAME [with PARAMS], do the following.` | `That is the end of NAME.` |

Mismatched or missing terminators are caught at parse time, before your
program ever runs, with the line number of the sentence that opened the
unclosed block.

---

## 18. Error messages

All errors are raised as a `PlainspeakError` and printed as
`Plainspeak error: ...` with a line number where possible. Common ones:

- Missing period at the end of a line.
- An unrecognized sentence shape ("I don't understand this sentence").
- A variable used before it's been introduced with `Let`/`Set`.
- A condition that doesn't parse as a comparison or a boolean/`and`/`or` combination.
- An `If`/`Repeat`/`While`/`For each`/`To` block missing its terminator.

**Python equivalent:** each of these is just a `raise PlainspeakError(...)`
at the point the interpreter gets confused — there's no recovery, the
program stops.

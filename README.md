# Custom Python Translator

A small rule-based tool that translates simple Python code into JavaScript, C, C++ or Java. It parses the input with Python's `ast` module and rewrites supported statements using per-language rules. It uses only the Python standard library.

## Usage

Requires Python 3.9+ (for `ast.unparse`).

```bash
python3 custom-translator.py
```

Enter the target language (`JavaScript`, `C`, `C++` or `Java`), then paste the Python code and finish with Ctrl-D (Ctrl-Z then Enter on Windows).

You can also pipe a file, putting the language on the first line:

```bash
{ echo JavaScript; cat example.py; } | python3 custom-translator.py
```

## Example

Input:

```python
total = 0
for i in range(1, 5):
    total += i
print("total", total)
```

JavaScript output:

```javascript
let total = 0;
for (let i = 1; i < 5; i += 1) {
    total += i;
}
console.log("total", total);
```

## Supported constructs

- Function definitions (`def`)
- `print(...)` and other function calls
- `for` loops over `range(...)`, and for-each loops (JavaScript, C++, Java)
- `while` loops, `if` / `else`
- Assignments, augmented assignments (`+=`, etc.) and `return`
- Arithmetic, comparison and boolean operators (`and`, `or`, `not`)

## Limitations

This is a simple rule-based translator, not a compiler, and the output may need manual edits:

- Types are not inferred beyond simple constants. Variables are declared with `let` (JavaScript), `auto` (C++), `var` (Java) or a basic C type, and function parameters are typed as `int` in C/C++ and `String` in Java.
- In C, `print` arguments that are not constants are formatted with `%d`.
- Lists, dictionaries, classes, comprehensions, imports and other unsupported statements are not translated; unsupported statements are emitted as `// Unsupported statement: ...` comments, and unsupported expressions are kept in Python syntax.
- For-each loops are not supported in C.

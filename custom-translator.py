import ast
import sys

# Define translation rules for each target language
translation_rules = {
    "JavaScript": {
        "print": "console.log",
        "def": "function",
        "for": "for",
        "if": "if",
        "else": "else",
        "range": "Array.from(Array",
        "True": "true",
        "False": "false",
    },
    "C": {
        "print": "printf",
        "def": "void",
        "for": "for",
        "if": "if",
        "else": "else",
        "range": "for (int i = 0; i <",
        "True": "1",
        "False": "0",
    },
    "C++": {
        "print": "std::cout",
        "def": "void",
        "for": "for",
        "if": "if",
        "else": "else",
        "range": "for (int i = 0; i <",
        "True": "true",
        "False": "false",
    },
    "Java": {
        "print": "System.out.println",
        "def": "public static void",
        "for": "for",
        "if": "if",
        "else": "else",
        "range": "for (int i = 0; i <",
        "True": "true",
        "False": "false",
    },
}

# Type names used when declaring variables in each target language
DECLARATION_TYPES = {
    "JavaScript": {"default": "let"},
    "C": {"int": "int", "float": "double", "str": "char*", "bool": "int", "default": "int"},
    "C++": {"default": "auto"},
    "Java": {"default": "var"},
}

# printf format specifiers for C
C_FORMATS = {int: "%d", float: "%f", str: "%s", bool: "%d"}


# Function to translate Python code to the target language
def translate_python_to_target(python_code, target_lang):
    rules = translation_rules.get(target_lang)
    if not rules:
        raise ValueError(f"Unsupported target language: {target_lang}")

    # Parse the Python code into an AST
    try:
        tree = ast.parse(python_code)
    except SyntaxError:
        raise ValueError("Invalid Python code")

    declared = set()

    def translate_expr(node):
        """Translate an expression node into target-language source."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return rules["True"] if node.value else rules["False"]
            if isinstance(node.value, str):
                escaped = node.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                return f'"{escaped}"'
            return str(node.value)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.BoolOp):
            operator = " && " if isinstance(node.op, ast.And) else " || "
            return "(" + operator.join(translate_expr(value) for value in node.values) + ")"
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return f"!({translate_expr(node.operand)})"
        if isinstance(node, ast.BinOp) and type(node.op) in BIN_OPS:
            return f"({translate_expr(node.left)} {_binop(node.op)} {translate_expr(node.right)})"
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in COMPARE_OPS:
            return f"{translate_expr(node.left)} {COMPARE_OPS[type(node.ops[0])]} {translate_expr(node.comparators[0])}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "print":
                return translate_print(node.args)
            args = ", ".join(translate_expr(arg) for arg in node.args)
            return f"{node.func.id}({args})"
        # Default case: keep the Python source for anything not handled above
        return ast.unparse(node)

    def translate_print(args):
        values = [translate_expr(arg) for arg in args]
        if target_lang == "C":
            formats = []
            for arg in args:
                value_type = type(arg.value) if isinstance(arg, ast.Constant) else int
                formats.append(C_FORMATS.get(value_type, "%d"))
            format_string = " ".join(formats) + "\\n"
            return f'{rules["print"]}("{format_string}"' + "".join(", " + value for value in values) + ")"
        if target_lang == "C++":
            return f"{rules['print']} << " + ' << " " << '.join(values or ['""']) + " << std::endl"
        if target_lang == "Java":
            return f"{rules['print']}(" + ' + " " + '.join(values or ['""']) + ")"
        return f"{rules['print']}({', '.join(values)})"

    def declaration_type(value):
        types = DECLARATION_TYPES[target_lang]
        if isinstance(value, ast.Constant):
            return types.get(type(value.value).__name__, types["default"])
        return types["default"]

    def translate_block(statements, indent):
        lines = []
        for statement in statements:
            lines.extend(translate_stmt(statement, indent))
        return lines

    def translate_stmt(node, indent):
        """Translate a statement node into a list of target-language lines."""
        pad = "    " * indent
        if isinstance(node, ast.FunctionDef):
            # Translate function definitions
            if target_lang == "Java":
                params = ", ".join("String " + arg.arg for arg in node.args.args)
            elif target_lang in ("C", "C++"):
                params = ", ".join("int " + arg.arg for arg in node.args.args)
            else:
                params = ", ".join(arg.arg for arg in node.args.args)
            declared.update(arg.arg for arg in node.args.args)
            return [f"{pad}{rules['def']} {node.name}({params}) {{"] + translate_block(node.body, indent + 1) + [f"{pad}}}"]
        if isinstance(node, ast.For):
            # Translate for loops; range() becomes a counting loop
            target = translate_expr(node.target)
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range" and 1 <= len(node.iter.args) <= 3:
                range_args = [translate_expr(arg) for arg in node.iter.args]
                start, stop, step = ("0", range_args[0], "1") if len(range_args) == 1 else (range_args + ["1"])[:3]
                counter = "let" if target_lang == "JavaScript" else "int"
                header = f"{rules['for']} ({counter} {target} = {start}; {target} < {stop}; {target} += {step}) {{"
            elif target_lang == "JavaScript":
                header = f"{rules['for']} (const {target} of {translate_expr(node.iter)}) {{"
            elif target_lang in ("C++", "Java"):
                loop_type = "auto" if target_lang == "C++" else "var"
                header = f"{rules['for']} ({loop_type} {target} : {translate_expr(node.iter)}) {{"
            else:
                return [f"{pad}// Unsupported loop (C has no for-each): {ast.unparse(node).splitlines()[0]}"]
            return [pad + header] + translate_block(node.body, indent + 1) + [f"{pad}}}"]
        if isinstance(node, ast.While):
            return [f"{pad}while ({translate_expr(node.test)}) {{"] + translate_block(node.body, indent + 1) + [f"{pad}}}"]
        if isinstance(node, ast.If):
            # Translate if / else statements
            lines = [f"{pad}{rules['if']} ({translate_expr(node.test)}) {{"] + translate_block(node.body, indent + 1)
            if node.orelse:
                lines += [f"{pad}}} {rules['else']} {{"] + translate_block(node.orelse, indent + 1)
            return lines + [f"{pad}}}"]
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            value = translate_expr(node.value)
            if name in declared:
                return [f"{pad}{name} = {value};"]
            declared.add(name)
            return [f"{pad}{declaration_type(node.value)} {name} = {value};"]
        if isinstance(node, ast.AugAssign) and type(node.op) in BIN_OPS:
            return [f"{pad}{translate_expr(node.target)} {_binop(node.op)}= {translate_expr(node.value)};"]
        if isinstance(node, ast.Return):
            return [f"{pad}return{(' ' + translate_expr(node.value)) if node.value else ''};"]
        if isinstance(node, ast.Expr):
            # Translate expressions (e.g., function calls)
            return [f"{pad}{translate_expr(node.value)};"]
        if isinstance(node, ast.Pass):
            return []
        # Anything else is reported instead of being translated incorrectly
        return [f"{pad}// Unsupported statement: {line}" for line in ast.unparse(node).splitlines()]

    return "\n".join(translate_block(tree.body, 0))


def _binop(op):
    """Return the operator symbol for a binary operator node."""
    return BIN_OPS[type(op)]


BIN_OPS = {
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Mod: "%",
    ast.FloorDiv: "/",
}
COMPARE_OPS = {
    ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
}

# Main function to run the translator
def main():
    print("Python Code Translator")
    print("Supported Target Languages: JavaScript, C, C++, Java")

    # Get user input (language names are matched case-insensitively)
    target_lang = input("Enter target language (JavaScript/C/C++/Java): ").strip()
    target_lang = {name.lower(): name for name in translation_rules}.get(target_lang.lower(), target_lang)

    # Read multi-line Python code until EOF (Ctrl-D, or Ctrl-Z then Enter on Windows)
    print("Enter Python code (finish with Ctrl-D, or Ctrl-Z then Enter on Windows):")
    python_code = sys.stdin.read()

    # Translate the code
    try:
        translated_code = translate_python_to_target(python_code, target_lang)
        print("\nTranslated Code:\n")
        print(translated_code)
    except Exception as e:
        print(f"Error: {e}")

# Run the program
if __name__ == "__main__":
    main()
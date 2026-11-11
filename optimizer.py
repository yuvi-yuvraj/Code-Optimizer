"""
Educational optimizer for a safe, deliberately limited C++ subset.

Supported optimization targets:
- scalar declarations and assignments
- arithmetic expressions using +, -, *, /, %
- return statements
- simple if/while/for blocks are preserved, not internally rewritten
- comments and preprocessor lines are preserved

This is not a replacement for a production C++ compiler. It avoids rewriting
expressions it cannot confidently understand.
"""
import ast
import re
from dataclasses import dataclass

IDENT = r"[A-Za-z_]\w*"
DECL_RE = re.compile(rf"^\s*(?:const\s+)?(?:int|long|short|float|double)\s+({IDENT})\s*(?:=\s*(.*?))?\s*;\s*$")
ASSIGN_RE = re.compile(rf"^\s*({IDENT})\s*=\s*(.*?)\s*;\s*$")
RETURN_RE = re.compile(r"^\s*return\b(.*?)\s*;\s*$")

def safe_eval(expr, env):
    """Evaluate only numeric constants and basic arithmetic via Python AST."""
    expr = expr.strip()
    if not expr or not re.fullmatch(r"[\w\s+\-*/%().]+", expr):
        return None
    expr = re.sub(r"\btrue\b", "1", expr)
    expr = re.sub(r"\bfalse\b", "0", expr)
    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None

    def visit(n):
        if isinstance(n, ast.Expression): return visit(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.Name) and n.id in env: return env[n.id]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = visit(n.operand)
            return +v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod)):
            a, b = visit(n.left), visit(n.right)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)): raise ValueError()
            if isinstance(n.op, ast.Add): return a + b
            if isinstance(n.op, ast.Sub): return a - b
            if isinstance(n.op, ast.Mult): return a * b
            if isinstance(n.op, (ast.Div, ast.FloorDiv)):
                if b == 0: raise ValueError()
                return a / b if isinstance(n.op, ast.Div) else a // b
            if isinstance(n.op, ast.Mod):
                if b == 0: raise ValueError()
                return a % b
        raise ValueError()
    try:
        return visit(node)
    except Exception:
        return None

def fmt_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)

def simplify(expr):
    original = expr
    # Basic identities, conservative and order-preserving.
    patterns = [
        (r"\b([A-Za-z_]\w*)\s*\+\s*0\b", r"\1"),
        (r"\b0\s*\+\s*([A-Za-z_]\w*)\b", r"\1"),
        (r"\b([A-Za-z_]\w*)\s*-\s*0\b", r"\1"),
        (r"\b([A-Za-z_]\w*)\s*\*\s*1\b", r"\1"),
        (r"\b1\s*\*\s*([A-Za-z_]\w*)\b", r"\1"),
        (r"\b([A-Za-z_]\w*)\s*/\s*1\b", r"\1"),
        (r"\b([A-Za-z_]\w*)\s*\*\s*0\b", "0"),
        (r"\b0\s*\*\s*([A-Za-z_]\w*)\b", "0"),
    ]
    for pat, repl in patterns:
        expr = re.sub(pat, repl, expr)
    return expr, expr != original

def optimize_cpp(source):
    lines = source.splitlines()
    output = []
    report = []
    env = {}
    declared = set()
    assigned = {}
    removed = set()
    transformed = []

    # Pass 1: constant folding, propagation, algebraic simplification, copy propagation.
    for idx, raw in enumerate(lines):
        s = raw.strip()
        if not s or s.startswith("//") or s.startswith("#") or s.startswith("/*") or s.startswith("*") or s.startswith("}") or s.startswith("{"):
            transformed.append(raw)
            continue
        indent = raw[:len(raw) - len(raw.lstrip())]
        m = DECL_RE.match(raw)
        a = ASSIGN_RE.match(raw)
        target = value = None
        is_decl = bool(m)
        if m:
            target, value = m.group(1), m.group(2)
            declared.add(target)
        elif a and not s.startswith(("if", "while", "for", "switch")):
            target, value = a.group(1), a.group(2)
        if target and value is not None:
            expr = value
            # Propagate known constants/copies only at simple token boundaries.
            before = expr
            for name, known in list(env.items()):
                expr = re.sub(rf"\b{re.escape(name)}\b", str(known), expr)
            if expr != before:
                report.append({"technique": "Constant / Copy Propagation",
                               "line": idx + 1, "detail": f"Replaced known variable(s) in '{before.strip()}'."})
            folded = safe_eval(expr, {})
            if folded is not None:
                expr = fmt_number(folded)
                report.append({"technique": "Constant Folding",
                               "line": idx + 1, "detail": f"Evaluated expression to {expr}."})
            expr, changed = simplify(expr)
            if changed:
                report.append({"technique": "Algebraic Simplification",
                               "line": idx + 1, "detail": f"Simplified expression to '{expr}'."})
            transformed.append(f"{indent}{target} = {expr};" if not is_decl else
                               f"{indent}{raw.strip().split()[0]} {target} = {expr};")
            # Track only literal constants and simple copies.
            if re.fullmatch(r"-?\d+(?:\.\d+)?", expr.strip()):
                env[target] = float(expr) if "." in expr else int(expr)
            elif re.fullmatch(IDENT, expr.strip()):
                env[target] = expr.strip()
            else:
                env.pop(target, None)
            assigned[target] = idx
        else:
            transformed.append(raw)
            # Any nontrivial control-flow line invalidates assumptions conservatively.
            if re.match(r"^\s*(if|else|while|for|switch|case|break|continue)\b", raw):
                env.clear()

    # Pass 2: count variable uses and remove dead simple assignments (not declarations with side effects).
    joined = "\n".join(transformed)
    use_counts = {}
    for name in declared | set(assigned):
        # Remove LHS occurrences from count by checking line patterns.
        count = 0
        for line in transformed:
            st = line.strip()
            dm = DECL_RE.match(line)
            am = ASSIGN_RE.match(line)
            if dm and dm.group(1) == name:
                rhs = dm.group(2) or ""
            elif am and am.group(1) == name:
                rhs = am.group(2)
            else:
                rhs = line
            count += len(re.findall(rf"\b{re.escape(name)}\b", rhs))
        use_counts[name] = count

    final_lines = []
    for idx, line in enumerate(transformed):
        dm = DECL_RE.match(line)
        am = ASSIGN_RE.match(line)
        target = dm.group(1) if dm else (am.group(1) if am else None)
        rhs = (dm.group(2) or "") if dm else (am.group(2) if am else "")
        # Do not remove declarations without initializers or statements with possible side effects.
        if target and use_counts.get(target, 0) == 0 and rhs and safe_eval(rhs, {}) is not None:
            report.append({"technique": "Dead Code Elimination", "line": idx + 1,
                           "detail": f"Removed unused assignment to '{target}'."})
            continue
        final_lines.append(line)

    # Pass 3: common subexpression elimination for repeated exact pure RHS expressions.
    # Keep it intentionally simple and only applies to identical arithmetic RHS text.
    seen = {}
    cse_lines = []
    for idx, line in enumerate(final_lines):
        dm = DECL_RE.match(line)
        am = ASSIGN_RE.match(line)
        if dm:
            target, rhs = dm.group(1), dm.group(2) or ""
        elif am:
            target, rhs = am.group(1), am.group(2)
        else:
            cse_lines.append(line); continue
        key = re.sub(r"\s+", "", rhs)
        if re.search(r"[+\-*/%]", rhs) and key in seen and not re.search(r"\b\d+\s*/\s*0\b", rhs):
            replacement = seen[key]
            prefix = line[:len(line) - len(line.lstrip())]
            if dm:
                typ = line.strip().split()[0]
                cse_lines.append(f"{prefix}{typ} {target} = {replacement};")
            else:
                cse_lines.append(f"{prefix}{target} = {replacement};")
            report.append({"technique": "Common Subexpression Elimination", "line": idx + 1,
                           "detail": f"Reused previously computed expression via '{replacement}'."})
        else:
            cse_lines.append(line)
            if re.search(r"[+\-*/%]", rhs):
                seen[key] = target

    optimized = "\n".join(cse_lines).strip() + "\n"
    original_lines = len([x for x in lines if x.strip()])
    optimized_lines = len([x for x in cse_lines if x.strip()])
    return {
        "optimized_code": optimized,
        "report": report,
        "summary": {
            "optimizations": len(report),
            "original_lines": original_lines,
            "optimized_lines": optimized_lines,
            "lines_removed": max(0, original_lines - optimized_lines),
            "techniques_used": sorted(set(x["technique"] for x in report))
        },
        "notes": [
            "This optimizer targets a safe educational subset of C++.",
            "Control-flow constructs are preserved; optimization is conservative around them.",
            "Always validate the optimized output with a C++ compiler and test program behavior."
        ]
    }

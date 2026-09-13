"""Six independent lenses, paired two-per-risk.

Each lens is a narrow, deterministic reading of Solidity source. No lens can
confirm anything on its own: a finding is only promoted when two lenses that
work from different evidence arrive at the same (contract, function, risk).
Disagreement is meaningful and is kept as a candidate, not published.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterator

from .memory import signature

PRIVILEGED = re.compile(r"\b(owner|admin|treasury|fee|rate|price|oracle|paused|router|beneficiary)\w*\b", re.I)
EXTERNAL_CALL = re.compile(r"\.(call|delegatecall|transfer|send)\s*[{(]|\.\w+\s*\{\s*value\s*:|\.(call|delegatecall|callcode)\.value\s*\(")
STATE_WRITE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(\[[^\]]*\]|\.\w+)*\s*(=|\+=|-=)[^=]")
FUNC = re.compile(r"^\s*function\s*(\w*)\s*\(", re.M)  # the name is empty for a 0.4 fallback: `function () payable`
ALIAS = re.compile(r"^\s*(?:var|\w+(?:\.\w+)?\s+storage)\s+(\w+)\s*=\s*([A-Za-z_]\w*)")


@dataclass(frozen=True)
class Sighting:
    lens: str
    risk: str
    contract: str
    function: str
    line: int
    evidence: str

    @property
    def key(self) -> str:
        return f"{self.contract}:{self.function}:{self.risk}"

    @property
    def signature(self) -> str:
        return signature(self.risk, self.evidence)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["signature"] = self.signature
        return d


@dataclass
class Function:
    name: str
    header: str
    body: str
    start_line: int


def parse_functions(src: str) -> list[Function]:
    """Split a Solidity file into functions by brace matching."""
    out: list[Function] = []
    for m in FUNC.finditer(src):
        open_idx = src.find("{", m.end())
        semi = src.find(";", m.end())
        if open_idx == -1 or (semi != -1 and semi < open_idx):
            continue  # interface / abstract declaration, no body
        depth, i = 0, open_idx
        while i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append(
            Function(
                name=m.group(1) or "fallback",  # what 0.6+ and Slither call the unnamed function
                header=src[m.start():open_idx],
                body=src[open_idx : i + 1],
                start_line=src[: m.start()].count("\n") + 1,
            )
        )
    return out


def state_vars(src: str) -> set[str]:
    """Contract-scope variable names (crude but honest: declarations outside functions)."""
    stripped = src
    for fn in parse_functions(src):
        stripped = stripped.replace(fn.body, "")
    pat = re.compile(r"^\s*(?:mapping\s*\([^)]*\)|address|uint\d*|int\d*|bool|bytes\d*|string)\s+"
                     r"(?:public|private|internal|immutable|constant|payable|\s)*\s*(\w+)\s*[;=]", re.M)
    return {m.group(1) for m in pat.finditer(stripped)}


def _is_external(fn: Function) -> bool:
    # Before 0.5 a function with no visibility keyword was public; from 0.5 the keyword is mandatory,
    # so "not internal and not private" is callable from outside on every compiler version.
    return not re.search(r"\b(internal|private)\b", fn.header)


def _is_readonly(fn: Function) -> bool:
    return bool(re.search(r"\b(view|pure)\b", fn.header))


def _lines(fn: Function) -> Iterator[tuple[int, str]]:
    for off, raw in enumerate(fn.body.splitlines()):
        yield fn.start_line + off, raw.strip().lstrip("{").strip()


# --------------------------- risk: reentrancy ---------------------------

def _storage_aliases(fn: Function, svars: set[str]) -> set[str]:
    """Local names that point into storage: `var acc = Acc[msg.sender]`, `Item storage it = items[id]`."""
    return {m.group(1) for _, text in _lines(fn) for m in [ALIAS.match(text)] if m and m.group(2) in svars}


def callorder_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: an external call happens before a state write in the same function."""
    out, svars = [], state_vars(src)
    for fn in parse_functions(src):
        if _is_readonly(fn):
            continue
        writes_storage = svars | _storage_aliases(fn, svars)
        call_at = None
        for ln, text in _lines(fn):
            if call_at is None and EXTERNAL_CALL.search(text):
                call_at = (ln, text)
                continue
            m = STATE_WRITE.match(text)
            if call_at and m and m.group(1) in writes_storage:
                out.append(Sighting("callorder-lens", "reentrancy", contract, fn.name, call_at[0], call_at[1]))
                break
    return out


def guard_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: a function moves value out and carries no reentrancy guard."""
    out = []
    for fn in parse_functions(src):
        if _is_readonly(fn) or not _is_external(fn):
            continue
        if re.search(r"nonReentrant|ReentrancyGuard|_locked|lock\(\)", fn.header + fn.body):
            continue
        for ln, text in _lines(fn):
            if EXTERNAL_CALL.search(text):
                out.append(Sighting("guard-lens", "reentrancy", contract, fn.name, ln, text))
                break
    return out


# ---------------------- risk: unguarded-state-write ----------------------

def modifier_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: externally callable, writes storage, carries no modifier at all."""
    out, svars = [], state_vars(src)
    known = {"external", "public", "payable", "returns", "virtual", "override", "memory", "calldata", "storage"}
    for fn in parse_functions(src):
        if _is_readonly(fn) or not _is_external(fn):
            continue
        tail = fn.header.split(")", 1)[-1]
        mods = {w for w in re.findall(r"\b[a-zA-Z_]\w*\b", tail)} - known
        if mods:
            continue
        for ln, text in _lines(fn):
            m = STATE_WRITE.match(text)
            if m and m.group(1) in svars:
                out.append(Sighting("modifier-lens", "unguarded-state-write", contract, fn.name, ln, text))
                break
    return out


def sender_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: writes a privileged-looking variable with no msg.sender check anywhere."""
    out, svars = [], state_vars(src)
    for fn in parse_functions(src):
        if _is_readonly(fn) or not _is_external(fn):
            continue
        if re.search(r"msg\.sender|_checkOwner|onlyOwner|hasRole|_msgSender", fn.body + fn.header):
            continue
        for ln, text in _lines(fn):
            m = STATE_WRITE.match(text)
            if m and m.group(1) in svars and PRIVILEGED.search(m.group(1)):
                out.append(Sighting("sender-lens", "unguarded-state-write", contract, fn.name, ln, text))
                break
    return out


# --------------------------- risk: unsafe-math ---------------------------
#
# One bug, two readings. The bug is storage arithmetic that can wrap round. wrap-lens reads the
# compiler's side: is wrapping even possible here (a pre-0.8 pragma, or an `unchecked` block)?
# bound-lens reads the code's side: does anything in the function bound the operands before the
# write? Neither reading alone is a finding. Checked arithmetic with no guard is a candidate;
# unchecked arithmetic behind a require is a candidate; only both together reach quorum.

ARITH = re.compile(r"^\s*(?:(?:uint|int)\d*\s+)?([A-Za-z_]\w*)\s*((?:\[[^\]]*\]|\.\w+)*)\s*(\+=|-=|\*=|=(?!=))\s*(.+?);")
RAW_OP = re.compile(r"[\w)\]]\s*[+*-]\s*[\w(]")
SAFE_MATH = re.compile(r"\.(add|sub|mul|div)\s*\(")
PRAGMA = re.compile(r"pragma\s+solidity\s*([^;]+);")
BOUND = re.compile(r"\b(require|assert|if)\s*\(.*(<=|>=|<|>)")
# Operands a 256-bit number cannot be wrapped by: what the chain itself bounds, and small constants.
CHAIN_BOUNDED = {"msg", "value", "block", "number", "timestamp", "now", "length", "sender"}


def _min_pragma(src: str) -> tuple[int, int] | None:
    """The lowest compiler version the file admits, as (major, minor). None if it names none."""
    versions = [tuple(int(x) for x in v.split(".")[:2])
                for m in PRAGMA.finditer(src) for v in re.findall(r"\d+\.\d+(?:\.\d+)?", m.group(1))]
    return min(versions) if versions else None


def _wrapping_lines(fn: Function, wraps_everywhere: bool) -> set[int]:
    """Lines where the compiler will let arithmetic wrap: every line before 0.8, else only `unchecked` blocks."""
    if wraps_everywhere:
        return {ln for ln, _ in _lines(fn)}
    out, depth = set(), 0
    for ln, text in _lines(fn):
        if depth == 0 and "unchecked" in text:
            depth = 0
        elif depth == 0:
            continue
        depth += text.count("{") - text.count("}")
        out.add(ln)
        if depth <= 0:
            depth = 0
    return out


def _storage_arithmetic(fn: Function, svars: set[str]) -> Iterator[tuple[int, str, str, str]]:
    """(line, text, target, rhs) for every raw + - * that writes storage or reads it into a local."""
    names = svars | _storage_aliases(fn, svars)
    for ln, text in _lines(fn):
        if text.startswith("//") or text.startswith("*"):
            continue
        m = ARITH.match(text)
        if not m:
            continue
        target, op, rhs = m.group(1), m.group(3), m.group(4)
        if SAFE_MATH.search(rhs) or (op == "=" and not RAW_OP.search(rhs)):
            continue
        touches_storage = target in names or any(re.search(rf"\b{re.escape(v)}\b", rhs) for v in names)
        if touches_storage:
            yield ln, text, target, rhs


def wrap_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: the compiler lets this storage arithmetic wrap (a pre-0.8 pragma, or an unchecked block)."""
    out, svars = [], state_vars(src)
    pragma = _min_pragma(src)
    wraps_everywhere = pragma is not None and pragma < (0, 8)
    for fn in parse_functions(src):
        if _is_readonly(fn):
            continue
        allowed = _wrapping_lines(fn, wraps_everywhere)
        for ln, text, _, _ in _storage_arithmetic(fn, svars):
            if ln in allowed:
                out.append(Sighting("wrap-lens", "unsafe-math", contract, fn.name, ln, text))
                break
    return out


def bound_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: nothing in the function bounds the operands before the storage arithmetic."""
    out, svars = [], state_vars(src)
    for fn in parse_functions(src):
        if _is_readonly(fn):
            continue
        for ln, text, target, rhs in _storage_arithmetic(fn, svars):
            rhs_names = set(re.findall(r"[A-Za-z_]\w*", rhs)) - {target}
            if not rhs_names - CHAIN_BOUNDED - set(re.findall(r"\b(?:uint|int)\d*\b", rhs)):
                continue  # `+= msg.value`, `+= 1`, `= block.number + 1`: nothing here can wrap a uint256
            operands = {target} | rhs_names
            before = [t for l, t in _lines(fn) if l < ln]
            guarded = any(BOUND.search(t) and any(re.search(rf"\b{re.escape(o)}\b", t) for o in operands) for t in before)
            if not guarded:
                out.append(Sighting("bound-lens", "unsafe-math", contract, fn.name, ln, text))
                break
    return out


LENSES = {
    "callorder-lens": callorder_lens,
    "guard-lens": guard_lens,
    "modifier-lens": modifier_lens,
    "sender-lens": sender_lens,
    "wrap-lens": wrap_lens,
    "bound-lens": bound_lens,
}

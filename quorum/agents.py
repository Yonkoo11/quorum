"""Eight independent lenses, paired two-per-risk.

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
# `addr.transfer(x)` and `addr.send(x)` forward 2300 gas and cannot re-enter, so they are not external
# calls for the reentrancy pair (Slither draws the same line). `token.transfer(to, amt)` is: an ERC777
# hook runs inside it.
EXTERNAL_CALL = re.compile(r"\.(call|delegatecall)\s*[{(]|\.\w+\s*\{\s*value\s*:|\.(call|delegatecall|callcode)\.value\s*\(|\.(transfer|send)\s*\([^()]*,")
DELETE = re.compile(r"^\s*delete\s+([A-Za-z_]\w*)")
CONTRACT = re.compile(r"^\s*(?:abstract\s+)?(?:contract|library)\s+(\w+)", re.M)
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
    start_line: int        # the `function` keyword
    body_line: int = 0     # the opening brace; evidence lines are counted from here
    contract: str = ""     # the enclosing contract, so a 0.4 constructor (same name) can be told apart


def _strip_comments(src: str) -> str:
    """Comments replaced by spaces, newlines kept, so braces and calls inside them are not parsed
    and every line number survives."""
    out, i, n = [], 0, len(src)
    while i < n:
        two = src[i:i + 2]
        if two == "//":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i)); i = j
        elif two == "/*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append("".join("\n" if c == "\n" else " " for c in src[i:j])); i = j
        elif src[i] == '"' or src[i] == "'":
            q = src[i]; j = i + 1
            while j < n and src[j] != q and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1]); i = j + 1
        else:
            out.append(src[i]); i += 1
    return "".join(out)


def parse_functions(src: str) -> list[Function]:
    """Split a Solidity file into functions by brace matching."""
    out: list[Function] = []
    src = _strip_comments(src)
    contracts = [(c.start(), c.group(1)) for c in CONTRACT.finditer(src)]
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
                body_line=src[:open_idx].count("\n") + 1,
                contract=next((name for start, name in reversed(contracts) if start < m.start()), ""),
            )
        )
    return out


_DECL = re.compile(r"^\s*(mapping\s*\([^)]*\)|address|uint\d*|int\d*|bool|bytes\d*|string)\s+"
                   r"(?:public|private|internal|immutable|constant|payable|\s)*\s*(\w+)\s*[;=]", re.M)


def _declarations(src: str) -> list[tuple[str, str]]:
    """(type, name) for every contract-scope declaration (crude but honest: declarations outside functions)."""
    stripped = _strip_comments(src)
    for fn in parse_functions(src):
        stripped = stripped.replace(fn.body, "")
    return [(m.group(1), m.group(2)) for m in _DECL.finditer(stripped)]


def state_vars(src: str) -> set[str]:
    """Contract-scope variable names."""
    return {name for _, name in _declarations(src)}


# Names that count things rather than hold them: an id, an index, a count. They only ever grow and that is
# their job, so they are not ledgers. Added after reading the seven SmartBugs confirmations of the first cut
# (three were a raffle id and a birth counter read in a condition next to a refund); marked tuned in bench/.
COUNTER = re.compile(r"(Id|ID|Ids|Count|Counter|Index|Idx|Nonce|Length|Num|Number|Seq)$")


def ledger_vars(src: str) -> set[str]:
    """State variables that can hold a balance: mappings and integers, minus configuration and counter names."""
    return {name for typ, name in _declarations(src)
            if (typ.startswith("mapping") or typ.startswith("uint") or typ.startswith("int"))
            and not PRIVILEGED.search(name) and not COUNTER.search(name)}


def _is_external(fn: Function) -> bool:
    # Before 0.5 a function with no visibility keyword was public; from 0.5 the keyword is mandatory,
    # so "not internal and not private" is callable from outside on every compiler version.
    return not re.search(r"\b(internal|private)\b", fn.header)


def _is_readonly(fn: Function) -> bool:
    return bool(re.search(r"\b(view|pure|constant)\b", fn.header))


# A function only a privileged caller can reach: the owner re-entering the owner's own function is not an
# attack. Read from the header's modifiers (onlyOwner, onlyRole(...), onlyAdmin, auth, requiresAuth ...).
# Added after the Robinhood Chain run (bench/ROBINHOOD.md): most false reentrancy confirmations were here.
# Only names that mean one privileged party. `onlyMember`, `onlyStaker`, `onlyWhitelisted` are many callers,
# any of whom can be a contract, so they stay in scope.
OWNER_ONLY = re.compile(r"\bonly(Owner|Admin|Gov\w*|Operator|Manager|Controller|Keeper|Role|Authorized|Auth\w*|Minter|"
                        r"Treasury|Dao|DAO|Guardian|Executor|Timelock|Deployer|Factory|Vault|Protocol|Multisig|Council)\w*\b"
                        r"|\b(auth|requiresAuth|onlyowner|adminOnly|ownerOnly|restricted)\b")


def _owner_only(fn: Function) -> bool:
    tail = fn.header.split(")", 1)[-1]
    return bool(OWNER_ONLY.search(tail))


def _is_constructor(fn: Function) -> bool:
    """Before 0.5 the constructor was a function with the contract's own name, callable once at deploy."""
    return bool(fn.contract) and fn.name == fn.contract


def _lines(fn: Function) -> Iterator[tuple[int, str]]:
    for off, raw in enumerate(fn.body.splitlines()):
        yield (fn.body_line or fn.start_line) + off, raw.strip().lstrip("{").strip()


# --------------------------- risk: reentrancy ---------------------------

def _helpers(fns: list[Function]) -> dict[str, Function]:
    """Internal and private functions by name, the ones an external function may run as part of itself."""
    return {f.name: f for f in fns if not _is_external(f) and f.name}


def _with_helpers(fn: Function, helpers: dict[str, Function]) -> list[Function]:
    """The function and, one level down, every helper it calls by name. The Sherwood vault paid its reward
    inside a private _claim reached from three external functions; a reader that stops at the external
    body never sees the call (bench/ROBINHOOD.md)."""
    called = [helpers[n] for n in dict.fromkeys(re.findall(r"\b([A-Za-z_]\w*)\s*\(", fn.body))
              if n in helpers and helpers[n] is not fn]
    return [fn] + called


def _storage_aliases(fn: Function, svars: set[str]) -> set[str]:
    """Local names that point into storage: `var acc = Acc[msg.sender]`, `Item storage it = items[id]`."""
    return {m.group(1) for _, text in _lines(fn) for m in [ALIAS.match(text)] if m and m.group(2) in svars}


def callorder_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: an external call happens before a state write in the same function, or in a helper it runs."""
    out, svars = [], state_vars(src)
    fns = parse_functions(src)
    helpers = _helpers(fns)
    for fn in fns:
        if _is_readonly(fn) or not _is_external(fn) or _owner_only(fn):
            continue  # a helper is read through the functions that call it, not on its own
        call_at = None
        for part in _with_helpers(fn, helpers):
            writes_storage = svars | _storage_aliases(part, svars)
            for ln, text in _lines(part):
                if call_at is None and EXTERNAL_CALL.search(text):
                    call_at = (ln, text)
                    continue
                m = STATE_WRITE.match(text) or DELETE.match(text)
                if call_at and m and m.group(1) in writes_storage:
                    out.append(Sighting("callorder-lens", "reentrancy", contract, fn.name, call_at[0], call_at[1]))
                    break
            else:
                continue
            break
    return out


# A reentrancy guard, by the name of the modifier or by the flag it sets. `modifier lock()` over a
# `_unlocked` flag is the Uniswap V2 Pair idiom and the most forked guard in Solidity; reading only
# OpenZeppelin's spelling made every fork of it look unguarded (bench/MODERN.md).
GUARD_MODIFIER = re.compile(r"^(non_?reentrant|lock|locked|mutex|no_?reentry|reentrancy_?guard|synchronized)$", re.I)
GUARD_FLAG = re.compile(r"nonReentrant|ReentrancyGuard|_?locked\b|_?unlocked\b|_?notEntered\b|_status\b")


def _guarded(parts: list[Function]) -> bool:
    if any(GUARD_MODIFIER.match(m) for p in parts for m in _modifiers(p)):
        return True
    return bool(GUARD_FLAG.search("".join(p.header + p.body for p in parts)))


def guard_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: a function (or a helper it runs) moves value out and carries no reentrancy guard."""
    out = []
    fns = parse_functions(src)
    helpers = _helpers(fns)
    for fn in fns:
        if _is_readonly(fn) or not _is_external(fn) or _owner_only(fn):
            continue
        parts = _with_helpers(fn, helpers)
        if _guarded(parts):
            continue
        for part in parts:
            hit = next(((ln, text) for ln, text in _lines(part)
                        if not text.startswith("//") and not text.startswith("*") and EXTERNAL_CALL.search(text)), None)
            if hit:
                out.append(Sighting("guard-lens", "reentrancy", contract, fn.name, hit[0], hit[1]))
                break
    return out


# ---------------------- risk: unguarded-state-write ----------------------

# Everything between the parameter list and the body that is not a modifier: visibility, mutability,
# inheritance keywords, and the return clause. `external returns (address)` is not a guard, and reading
# `address` as one hid every returning function from this lens until the contest benchmark showed it
# (bench/MODERN.md).
_NOT_A_MODIFIER = {"external", "public", "internal", "private", "payable", "pure", "view", "constant",
                   "virtual", "override", "returns", "memory", "calldata", "storage"}


def _modifiers(fn: Function) -> set[str]:
    """The modifier names a function carries, with the return clause and the keywords removed."""
    tail = fn.header.split(")", 1)[-1]
    tail = re.sub(r"\breturns\s*\([^)]*\)?", " ", tail)      # the return clause, closing brace optional
    tail = re.sub(r"\boverride\s*\([^)]*\)?", " ", tail)     # override(A, B)
    return {w for w in re.findall(r"\b[a-zA-Z_]\w*\b", tail)} - _NOT_A_MODIFIER


def modifier_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: externally callable, writes storage, carries no modifier at all."""
    out, svars = [], state_vars(src)
    fns = parse_functions(src)
    helpers = _helpers(fns)
    for fn in fns:
        if _is_readonly(fn) or not _is_external(fn) or _is_constructor(fn):
            continue
        mods = _modifiers(fn)
        if mods:
            continue
        for part in _with_helpers(fn, helpers):
            hit = next(((ln, text) for ln, text in _lines(part)
                        for m in [STATE_WRITE.match(text)] if m and m.group(1) in svars), None)
            if hit:
                out.append(Sighting("modifier-lens", "unguarded-state-write", contract, fn.name, hit[0], hit[1]))
                break
    return out


def sender_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: writes a privileged-looking variable with no msg.sender check anywhere."""
    out, svars = [], state_vars(src)
    fns = parse_functions(src)
    helpers = _helpers(fns)
    for fn in fns:
        if _is_readonly(fn) or not _is_external(fn) or _is_constructor(fn):
            continue
        parts = _with_helpers(fn, helpers)
        if re.search(r"msg\.sender|_checkOwner|onlyOwner|hasRole|_msgSender",
                     "".join(p.body + p.header for p in parts)):
            continue
        for part in parts:
            hit = next(((ln, text) for ln, text in _lines(part)
                        for m in [STATE_WRITE.match(text)]
                        if m and m.group(1) in svars and PRIVILEGED.search(m.group(1))), None)
            if hit:
                out.append(Sighting("sender-lens", "unguarded-state-write", contract, fn.name, hit[0], hit[1]))
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
BOUND = re.compile(r"\b(require|assert|if)\s*\(.*(<=|>=|<|>|==)")
# Operands a 256-bit number cannot be wrapped by: what the chain itself bounds, and small constants.
CHAIN_BOUNDED = re.compile(r"\bmsg\.(value|sender)\b|\bblock\.(number|timestamp)\b|\bnow\b|\.length\b|\btx\.\w+")
UNITS = {"wei", "gwei", "ether", "seconds", "minutes", "hours", "days", "weeks", "uint", "int"}


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
        m = ARITH.match(re.sub(r"^unchecked\s*\{\s*", "", text))  # `unchecked { x += y; }` on one line
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
            free = CHAIN_BOUNDED.sub("", rhs)
            rhs_names = set(re.findall(r"[A-Za-z_]\w*", free)) - {target} - UNITS - set(re.findall(r"\b(?:uint|int)\d*\b", free))
            if not rhs_names:
                continue  # `+= msg.value`, `+= 1`, `= now + 1 weeks`: nothing here can wrap a uint256
            operands = {target} | rhs_names
            before = [t for l, t in _lines(fn) if l < ln]
            guarded = any(BOUND.search(t) and any(re.search(rf"\b{re.escape(o)}\b", t) for o in operands) for t in before)
            guarded = guarded or bool(re.search(r"(<=|>=|<|>)[^?;]*\?", rhs))  # `a >= b ? 0 : b - a` bounds itself
            if not guarded:
                out.append(Sighting("bound-lens", "unsafe-math", contract, fn.name, ln, text))
                break
    return out


# ------------------------ risk: accounting-mismatch ------------------------
#
# One bug, two readings. The bug is a balance that only ever goes up while value goes out against it:
# "a contract that adds to a balance in one function and never takes it back in another". ledger-lens
# reads the whole contract: is there any way down for this variable? payout-lens reads one function:
# does value leave here against a balance this function never reduces? A monotonic counter read by a
# setter is a candidate; a payout against a balance the contract lowers elsewhere is a candidate; only
# both together confirm. Not this shape, and invisible to a line reader: a sibling function that forgot
# one debit another function has (the variable does go down somewhere, on the other path).

OUTFLOW = re.compile(EXTERNAL_CALL.pattern + r"|\.(transfer|send|safeTransfer|safeTransferFrom|transferFrom)\s*\(")
# A write anywhere on the line, not only at its start: `unchecked { staked[msg.sender] -= amount; }` and
# `if (ok) total -= x;` are writes too. Before the Robinhood Chain run they were invisible, which made a
# balance that is lowered on one such line look one-way (bench/ROBINHOOD.md).
WRITE = re.compile(r"(?<![\w.])(delete\s+)?([A-Za-z_]\w*)\s*((?:\[[^\]]*\]|\.\w+)*)\s*(\+\+|--|\+=|-=|\*=|/=|(?<![=!<>])=(?!=))"
                   r"|(?<![\w.])(\+\+|--)\s*([A-Za-z_]\w*)")


def _writes_of(fn: Function, svars: set[str] | None = None) -> Iterator[tuple[int, str, str, bool]]:
    """(line, text, variable, is_credit) for every write to a named variable in this function.
    A write through a storage alias (`Item storage it = items[id]; it.amount -= x`) is a write to items."""
    alias: dict[str, str] = {}
    for ln, text in _lines(fn):
        if text.startswith("//") or text.startswith("*"):
            continue
        a = ALIAS.match(text)
        if a and (svars is None or a.group(2) in svars):
            alias[a.group(1)] = a.group(2)
        for m in WRITE.finditer(text):
            if m.group(5):
                yield ln, text, alias.get(m.group(6), m.group(6)), m.group(5) == "++"
                continue
            name, member, op = m.group(2), m.group(3), m.group(4)
            credit = op in ("++", "+=") or (op == "=" and not m.group(1) and bool(
                re.match(rf"\s*{re.escape(name)}\s*{re.escape(member or '')}\s*\+", text[m.end():])))
            yield ln, text, alias.get(name, name), credit and not m.group(1)


def _reads(fn: Function, names: set[str]) -> Iterator[tuple[int, str, str]]:
    """(line, text, variable) for every line that mentions a variable without writing it."""
    for ln, text in _lines(fn):
        if text.startswith("//") or text.startswith("*"):
            continue
        written = {(m.group(2) or m.group(6)) for m in WRITE.finditer(text)}
        for v in names:
            if v not in written and re.search(rf"\b{re.escape(v)}\b", text):
                yield ln, text, v
                break


def one_way_ledgers(src: str) -> set[str]:
    """Ledger variables written somewhere in the contract whose every write, anywhere, is a credit."""
    written: dict[str, bool] = {}
    svars = state_vars(src)
    for fn in parse_functions(src):
        for _, _, name, credit in _writes_of(fn, svars):
            written[name] = written.get(name, True) and credit
    return {v for v in ledger_vars(src) if written.get(v)}


def ledger_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: the balance this function relies on has no way down anywhere in the contract."""
    out, one_way, svars = [], one_way_ledgers(src), state_vars(src)
    if not one_way:
        return out
    for fn in parse_functions(src):
        if _is_readonly(fn) or not _is_external(fn) or _is_constructor(fn):
            continue
        touched = {name for _, _, name, _ in _writes_of(fn, svars)}
        for ln, text, v in _reads(fn, one_way - touched):
            out.append(Sighting("ledger-lens", "accounting-mismatch", contract, fn.name, ln, text))
            break
    return out


def payout_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: value leaves this function against a balance it reads and never reduces."""
    out, ledgers = [], ledger_vars(src)
    for fn in parse_functions(src):
        if _is_readonly(fn) or not _is_external(fn) or _is_constructor(fn):
            continue
        outflow = next(((ln, text) for ln, text in _lines(fn)
                        if not text.startswith("//") and not text.startswith("*") and OUTFLOW.search(text)), None)
        if not outflow:
            continue
        written = {name for _, _, name, _ in _writes_of(fn, ledgers)}
        read = {v for _, _, v in _reads(fn, ledgers)}
        if read and not (read & written):
            out.append(Sighting("payout-lens", "accounting-mismatch", contract, fn.name, outflow[0], outflow[1]))
    return out


LENSES = {
    "callorder-lens": callorder_lens,
    "guard-lens": guard_lens,
    "modifier-lens": modifier_lens,
    "sender-lens": sender_lens,
    "wrap-lens": wrap_lens,
    "bound-lens": bound_lens,
    "ledger-lens": ledger_lens,
    "payout-lens": payout_lens,
}

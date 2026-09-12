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

def unchecked_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: arithmetic inside an unchecked block."""
    out = []
    for fn in parse_functions(src):
        depth, inside = 0, False
        for ln, text in _lines(fn):
            if "unchecked" in text:
                inside, depth = True, 0
            if inside:
                depth += text.count("{") - text.count("}")
                if re.search(r"[+\-*]=|[^/+\-*]\s[+\-*]\s", text) and "unchecked" not in text:
                    out.append(Sighting("unchecked-lens", "unsafe-math", contract, fn.name, ln, text))
                    break
                if depth <= 0 and "{" in fn.body:
                    inside = False
    return out


def precision_lens(contract: str, src: str) -> list[Sighting]:
    """Evidence: a division evaluated before a multiplication in the same expression."""
    out = []
    for fn in parse_functions(src):
        for ln, text in _lines(fn):
            if text.startswith("//") or text.startswith("*"):
                continue
            if re.search(r"/\s*[\w.()\[\]]+\s*\*", text):
                out.append(Sighting("precision-lens", "unsafe-math", contract, fn.name, ln, text))
                break
    return out


LENSES = {
    "callorder-lens": callorder_lens,
    "guard-lens": guard_lens,
    "modifier-lens": modifier_lens,
    "sender-lens": sender_lens,
    "unchecked-lens": unchecked_lens,
    "precision-lens": precision_lens,
}

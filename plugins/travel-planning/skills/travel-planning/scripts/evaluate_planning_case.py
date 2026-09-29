#!/usr/bin/env python3
"""Evaluate explicit local synthetic planning cases; never contact providers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
import sys
from decimal import Decimal, DecimalException, localcontext
from pathlib import Path


MAX_BYTES = 262144
ID = re.compile(r"[a-z][a-z0-9-]{0,79}\Z")
UNITS = {"boolean", "text", "minutes", "count", "nights", "AUD", "EUR", "USD"}


class InputError(ValueError):
    """Invalid evaluation input; details deliberately stay out of diagnostics."""


def require(condition):
    if not condition:
        raise InputError("Invalid evaluation input")


def fields(value, names):
    require(isinstance(value, dict) and set(value) == set(names.split()))


def identifier(value):
    require(isinstance(value, str) and ID.fullmatch(value) is not None)
    return value


def number(value):
    require(type(value) in (int, float) and abs(value) <= 10**12 and math.isfinite(value))
    return bounded_decimal(Decimal(str(value)))


def bounded_decimal(value):
    require(value.is_finite() and value.copy_abs() <= 10**12)
    digits = list(value.as_tuple().digits)
    exponent = value.as_tuple().exponent
    if value:
        while digits[-1] == 0:
            digits.pop()
            exponent += 1
        require(exponent >= -6 and len(digits) <= 15)
    return value


def parse_float(token):
    # Reject precision loss before converting to a JSON-serializable Python value.
    require(len(token) <= 64)
    exact = bounded_decimal(Decimal(token))
    value = float(exact)
    require(Decimal(str(value)) == exact)
    return value


def sequence(value, maximum=100, minimum=0):
    require(isinstance(value, list) and minimum <= len(value) <= maximum)
    return value


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def tree_bound(value, depth=0):
    require(depth <= 24)
    if isinstance(value, dict):
        require(len(value) <= 100)
        for key, item in value.items():
            tree_bound(key, depth + 1)
            tree_bound(item, depth + 1)
    elif isinstance(value, list):
        sequence(value)
        for item in value:
            tree_bound(item, depth + 1)
    elif isinstance(value, str):
        require(len(value) <= 12000 and not any(0xD800 <= ord(c) <= 0xDFFF for c in value))
    elif type(value) in (int, float):
        number(value)
    else:
        require(value is None or type(value) is bool)


def load(path):
    """Read one explicit regular file with bounded size and strict JSON syntax."""
    try:
        require(stat.S_ISREG(path.lstat().st_mode))
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_float=parse_float,
                           parse_constant=lambda _: require(False))
        tree_bound(value)
        return value, hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, ValueError, RecursionError, OverflowError, DecimalException):
        raise InputError("Invalid evaluation input") from None


def expression(expr, facts, depth=0):
    """Return (Decimal or unknown, unit); the grammar contains no executable code."""
    require(depth <= 8 and isinstance(expr, dict))
    if set(expr) == {"fact"}:
        key = identifier(expr["fact"])
        require(key in facts)
        fact = facts[key]
        require(fact["unit"] not in {"boolean", "text"})
        return (number(fact["value"]) if fact["status"] == "verified" else None, fact["unit"])
    if expr.get("op") == "scale":
        fields(expr, "op factor arg")
        factor = number(expr["factor"])
        require(factor.copy_abs() <= 1000)
        value, unit = expression(expr["arg"], facts, depth + 1)
        with localcontext() as context:
            context.prec = 50
            result = None if value is None else value * factor
    else:
        fields(expr, "op args")
        require(expr["op"] in ("sum", "min", "max"))
        items = [expression(arg, facts, depth + 1) for arg in sequence(expr["args"], 20, 1)]
        unit = items[0][1]
        require(all(item[1] == unit for item in items))
        values = [item[0] for item in items]
        with localcontext() as context:
            context.prec = 50
            result = None if None in values else {"sum": sum, "min": min, "max": max}[expr["op"]](values)
    if result is not None:
        bounded_decimal(result)
    return result, unit


def condition(test, facts):
    require(isinstance(test, dict))
    if set(test) == {"fact", "equals"}:
        key = identifier(test["fact"])
        require(key in facts)
        fact = facts[key]
        require(fact["unit"] in {"boolean", "text"})
        expected = test["equals"]
        require(type(expected) is (bool if fact["unit"] == "boolean" else str))
        return fact["status"] == "verified" and fact["value"] == expected
    fields(test, "left op right")
    require(test["op"] in ("le", "ge", "eq"))
    left, unit = expression(test["left"], facts)
    right, other = expression(test["right"], facts)
    require(unit == other)
    if left is None or right is None:
        return False
    return {"le": left <= right, "ge": left >= right, "eq": left == right}[test["op"]]


def validate_case(case):
    tree_bound(case)
    fields(case, "schema id prompt facts rules examples")
    require(case["schema"] == "planning-case/v1")
    identifier(case["id"])
    require(isinstance(case["prompt"], str) and bool(case["prompt"].strip()))
    facts = case["facts"]
    require(isinstance(facts, dict) and 1 <= len(facts) <= 100)
    for key, fact in facts.items():
        identifier(key)
        fields(fact, "description value unit status")
        require(isinstance(fact["description"], str) and bool(fact["description"].strip()))
        require(isinstance(fact["unit"], str) and fact["unit"] in UNITS)
        require(fact["status"] in ("verified", "unknown"))
        if fact["status"] == "unknown":
            require(fact["value"] is None)
        elif fact["unit"] == "boolean":
            require(type(fact["value"]) is bool)
        elif fact["unit"] == "text":
            require(isinstance(fact["value"], str))
        else:
            number(fact["value"])
    ids = set()
    for rule in sequence(case["rules"], 40, 1):
        require(isinstance(rule, dict))
        key = identifier(rule.get("id"))
        require(key not in ids)
        ids.add(key)
        kind = rule.get("kind")
        if kind == "quantity":
            fields(rule, "id kind expression")
            expression(rule["expression"], facts)
        elif kind == "pending":
            fields(rule, "id kind facts")
            keys = sequence(rule["facts"], 100, 1)
            require(all(isinstance(k, str) and k in facts for k in keys) and len(set(keys)) == len(keys))
        elif kind == "choice":
            fields(rule, "id kind options minimum maximum policy")
            require(type(rule["minimum"]) is int and type(rule["maximum"]) is int)
            require(1 <= rule["minimum"] <= rule["maximum"] <= 20)
            require(rule["policy"] in ("feasible", "cheapest"))
            require(rule["policy"] != "cheapest" or rule["minimum"] == rule["maximum"] == 1)
            options = set()
            units = set()
            for option in sequence(rule["options"], 20, 1):
                fields(option, "id requires cost" if rule["policy"] == "cheapest" else "id requires")
                name = identifier(option["id"])
                require(name not in options)
                options.add(name)
                for test in sequence(option["requires"], 20):
                    condition(test, facts)
                if rule["policy"] == "cheapest":
                    value, unit = expression(option["cost"], facts)
                    require(unit in {"AUD", "EUR", "USD"} and (value is None or value >= 0))
                    units.add(unit)
            require(len(units) <= 1)
        else:
            raise InputError("Invalid evaluation input")
    example_ids = set()
    for example in sequence(case["examples"], 30):
        fields(example, "id answers expect")
        key = identifier(example["id"])
        require(key not in example_ids)
        example_ids.add(key)
        require(isinstance(example["answers"], dict) and example["expect"] in ("pass", "fail"))
    return case


def validate_candidate(candidate, case, digest):
    tree_bound(candidate)
    fields(candidate, "schema case_id case_sha256 answers")
    require(candidate["schema"] == "planning-answer/v1" and candidate["case_id"] == case["id"])
    require(candidate["case_sha256"] == digest)
    answers = candidate["answers"]
    require(isinstance(answers, dict) and set(answers) == {rule["id"] for rule in case["rules"]})
    for rule in case["rules"]:
        answer = answers[rule["id"]]
        if rule["kind"] == "quantity":
            fields(answer, "value unit")
            require(isinstance(answer["unit"], str) and answer["unit"] in UNITS)
            if answer["value"] is not None:
                number(answer["value"])
        else:
            sequence(answer, 100)
            require(all(isinstance(item, str) for item in answer) and len(set(answer)) == len(answer))
            allowed = set(case["facts"]) if rule["kind"] == "pending" else {o["id"] for o in rule["options"]}
            require(set(answer) <= allowed)
    return answers


def evaluate(case, candidate, digest):
    """Check decision fields only. This does not validate a production itinerary."""
    validate_case(case)
    answers = validate_candidate(candidate, case, digest)
    facts = case["facts"]
    checks = []
    for rule in case["rules"]:
        answer = answers[rule["id"]]
        if rule["kind"] == "quantity":
            value, unit = expression(rule["expression"], facts)
            actual = None if answer["value"] is None else number(answer["value"])
            passed = actual == value and answer["unit"] == unit
        elif rule["kind"] == "pending":
            passed = set(answer) == {key for key in rule["facts"] if facts[key]["status"] == "unknown"}
        else:
            eligible = {}
            unknown_cost = False
            for option in rule["options"]:
                if all(condition(test, facts) for test in option["requires"]):
                    value = None
                    if rule["policy"] == "cheapest":
                        value, _ = expression(option["cost"], facts)
                        unknown_cost |= value is None
                    eligible[option["id"]] = value
            if len(eligible) < rule["minimum"] or unknown_cost:
                passed = not answer  # Explicitly defer an unsupported choice/comparison.
            else:
                passed = rule["minimum"] <= len(answer) <= rule["maximum"] and set(answer) <= set(eligible)
                if passed and rule["policy"] == "cheapest":
                    passed = eligible[answer[0]] == min(eligible.values())
        checks.append({"id": rule["id"], "result": "pass" if passed else "fail"})
    return {"result": "pass" if all(c["result"] == "pass" for c in checks) else "fail",
            "case_sha256": digest, "scope": "synthetic_decision_fields", "checks": checks}


def public_case(case, digest):
    answer_fields = []
    for rule in case["rules"]:
        field = {"id": rule["id"]}
        if rule["kind"] == "quantity":
            field.update(type="quantity", unit=expression(rule["expression"], case["facts"])[1],
                         unknown_value=None)
        elif rule["kind"] == "pending":
            field.update(type="id_array", allowed_ids=rule["facts"], meaning="unknown_facts_in_this_scope")
        else:
            field.update(type="id_array", allowed_ids=[option["id"] for option in rule["options"]],
                         minimum=rule["minimum"], maximum=rule["maximum"], policy=rule["policy"],
                         deferral_value=[])
        answer_fields.append(field)
    return {"schema": "planning-prompt/v1", "case_id": case["id"], "case_sha256": digest,
            "prompt": case["prompt"], "facts": case["facts"],
            "answer_fields": answer_fields}


class BoundedParser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError("Invalid command arguments")


def main(argv=None):
    parser = BoundedParser(description=__doc__)
    parser.add_argument("--case", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--candidate", type=Path)
    mode.add_argument("--show-case", action="store_true")
    try:
        args = parser.parse_args(argv)
    except InputError:
        print('{"result":"invalid_arguments"}')
        return 2
    try:
        case, digest = load(args.case)
        validate_case(case)
    except (InputError, RecursionError):
        print('{"result":"invalid_case"}')
        return 2
    if args.show_case:
        print(json.dumps(public_case(case, digest), ensure_ascii=True, indent=2))
        return 0
    try:
        candidate, candidate_digest = load(args.candidate)
        report = evaluate(case, candidate, digest)
    except (InputError, RecursionError):
        print('{"result":"invalid_candidate"}')
        return 2
    report["candidate_sha256"] = candidate_digest
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

import itertools
import math

from besser.BUML.metamodel.quantum import ControlState

from transformations.model_io import attr, many, objects_of, one
from transformations.t2_solution_quantum import Layout, build_oracle, expression, holds, is_atom, operator, q3_atom


def baseline(problem_model):
    # Brute force straight on the problem model, independent of T1/T2.
    # (Subset sum is weakly NP-complete: dynamic programming over the amount
    # solves these instances in O(n * amount), so a classical solver always wins here.)
    payment = objects_of(problem_model, "Payment")[0]
    pieces = many(one(payment, "paidFrom"), "pieces")
    limit = attr(payment, "maxPieces")
    found = []
    for r in range(len(pieces) + 1):
        if limit is not None and r > limit:
            break
        for combo in itertools.combinations(pieces, r):
            if sum(p.value for p in combo) == payment.amount:
                found.append(sorted(p.label for p in combo))
    return sorted(found)


def success_theory(n_search, m, rounds):
    if m == 0:
        return 0.0
    theta = math.asin(math.sqrt(m / 2 ** n_search))
    return math.sin((2 * rounds + 1) * theta) ** 2


def run_reversible(ops, state):
    # X gates with (anti-)controls only permute basis states
    for op in ops:
        if all(state[q] == (s == ControlState.CONTROL) for q, s in zip(op.control_qubits, op.control_states)):
            state[op.target_qubits[0]] ^= 1
    return state


def basis_inputs(system, size):
    variables = many(system, "variables")
    for combo in itertools.product(*[range(2 ** v.bitWidth) for v in variables]):
        state, pos = [0] * size, 0
        for var, value in zip(variables, combo):
            for j in range(var.bitWidth):
                state[pos] = (value >> j) & 1
                pos += 1
        yield {v.name_: x for v, x in zip(variables, combo)}, state


def check_arithmetic(system):
    """Annex A, class C: every arithmetic block computes a0 + sum(a_i*y_i) on every basis input."""
    root = one(system, "rootConstraint")
    for atom in [root] if is_atom(root) else many(root, "operands"):
        layout = Layout()
        qubits_of = {v: layout.take(v.bitWidth) for v in many(system, "variables")}
        n = layout.size
        ops, flag = q3_atom(atom, layout, qubits_of)
        is_eq = operator(atom) == "EQ"
        register = list(range(n, layout.size - is_eq))  # "=" adds a flag after the register
        for values, state in basis_inputs(system, layout.size):
            state = run_reversible(ops, state)
            e = expression(atom, values)
            got = sum(state[q] << i for i, q in enumerate(register))
            assert got == (e if is_eq else e - 1) % 2 ** len(register), f"{atom.name_}: wrong sum"
            assert state[flag] == (e == 0 if is_eq else e <= 0), f"{atom.name_}: wrong flag"


def check_oracle(system):
    """The oracle flips the phase qubit iff the constraints hold, and leaves every ancilla clean."""
    oracle, layout, _, _, phase = build_oracle(system)
    for values, before in basis_inputs(system, layout.size):
        after = run_reversible(oracle, list(before))
        assert after[phase] == int(holds(one(system, "rootConstraint"), values)), "oracle marks a wrong state"
        assert after[:phase] == before[:phase] and not any(after[phase + 1:]), "dirty ancilla"

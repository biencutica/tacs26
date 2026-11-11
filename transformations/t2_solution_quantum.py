"""T2 (M2M): linear integer constraint model + solver config -> BESSER quantum circuit (Grover).

Rules:
  Q1 ConstraintSystem       -> QuantumCircuit, register q (variables, phase qubit, ancillas), register c
  Q2 IntegerVariable        -> one qubit per bit: H at the start, Measurement into c at the end
  Q3 AtomicConstraint       -> ancilla register computing a0 + sum(a_i * y_i), and a flag qubit
  Q4 root constraint        -> mark: flip the phase qubit when the formula holds (AND / OR of flags)
  Q5 each round             -> diffuser on the variable qubits
  Q6 SolverConfig           -> number of rounds, from iterations or expectedSolutions

Only X/H/Z gates with (anti-)controls are used, so the oracle is a permutation of
basis states and every arithmetic block can be tested exhaustively.
The trace maps every classical bit back to (IntegerVariable, bit index).
"""

import math

from besser.BUML.metamodel.quantum import (
    ClassicalRegister, ControlState, HadamardGate, Measurement, PauliXGate, PauliZGate, QuantumCircuit)

from transformations.model_io import attr, literal, many, objects_of, one

ON, OFF = ControlState.CONTROL, ControlState.ANTI_CONTROL


def system_of(solution_model):
    systems = objects_of(solution_model, "ConstraintSystem")
    assert len(systems) == 1, "T2 expects exactly one ConstraintSystem"
    return systems[0]


def variables_of(system):
    return many(system, "variables")


def is_atom(node):
    return node.classifier.name == "AtomicConstraint"


def operator(node):
    return literal(node.operator)


def constant(atom):
    return one(atom, "expression").constant


def terms(atom):
    return many(one(atom, "expression"), "terms")


def operands(node):
    return many(node, "operands")


class Layout:
    """Hands out qubit indices; the generator needs one register named q."""

    def __init__(self):
        self.size = 0

    def take(self, n):
        qubits = list(range(self.size, self.size + n))
        self.size += n
        return qubits


def x(target, controls=(), states=None):
    controls = list(controls)
    return PauliXGate(target_qubit=target, control_qubits=controls or None,
                      control_states=states or ([ON] * len(controls)) or None)


def register_width(atom, offset):
    # Annex A, class C, "Quantum implementation notes": smallest two's complement
    # width B covering the minimum and maximum of a0 + sum(a_i * y_i) (+ offset)
    low = high = constant(atom) + offset
    for t in terms(atom):
        top = t.coefficient * (2 ** one(t, "variable").bitWidth - 1)
        low += min(0, top)
        high += max(0, top)
    bits = 1
    while not (-2 ** (bits - 1) <= low and high <= 2 ** (bits - 1) - 1):
        bits += 1
    return bits


def controlled_add_constant(k, register, control):
    # Adds k (mod 2^B) to the register when control is |1>. Each set bit b of k is an
    # increment of register[b:], a cascade of multi-controlled X gates from the top
    # bit down (Vedral, Barenco, Ekert 1996; Barenco et al. 1995).
    ops = []
    width = len(register)
    k %= 2 ** width
    for b in range(width):
        if (k >> b) & 1:
            for t in range(width - 1, b - 1, -1):
                ops.append(x(register[t], [control] + register[b:t]))
    return ops


def q3_atom(atom, layout, qubits_of):
    """Returns (ops, flag): flag is |1> iff the atom holds."""
    # e <= 0  <=>  e - 1 < 0  <=>  the sign bit of e - 1 is 1, so for <= the
    # register holds e - 1 and its top bit is the flag (two's complement)
    offset = -1 if operator(atom) == "LE" else 0
    register = layout.take(register_width(atom, offset))

    start = (constant(atom) + offset) % 2 ** len(register)
    ops = [x(register[b]) for b in range(len(register)) if (start >> b) & 1]
    for t in terms(atom):
        var = one(t, "variable")
        for j in range(var.bitWidth):
            ops += controlled_add_constant(t.coefficient * 2 ** j, register, qubits_of[var][j])

    if operator(atom) == "LE":
        return ops, register[-1]

    # e = 0  <=>  every bit is 0: one X anti-controlled by the whole register
    flag = layout.take(1)[0]
    ops.append(x(flag, register, [OFF] * len(register)))
    return ops, flag


def combine(connective, flags, target):
    if connective == "AND":
        return [x(target, flags)]
    # OR is the negation of the all-zero check (De Morgan).
    return [x(target, flags, [OFF] * len(flags)), x(target)]


def compute(node, layout, qubits_of):
    """Computes a constraint into a flag qubit; nested logical constraints get an ancilla."""
    if is_atom(node):
        return q3_atom(node, layout, qubits_of)
    ops, flags = compute_operands(node, layout, qubits_of)
    flag = layout.take(1)[0]
    return ops + combine(operator(node), flags, flag), flag


def compute_operands(node, layout, qubits_of):
    ops, flags = [], []
    for child in operands(node):
        child_ops, flag = compute(child, layout, qubits_of)
        ops += child_ops
        flags.append(flag)
    return ops, flags


def q4_oracle(system, layout, qubits_of, phase):
    # compute - mark - uncompute (Annex A, class C); every gate is self-inverse,
    # so uncompute is the compute sequence in mirror order
    root = one(system, "rootConstraint")
    if is_atom(root):
        ops, flag = q3_atom(root, layout, qubits_of)
        return ops + [x(phase, [flag])] + ops[::-1]
    ops, flags = compute_operands(root, layout, qubits_of)
    return ops + combine(operator(root), flags, phase) + ops[::-1]


def q5_diffuser(search):
    # 2|s><s| - I up to a global phase (Grover 1996; Nielsen & Chuang, ch. 6)
    ops = [HadamardGate(target_qubit=q) for q in search]
    ops += [x(q) for q in search]
    ops.append(PauliZGate(target_qubit=search[-1], control_qubits=search[:-1] or None))
    ops += [x(q) for q in search]
    ops += [HadamardGate(target_qubit=q) for q in search]
    return ops


def q6_rounds(config, n_search):
    if attr(config, "iterations") is not None:
        return config.iterations
    m = config.expectedSolutions
    if m == 0:
        return 0
    # k = floor(pi / (4 theta)), sin^2(theta) = M / N (Boyer, Brassard, Hoyer, Tapp 1998)
    theta = math.asin(math.sqrt(m / 2 ** n_search))
    return math.floor(math.pi / (4 * theta))


def build_oracle(system):
    """Q1/Q2 layout and the Q3/Q4 oracle; returns (ops, layout, qubits_of, search, phase)."""
    layout = Layout()
    qubits_of = {var: layout.take(var.bitWidth) for var in variables_of(system)}
    search = [q for var in variables_of(system) for q in qubits_of[var]]
    phase = layout.take(1)[0]
    return q4_oracle(system, layout, qubits_of, phase), layout, qubits_of, search, phase


def transform(solution_model, config, trace):
    system = system_of(solution_model)
    oracle, layout, qubits_of, search, phase = build_oracle(system)
    rounds = q6_rounds(config, len(search))

    circuit = QuantumCircuit(name=system.name_, qubits=layout.size)
    circuit.add_creg(ClassicalRegister("c", len(search)))

    # The phase qubit in |-> turns a controlled X into a phase flip.
    ops = [HadamardGate(target_qubit=q) for q in search]
    ops += [x(phase), HadamardGate(target_qubit=phase)]
    for _ in range(rounds):
        ops += oracle + q5_diffuser(search)
    ops += [Measurement(target_qubit=q, output_bit=i) for i, q in enumerate(search)]
    for op in ops:
        circuit.add_operation(op)

    trace["rounds"] = rounds
    trace["clbits"] = {search.index(q): (var, j) for var in variables_of(system)
                       for j, q in enumerate(qubits_of[var])}
    return circuit


def expression(atom, values):
    return constant(atom) + sum(t.coefficient * values[one(t, "variable").name_] for t in terms(atom))


def holds(node, values):
    """Meaning of the solution DSL; values maps IntegerVariable object names to integers."""
    if is_atom(node):
        e = expression(node, values)
        return e == 0 if operator(node) == "EQ" else e <= 0
    results = [holds(child, values) for child in operands(node)]
    return all(results) if operator(node) == "AND" else any(results)


def decode(bitstring, trace):
    """Values of the variables, read through T2's trace of classical bits."""
    bits = bitstring[::-1]  # Qiskit bitstrings are little-endian: the rightmost character is c[0]
    values = {}
    for clbit, (var, j) in trace["clbits"].items():
        values[var.name_] = values.get(var.name_, 0) | int(bits[clbit]) << j
    return values

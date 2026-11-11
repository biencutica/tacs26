"""The whole chain, for each instance file in instances/:
problem model -> T1 -> solution model -> T2 -> quantum model -> T3 (BESSER generator)
-> Qiskit on Aer -> results in domain terms, compared with the classical baseline

Usage:  python pipeline.py (all instances)
        python pipeline.py tiny many (some instances)
"""

import contextlib
import os
import runpy
import sys

from besser.generators.qiskit import QiskitGenerator

from transformations import t1_problem_solution as t1, t2_solution_quantum as t2
from transformations.model_io import attr, load, many, objects_of, one
from validation import baseline, check_arithmetic, check_oracle, success_theory

ROOT = os.path.dirname(os.path.abspath(__file__))
INSTANCES = os.path.join(ROOT, "instances")
CONFIG = os.path.join(ROOT, "config", "default.py")
OUTPUT = os.path.join(ROOT, "output")

def run(name):
    problem = load(os.path.join(INSTANCES, name + ".py"))["object_model"]

    # solver choices are inputs: M comes from the classical baseline unless rounds are fixed
    config = load(CONFIG)["solver_config"]
    expected = baseline(problem)
    
    if attr(config, "iterations") is None:
        config.expectedSolutions = len(expected)

    t1_trace, t2_trace = {}, {}
    solution = t1.transform(problem, t1_trace)
    circuit = t2.transform(solution, config, t2_trace)
    system = t2.system_of(solution)
    check_arithmetic(system)
    check_oracle(system)

    # T3, and the generated script is run untouched 
    folder = os.path.join(OUTPUT, name)
    with open(os.devnull, "w", encoding="utf-8") as quiet, contextlib.redirect_stdout(quiet):
        QiskitGenerator(circuit, output_dir=folder, shots=config.shots).generate()
        counts = runpy.run_path(os.path.join(folder, "qiskit_circuit.py"))["counts"]

    # decode each measured bitstring and keep the ones that satisfy the constraints
    label = {var.name_: piece.label for var, piece in t1_trace.items()}
    found = {}
    
    for bitstring, shots in counts.items():
        values = t2.decode(bitstring, t2_trace)
        if t2.holds(one(system, "rootConstraint"), values):
            used = tuple(sorted(label[v] for v, x in values.items() if x == 1))
            found[used] = found.get(used, 0) + shots

    payment = objects_of(problem, "Payment")[0]
    limit = attr(payment, "maxPieces")
    n_search = circuit.cregs[0].size

    print(f"\n== {name}: {one(payment, 'paidFrom').owner} pays {payment.amount}"
          + (f" with at most {limit} pieces" if limit else ""))
    print(f"   {circuit.num_qubits} qubits, {2 ** n_search} choices, {t2_trace['rounds']} Grover rounds")
    
    for used, shots in sorted(found.items(), key=lambda kv: -kv[1]):
        print(f"   {shots:4d} shots: pay with {' + '.join(used)}")
    
    if not found:
        print("   no valid payment measured: the amount cannot be paid")
    
    print(f"   classical baseline: {expected or 'no solution'}")

    return dict(name=name, qubits=circuit.num_qubits, n=n_search, m=len(expected),
                rounds=t2_trace["rounds"], p_valid=sum(found.values()) / config.shots,
                p_theory=success_theory(n_search, len(expected), t2_trace["rounds"]),
                agrees=sorted(list(u) for u in found) == expected)


def write_summary(rows):
    lines = ["| instance | qubits | N | M (baseline) | Grover rounds = oracle calls "
             "| P(valid) measured | P(valid) theory | agrees with baseline |",
             "|---|---|---|---|---|---|---|---|"]
    
    for r in rows:
        lines.append(f"| {r['name']} | {r['qubits']} | {2 ** r['n']} | {r['m']} | {r['rounds']} "
                     f"| {r['p_valid']:.3f} | {r['p_theory']:.3f} | {'yes' if r['agrees'] else 'NO'} |")
    
    with open(os.path.join(OUTPUT, "validation.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(f[:-3] for f in os.listdir(INSTANCES) if f.endswith(".py"))
    write_summary([run(name) for name in names])
    
    print("\nGenerated code in output/<instance>/, summary in output/validation.md")

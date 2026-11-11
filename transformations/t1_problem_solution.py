"""T1 (M2M): exact payment problem model -> linear integer constraint model

Rules, for one Payment of the problem model:
  R1 Payment -> ConstraintSystem
  R2 Piece of its wallet -> IntegerVariable of 1 bit, "piece is used"
  R3 Payment.amount -> AtomicConstraint  sum(value_i * y_i) - amount = 0
  R4 Payment.maxPieces -> AtomicConstraint  sum(y_i) - maxPieces <= 0
  R5 two or more atoms -> LogicalConstraint AND, as the root constraint

The trace maps every IntegerVariable back to its Piece, to report results in domain terms.
"""

from besser.BUML.metamodel.object import ObjectModel

import metamodels.solution_dsl as S
from transformations.model_io import attr, enum_literal, many, new, objects_of, one


def r1_payment_to_system(payment, target):
    system = new(S.ConstraintSystem, f"{payment.name_}_system", name=payment.name_)
    target.add_object(system)
    
    return system


def r2_piece_to_variable(piece, target, trace):
    # subset-sum ex: one bit per item (1 = chosen)
    # named after the piece object, not its label: BESSER builds link names from
    # the "name" attribute, and labels such as "2 euro cent coin" contain spaces
    var = new(S.IntegerVariable, f"var_{piece.name_}", name=piece.name_, bitWidth=1)
    target.add_object(var)
    trace[var] = piece
    
    return var


def r3_amount_to_exact(payment, variables, trace, target):
    # ex: 2y1 + 3y2 + 5y3 + 7y4 - 15 = 0
    terms = [(trace[v].value, v) for v in variables]
    return _atom(f"{payment.name_}_exact", "EQ", -payment.amount, terms, target)


def r4_max_pieces_to_limit(payment, variables, target):
    # a bound y1 + ... + yn <= k becomes y1 + ... + yn - k <= 0
    terms = [(1, v) for v in variables]
    return _atom(f"{payment.name_}_limit", "LE", -payment.maxPieces, terms, target)


def r5_conjunction(payment, atoms, target):
    # atoms are combined with "and"
    root = new(S.LogicalConstraint, f"{payment.name_}_all",
               operator=enum_literal(S.LogicalOperator, "AND"))
    root.operands = set(atoms)
    target.add_object(root)
    return root


def _atom(name, operator, constant, terms, target):
    expression = new(S.LinearExpression, f"{name}_expr", constant=constant)
    target.add_object(expression)
    linear_terms = []
    
    for coefficient, var in terms:
        term = new(S.LinearTerm, f"{name}_{var.name_}", coefficient=coefficient)
        term.variable = var
        target.add_object(term)
        linear_terms.append(term)
    
    expression.terms = set(linear_terms)
    atom = new(S.AtomicConstraint, name, operator=enum_literal(S.ComparisonOperator, operator))
    atom.expression = expression
    target.add_object(atom)
    
    return atom


def transform(source, trace):
    target = ObjectModel(name=f"{source.name}_solution")
    
    for payment in objects_of(source, "Payment"):
        system = r1_payment_to_system(payment, target)

        variables = [r2_piece_to_variable(p, target, trace)
                     for p in many(one(payment, "paidFrom"), "pieces")]
        system.variables = set(variables)

        atoms = [r3_amount_to_exact(payment, variables, trace, target)]
        if attr(payment, "maxPieces") is not None:
            atoms.append(r4_max_pieces_to_limit(payment, variables, target))

        system.rootConstraint = atoms[0] if len(atoms) == 1 else r5_conjunction(payment, atoms, target)
    
    return target

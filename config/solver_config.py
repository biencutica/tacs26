##################################
# SOLVER CONFIGURATION (Grover)  #
##################################
# How the problem is solved, kept apart from the problem and solution DSLs.
# It is an extra input to T2.

from besser.BUML.metamodel.structural import (
    Class, Property, DomainModel, Multiplicity, IntegerType, Constraint
)

SolverConfig = Class(name="SolverConfig")

# iterations is optional: if absent, T2 derives it from expectedSolutions,
# which the pipeline fills in from the classical baseline
SolverConfig.attributes = {
    Property(name="shots", type=IntegerType),
    Property(name="iterations", type=IntegerType, multiplicity=Multiplicity(0, 1)),
    Property(name="expectedSolutions", type=IntegerType, multiplicity=Multiplicity(0, 1)),
}

positiveShots = Constraint(
    name="positiveShots", context=SolverConfig, language="OCL",
    expression="context SolverConfig inv positiveShots: self.shots > 0")
nonNegativeRounds = Constraint(
    name="nonNegativeRounds", context=SolverConfig, language="OCL",
    expression="context SolverConfig inv nonNegativeRounds: "
               "self.iterations->isEmpty() or self.iterations >= 0")
nonNegativeSolutions = Constraint(
    name="nonNegativeSolutions", context=SolverConfig, language="OCL",
    expression="context SolverConfig inv nonNegativeSolutions: "
               "self.expectedSolutions->isEmpty() or self.expectedSolutions >= 0")

domain_model = DomainModel(
    name="Solver_Config",
    types={SolverConfig},
    constraints={positiveShots, nonNegativeRounds, nonNegativeSolutions},
)

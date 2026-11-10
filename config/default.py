# Solver choices used for every instance (an input of T2, never hard-coded in it)

from besser.BUML.metamodel.object import ObjectModel
from config.solver_config import SolverConfig, domain_model

solver_config = SolverConfig("default").attributes(shots=1024).build()

object_model = ObjectModel(name="Default_Config", objects={solver_config})

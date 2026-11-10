# Instance 'none'
# No solution: only even pieces, odd amount

from besser.BUML.metamodel.object import ObjectModel
from metamodels.problem_dsl import Wallet, Piece, Payment

wallet = Wallet("wallet").attributes(owner="Joao").build()
x4 = Piece("x4").attributes(label="x4", value=4).build()
y6 = Piece("y6").attributes(label="y6", value=6).build()
z10 = Piece("z10").attributes(label="z10", value=10).build()
payment = Payment("payment").attributes(amount=7).build()

wallet.pieces = {x4, y6, z10}
wallet.payments = payment

object_model = ObjectModel(name="none", objects={wallet, payment, x4, y6, z10})

# Instance 'limit'
# Near the qubit limit (17 qubits), three solutions with at most 3 pieces

from besser.BUML.metamodel.object import ObjectModel
from metamodels.problem_dsl import Wallet, Piece, Payment

wallet = Wallet("wallet").attributes(owner="Mara").build()
a3 = Piece("a3").attributes(label="a3", value=3).build()
b5 = Piece("b5").attributes(label="b5", value=5).build()
c6 = Piece("c6").attributes(label="c6", value=6).build()
d7 = Piece("d7").attributes(label="d7", value=7).build()
e9 = Piece("e9").attributes(label="e9", value=9).build()
f11 = Piece("f11").attributes(label="f11", value=11).build()
payment = Payment("payment").attributes(amount=20, maxPieces=3).build()

wallet.pieces = {a3, b5, c6, d7, e9, f11}
wallet.payments = payment

object_model = ObjectModel(name="limit", objects={wallet, payment, a3, b5, c6, d7, e9, f11})

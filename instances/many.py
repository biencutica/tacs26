# Instance 'many'
# Several solutions: 5 = 5 = 1 + 4 = 2 + 3 with at most 2 pieces

from besser.BUML.metamodel.object import ObjectModel
from metamodels.problem_dsl import Wallet, Piece, Payment

wallet = Wallet("wallet").attributes(owner="Rui").build()
p1 = Piece("p1").attributes(label="p1", value=1).build()
p2 = Piece("p2").attributes(label="p2", value=2).build()
p3 = Piece("p3").attributes(label="p3", value=3).build()
p4 = Piece("p4").attributes(label="p4", value=4).build()
p5 = Piece("p5").attributes(label="p5", value=5).build()
payment = Payment("payment").attributes(amount=5, maxPieces=2).build()

wallet.pieces = {p1, p2, p3, p4, p5}
wallet.payments = payment

object_model = ObjectModel(name="many", objects={wallet, payment, p1, p2, p3, p4, p5})

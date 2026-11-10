# Instance 'tiny'
# Checkable by hand (Annex A, class C example): only 3 + 5 + 7 pays 15

from besser.BUML.metamodel.object import ObjectModel
from metamodels.problem_dsl import Wallet, Piece, Payment

wallet = Wallet("wallet").attributes(owner="Ana").build()
coin2 = Piece("coin2").attributes(label="coin2", value=2).build()
coin3 = Piece("coin3").attributes(label="coin3", value=3).build()
note5 = Piece("note5").attributes(label="note5", value=5).build()
coin7 = Piece("coin7").attributes(label="coin7", value=7).build()
payment = Payment("payment").attributes(amount=15).build()

wallet.pieces = {coin2, coin3, note5, coin7}
wallet.payments = payment

object_model = ObjectModel(name="tiny", objects={wallet, payment, coin2, coin3, note5, coin7})

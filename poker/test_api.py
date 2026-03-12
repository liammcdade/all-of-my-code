from texasholdem import TexasHoldEm, ActionType

game = TexasHoldEm(buyin=500, big_blind=5, small_blind=2, max_players=6)
game.start_hand()

print(f"Hand Phase: {game.hand_phase}")
print(f"Players: {game.players}")
print(f"Board: {game.board}")
print(f"Player 0 attributes: {dir(game.players[0])}")

# Try an action
# ActionType has FOLD, CALL, CHECK, RAISE, ALL_IN
# game.take_action(ActionType.CALL)

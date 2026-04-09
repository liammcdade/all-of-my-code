import os

WORDS = []
with open(os.path.join(os.path.dirname(__file__), 'wordlist.txt'), 'r') as f:
    WORDS = [line.strip() for line in f if line.strip()]

def get_pattern(guess, answer):
    pattern = ['B'] * 5
    guess_list = list(guess)
    answer_list = list(answer)
    # greens
    for i in range(5):
        if guess_list[i] == answer_list[i]:
            pattern[i] = 'G'
            guess_list[i] = None
            answer_list[i] = None
    # yellows
    for i in range(5):
        if pattern[i] == 'B' and guess_list[i] is not None:
            if guess_list[i] in answer_list:
                pattern[i] = 'Y'
                idx = answer_list.index(guess_list[i])
                answer_list[idx] = None
    return ''.join(pattern)

class WordleSolver:
    def __init__(self):
        self.possible_answers = WORDS[:]
        self.all_words = WORDS[:]

    def update_possible(self, guess, feedback):
        self.possible_answers = [w for w in self.possible_answers if get_pattern(guess, w) == feedback]

    def best_guess(self):
        if len(self.possible_answers) == 1:
            return self.possible_answers[0]
        if not self.possible_answers:
            return None
        best_word = None
        best_expected = float('inf')
        total_answers = len(self.possible_answers)
        for candidate in self.all_words:
            pattern_to_count = {}
            for answer in self.possible_answers:
                pattern = get_pattern(candidate, answer)
                pattern_to_count[pattern] = pattern_to_count.get(pattern, 0) + 1
            expected_remaining = sum(count ** 2 for count in pattern_to_count.values()) / total_answers
            if expected_remaining < best_expected:
                best_expected = expected_remaining
                best_word = candidate
        return best_word

if __name__ == "__main__":
    solver = WordleSolver()
    print("Wordle Solver - Advanced Terminal Version")
    print("Feedback: G=green (correct position), Y=yellow (correct letter wrong position), B=black (wrong letter)")
    while True:
        next_guess = solver.best_guess()
        if not next_guess:
            print("No more possible words.")
            break
        print(f"Suggested guess: {next_guess}")
        guess = input("Enter your guess (5 letters): ").strip().lower()
        if not guess:
            break
        if len(guess) != 5:
            print("Guess must be 5 letters.")
            continue
        feedback = input("Enter feedback (5 chars, e.g., GYBBB): ").strip().upper()
        if len(feedback) != 5 or not all(c in 'GYB' for c in feedback):
            print("Feedback must be 5 characters of G, Y, B.")
            continue
        solver.update_possible(guess, feedback)
        print(f"Possible answers remaining: {len(solver.possible_answers)}")
        if len(solver.possible_answers) == 1:
            print(f"The answer is: {solver.possible_answers[0]}")
            break

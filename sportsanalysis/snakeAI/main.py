import pygame
import random
import numpy as np
import os
import pickle

# Settings
WIDTH, HEIGHT = 400, 400
GRID_SIZE = 20
FPS = 10

# Actions: [straight, right, left]
ACTIONS = [0, 1, 2]

# Q-learning settings
LEARNING_RATE = 0.1
DISCOUNT = 0.9
EPSILON_DECAY = 0.995
MIN_EPSILON = 0.01


class SnakeGame:
    def __init__(self):
        pygame.init()
        self.display = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Snake AI")
        self.clock = pygame.time.Clock()
        self.reset()

    def reset(self):
        self.direction = random.choice([(1, 0), (0, 1), (-1, 0), (0, -1)])
        self.snake = [(WIDTH // 2, HEIGHT // 2)]
        self.spawn_food()
        self.score = 0
        return self.get_state()

    def spawn_food(self):
        while True:
            self.food = (
                random.randrange(0, WIDTH, GRID_SIZE),
                random.randrange(0, HEIGHT, GRID_SIZE),
            )
            if self.food not in self.snake:
                break

    def step(self, action):
        self.move(action)
        new_head = self.snake[0]
        reward = -0.1
        done = False

        if (
            new_head in self.snake[1:]
            or not 0 <= new_head[0] < WIDTH
            or not 0 <= new_head[1] < HEIGHT
        ):
            return self.get_state(), -10, True

        if new_head == self.food:
            self.score += 1
            reward = 10
            self.spawn_food()
        else:
            self.snake.pop()

        return self.get_state(), reward, done

    def move(self, action):
        idx = [(1, 0), (0, 1), (-1, 0), (0, -1)].index(self.direction)
        if action == 1:  # right
            idx = (idx + 1) % 4
        elif action == 2:  # left
            idx = (idx - 1) % 4
        self.direction = [(1, 0), (0, 1), (-1, 0), (0, -1)][idx]

        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        self.snake.insert(0, (head_x + dx * GRID_SIZE, head_y + dy * GRID_SIZE))

    def get_state(self):
        head = self.snake[0]
        food = self.food
        dir = self.direction
        state = (
            dir[0],
            dir[1],
            int(food[0] > head[0]),
            int(food[0] < head[0]),
            int(food[1] > head[1]),
            int(food[1] < head[1]),
        )
        return tuple(state)

    def render(self):
        self.display.fill((0, 0, 0))
        for segment in self.snake:
            pygame.draw.rect(
                self.display, (0, 255, 0), (*segment, GRID_SIZE, GRID_SIZE)
            )
        pygame.draw.rect(self.display, (255, 0, 0), (*self.food, GRID_SIZE, GRID_SIZE))
        pygame.display.flip()
        self.clock.tick(FPS)


class SnakeAI:
    def __init__(self, q_file="qtable.pkl"):
        self.q_file = q_file
        self.q_table = self.load_q_table()
        self.epsilon = 1.0

    def load_q_table(self):
        if os.path.exists(self.q_file):
            with open(self.q_file, "rb") as f:
                return pickle.load(f)
        return {}

    def save_q_table(self):
        with open(self.q_file, "wb") as f:
            pickle.dump(self.q_table, f)

    def get_qs(self, state):
        if state not in self.q_table:
            self.q_table[state] = np.zeros(len(ACTIONS))
        return self.q_table[state]

    def choose_action(self, state):
        if random.random() < self.epsilon:
            return random.choice(ACTIONS)
        return int(np.argmax(self.get_qs(state)))

    def learn(self, old_state, action, reward, new_state):
        old_q = self.get_qs(old_state)
        max_future_q = np.max(self.get_qs(new_state))
        old_q[action] = (1 - LEARNING_RATE) * old_q[action] + LEARNING_RATE * (
            reward + DISCOUNT * max_future_q
        )
        self.q_table[old_state] = old_q


if __name__ == "__main__":
    game = SnakeGame()
    ai = SnakeAI()

    episode = 0
    try:
        while True:
            state = game.reset()
            done = False
            total_reward = 0

            while not done:
                action = ai.choose_action(state)
                new_state, reward, done = game.step(action)
                ai.learn(state, action, reward, new_state)
                state = new_state
                total_reward += reward
                game.render()

            episode += 1
            ai.epsilon = max(MIN_EPSILON, ai.epsilon * EPSILON_DECAY)
            print(
                f"Episode {episode} - Score: {game.score} - Epsilon: {ai.epsilon:.3f}"
            )
            ai.save_q_table()

    except KeyboardInterrupt:
        print("Training stopped.")
        ai.save_q_table()
        pygame.quit()

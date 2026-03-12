import pygame
import numpy as np
import math

# -----------------------
# MATCH PARAMETERS
# -----------------------
team_a_elo = 2042
team_b_elo = 1538
baseline_goals = 2.53
match_time_sec = 90 * 60  # 90 minutes in seconds
tick_time = 1  # 1 second per tick

# -----------------------
# FUNCTIONS
# -----------------------
def lambda_per_team(team_a_elo, team_b_elo, baseline_goals=2.53, cap=250):
    D = team_b_elo - team_a_elo
    if D > cap:
        excess = D - cap
        D = cap - math.sqrt(excess)
    elif D < -cap:
        excess = -D - cap
        D = -cap + math.sqrt(excess)
    lambda_base = baseline_goals / 2
    lambda_A = lambda_base * 10 ** (-D / 400)
    lambda_B = lambda_base * 10 ** (D / 400)
    return lambda_A, lambda_B

def skellam_win_draw_probs(lambda_A, lambda_B, goals_A, goals_B, time_elapsed):
    time_left = match_time_sec - time_elapsed
    rem_A = max(lambda_A * (time_left / match_time_sec) - goals_A, 0)
    rem_B = max(lambda_B * (time_left / match_time_sec) - goals_B, 0)
    diff = rem_B - rem_A
    # Logistic-like odds based on difference
    win_prob = 1 / (1 + 10 ** (-diff / 400))
    draw_prob = 0.1  # simplified draw probability
    loss_prob = 1 - win_prob - draw_prob
    return max(min(win_prob, 1), 0), max(min(draw_prob, 1), 0), max(min(loss_prob, 1), 0)

# -----------------------
# INITIALIZATION
# -----------------------
pygame.init()
width, height = 800, 500
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Live Football Simulator")
font = pygame.font.SysFont(None, 36)
clock = pygame.time.Clock()

# Compute initial expected goals
lambda_A_total, lambda_B_total = lambda_per_team(team_a_elo, team_b_elo, baseline_goals)
rate_A_per_sec = lambda_A_total / match_time_sec
rate_B_per_sec = lambda_B_total / match_time_sec

# -----------------------
# GAME STATE
# -----------------------
score_A = 0
score_B = 0
time_elapsed = 0
win_prob, draw_prob, loss_prob = 0.5, 0.1, 0.4
red_cards_A, red_cards_B = 0, 0

# -----------------------
# BUTTONS
# -----------------------
button_color = (200, 200, 200)
button_hover = (150, 150, 150)
buttons = {
    "Goal A": pygame.Rect(50, 400, 100, 40),
    "Goal B": pygame.Rect(200, 400, 100, 40),
    "Red Card A": pygame.Rect(350, 400, 120, 40),
    "Red Card B": pygame.Rect(500, 400, 120, 40),
}

# -----------------------
# MAIN LOOP
# -----------------------
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if buttons["Goal A"].collidepoint(mouse_pos):
                score_A += 1
            elif buttons["Goal B"].collidepoint(mouse_pos):
                score_B += 1
            elif buttons["Red Card A"].collidepoint(mouse_pos):
                red_cards_A += 1
                lambda_A_total *= 0.8  # reduce expected goals by 20%
                rate_A_per_sec = lambda_A_total / match_time_sec
            elif buttons["Red Card B"].collidepoint(mouse_pos):
                red_cards_B += 1
                lambda_B_total *= 0.8  # reduce expected goals by 20%
                rate_B_per_sec = lambda_B_total / match_time_sec

    # Tick
    time_elapsed += tick_time
    if time_elapsed > match_time_sec:
        running = False

    # Automatic Poisson goal scoring per second
    if np.random.rand() < rate_A_per_sec:
        score_A += 1
    if np.random.rand() < rate_B_per_sec:
        score_B += 1

    # Update dynamic probabilities every second
    win_prob, draw_prob, loss_prob = skellam_win_draw_probs(
        lambda_A_total, lambda_B_total, score_A, score_B, time_elapsed
    )

    # -----------------------
    # DRAW GUI
    # -----------------------
    screen.fill((0, 128, 0))  # green pitch

    # Score and time
    score_text = font.render(f"{score_A} - {score_B}", True, (255, 255, 255))
    time_text = font.render(f"{time_elapsed//60}'", True, (255, 255, 255))
    prob_text = font.render(f"Win: {win_prob:.2f} Draw: {draw_prob:.2f} Loss: {loss_prob:.2f}", True, (255, 255, 0))
    red_text = font.render(f"Red Cards: A={red_cards_A} B={red_cards_B}", True, (255, 0, 0))

    screen.blit(score_text, (width//2 - 50, height//2 - 50))
    screen.blit(time_text, (width//2 - 50, height//2))
    screen.blit(prob_text, (50, height//2 + 50))
    screen.blit(red_text, (50, height//2 + 90))

    # Draw buttons
    for text, rect in buttons.items():
        color = button_hover if rect.collidepoint(mouse_pos) else button_color
        pygame.draw.rect(screen, color, rect)
        label = font.render(text, True, (0, 0, 0))
        screen.blit(label, (rect.x + 5, rect.y + 5))

    pygame.display.flip()
    clock.tick(1)  # 1 tick per second for real-time

pygame.quit()
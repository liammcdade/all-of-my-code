import tkinter as tk
from tkinter import ttk
import math
import time
import random

class PoolGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Pool Game")
        self.root.geometry("1200x800")
        self.root.resizable(False, False)

        # Game constants
        self.TABLE_WIDTH = 800
        self.TABLE_HEIGHT = 400
        self.BALL_RADIUS = 10
        self.POCKET_RADIUS = 55
        self.FRICTION = 0.97
        self.CUSHION_BOUNCE = 0.85

        # Pockets positions
        self.POCKETS = [
            {'x': 30, 'y': 30},
            {'x': self.TABLE_WIDTH / 2, 'y': 25},
            {'x': self.TABLE_WIDTH - 30, 'y': 30},
            {'x': 30, 'y': self.TABLE_HEIGHT - 30},
            {'x': self.TABLE_WIDTH / 2, 'y': self.TABLE_HEIGHT - 25},
            {'x': self.TABLE_WIDTH - 30, 'y': self.TABLE_HEIGHT - 30}
        ]

        # Game state
        self.game_mode = 'menu'
        self.balls = []
        self.cue_position = {'x': 0, 'y': 0}
        self.aim_angle = 0
        self.power = 0
        self.is_dragging = False
        self.drag_start = {'x': 0, 'y': 0}
        self.locked_angle = None
        self.cue_grabbed = False
        self.cue_pull_distance = 0
        self.current_player = 1
        self.player1_balls = []
        self.player2_balls = []
        self.balls_assigned = False
        self.win_probability = {'p1': 50, 'p2': 50}
        self.animation_id = None
        self.current_ai_shot = None

        # GUI elements
        self.setup_gui()
        self.show_menu()

    def setup_gui(self):
        # Main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Top control panel
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Canvas for the pool table
        self.canvas = tk.Canvas(self.main_frame, width=self.TABLE_WIDTH,
                               height=self.TABLE_HEIGHT, bg='#1a5f1a',
                               cursor='crosshair')
        self.canvas.pack(pady=10)

        # Info frame for game status
        self.info_frame = ttk.Frame(self.main_frame)
        self.info_frame.pack(fill=tk.X, padx=10, pady=5)

        # Bind mouse events
        self.canvas.bind('<Motion>', self.handle_mouse_move)
        self.canvas.bind('<Button-1>', self.handle_mouse_down)
        self.canvas.bind('<ButtonRelease-1>', self.handle_mouse_up)

    def show_menu(self):
        self.game_mode = 'menu'

        # Clear existing widgets
        for widget in self.control_frame.winfo_children():
            widget.destroy()
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        # Menu frame
        menu_frame = ttk.Frame(self.main_frame)
        menu_frame.place(relx=0.5, rely=0.5, anchor='center')

        title_label = ttk.Label(menu_frame, text="Pool Game",
                               font=('Arial', 36, 'bold'))
        title_label.pack(pady=20)

        button_frame = ttk.Frame(menu_frame)
        button_frame.pack(pady=20)

        eight_ball_btn = ttk.Button(button_frame, text="8-Ball",
                                   command=self.start_eight_ball,
                                   style='Game.TButton')
        eight_ball_btn.pack(pady=10, ipadx=20, ipady=10)

        nine_ball_btn = ttk.Button(button_frame, text="9-Ball",
                                  command=self.start_nine_ball,
                                  style='Game.TButton')
        nine_ball_btn.pack(pady=10, ipadx=20, ipady=10)

        ai_btn = ttk.Button(button_frame, text="AI vs AI",
                           command=self.start_ai_game,
                           style='Game.TButton')
        ai_btn.pack(pady=10, ipadx=20, ipady=10)

        # Style for game buttons
        style = ttk.Style()
        style.configure('Game.TButton', font=('Arial', 16))

    def start_eight_ball(self):
        self.game_mode = '8ball'
        self.init_eight_ball()
        self.setup_game_ui()

    def start_nine_ball(self):
        self.game_mode = '9ball'
        self.init_nine_ball()
        self.setup_game_ui()

    def start_ai_game(self):
        self.game_mode = 'ai'
        self.init_eight_ball()  # Use 8-ball rules for AI
        self.setup_ai_game_ui()
        # Start AI gameplay
        self.ai_take_turn()

    def setup_game_ui(self):
        # Clear menu
        for widget in self.main_frame.winfo_children():
            if hasattr(widget, 'place_info') and widget.place_info():
                widget.destroy()

        # Control buttons
        back_btn = ttk.Button(self.control_frame, text="Back to Menu",
                             command=self.show_menu)
        back_btn.pack(side=tk.LEFT, padx=5)

        self.player_label = ttk.Label(self.control_frame,
                                     text=f"Player {self.current_player}'s Turn",
                                     font=('Arial', 14))
        self.player_label.pack(side=tk.LEFT, padx=20)

        self.instructions_label = ttk.Label(self.control_frame,
                                           text="Click & hold anywhere to aim • Drag to set power • Release to shoot",
                                           font=('Arial', 10))
        self.instructions_label.pack(side=tk.LEFT, padx=20)

        self.power_label = ttk.Label(self.control_frame,
                                    text="Power: 0%",
                                    font=('Arial', 12))
        self.power_label.pack(side=tk.RIGHT, padx=5)

        # Game-specific UI
        if self.game_mode == '8ball':
            self.setup_eight_ball_ui()
        elif self.game_mode == '9ball':
            self.setup_nine_ball_ui()

        # Start animation
        self.animate()

    def setup_eight_ball_ui(self):
        # Player info panels
        self.p1_frame = ttk.LabelFrame(self.info_frame, text="Player 1",
                                      padding=10)
        self.p1_frame.pack(side=tk.LEFT, padx=10, fill=tk.Y)

        self.p1_type_label = ttk.Label(self.p1_frame,
                                      text="Not assigned")
        self.p1_type_label.pack()

        self.p1_balls_frame = ttk.Frame(self.p1_frame)
        self.p1_balls_frame.pack(pady=5)

        self.p1_prob_label = ttk.Label(self.p1_frame,
                                      text="Win Probability: 50%")
        self.p1_prob_label.pack(pady=5)

        self.p1_prob_bar = ttk.Progressbar(self.p1_frame, orient=tk.HORIZONTAL,
                                          length=200, mode='determinate',
                                          value=50)
        self.p1_prob_bar.pack()

        self.p2_frame = ttk.LabelFrame(self.info_frame, text="Player 2",
                                      padding=10)
        self.p2_frame.pack(side=tk.RIGHT, padx=10, fill=tk.Y)

        self.p2_type_label = ttk.Label(self.p2_frame,
                                      text="Not assigned")
        self.p2_type_label.pack()

        self.p2_balls_frame = ttk.Frame(self.p2_frame)
        self.p2_balls_frame.pack(pady=5)

        self.p2_prob_label = ttk.Label(self.p2_frame,
                                      text="Win Probability: 50%")
        self.p2_prob_label.pack(pady=5)

        self.p2_prob_bar = ttk.Progressbar(self.p2_frame, orient=tk.HORIZONTAL,
                                          length=200, mode='determinate',
                                          value=50)
        self.p2_prob_bar.pack()

    def setup_nine_ball_ui(self):
        # Nine ball remaining balls display
        balls_frame = ttk.LabelFrame(self.info_frame, text="Balls Remaining",
                                    padding=10)
        balls_frame.pack(pady=10)

        self.nine_balls_frame = ttk.Frame(balls_frame)
        self.nine_balls_frame.pack()

        self.next_ball_label = ttk.Label(balls_frame,
                                        text="Next ball to hit: 1")
        self.next_ball_label.pack(pady=5)

    def setup_ai_game_ui(self):
        # Clear menu
        for widget in self.main_frame.winfo_children():
            if hasattr(widget, 'place_info') and widget.place_info():
                widget.destroy()

        # Control buttons
        back_btn = ttk.Button(self.control_frame, text="Back to Menu",
                             command=self.show_menu)
        back_btn.pack(side=tk.LEFT, padx=5)

        self.player_label = ttk.Label(self.control_frame,
                                     text=f"AI Player {self.current_player}'s Turn",
                                     font=('Arial', 14))
        self.player_label.pack(side=tk.LEFT, padx=20)

        self.ai_status_label = ttk.Label(self.control_frame,
                                        text="AI thinking...",
                                        font=('Arial', 12))
        self.ai_status_label.pack(side=tk.RIGHT, padx=5)

        # AI-specific UI
        self.setup_eight_ball_ui()

        # Disable mouse interaction for AI mode
        self.canvas.unbind('<Motion>')
        self.canvas.unbind('<Button-1>')
        self.canvas.unbind('<ButtonRelease-1>')

        # Start animation
        self.animate()

    def ai_take_turn(self):
        if self.game_mode != 'ai':
            return

        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if not cue_ball:
            return

        self.ai_status_label.config(text=f"AI Player {self.current_player} thinking...")

        # Simple AI logic: find best shot
        best_shot = self.find_best_ai_shot()

        if best_shot:
            # Store the shot for visualization and execute after delay
            self.current_ai_shot = best_shot
            self.root.after(1000, lambda: self.execute_ai_shot(best_shot))
        else:
            # No good shot found, make a random shot
            self.root.after(1000, self.make_random_ai_shot)

    def find_best_ai_shot(self):
        """Advanced mathematical AI: calculate precise shots for pocketing balls"""
        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if not cue_ball:
            return None

        best_shot = None
        best_score = -1

        # Get target balls for current player
        target_balls = []
        if self.game_mode == 'ai' and self.balls_assigned:
            target_type = self.player1_balls[0] if self.current_player == 1 else self.player2_balls[0]
            target_balls = [b for b in self.balls if b['type'] == target_type and not b['pocketed']
                           and b['number'] != 8]  # Don't aim for 8-ball unless it's the only choice
        else:
            # Early game: target any visible ball
            target_balls = [b for b in self.balls if b['number'] > 0 and not b['pocketed']]

        for target_ball in target_balls:
            # Calculate precise shot for this ball
            shot = self.calculate_precise_shot(cue_ball, target_ball)
            if shot and shot['score'] > best_score:
                best_score = shot['score']
                best_shot = shot

        return best_shot

    def calculate_precise_shot(self, cue_ball, target_ball):
        """Calculate the mathematically precise shot to pocket a ball"""
        best_shot = None
        best_score = 0

        # Try each pocket to see which one gives the best shot
        for pocket in self.POCKETS:
            shot = self.calculate_shot_to_pocket(cue_ball, target_ball, pocket)
            if shot and shot['score'] > best_score:
                best_score = shot['score']
                best_shot = shot

        return best_shot

    def calculate_shot_to_pocket(self, cue_ball, target_ball, pocket):
        """Calculate the exact shot needed to send target_ball into pocket"""
        # Vector from target ball to pocket
        pocket_dx = pocket['x'] - target_ball['x']
        pocket_dy = pocket['y'] - target_ball['y']
        pocket_distance = math.sqrt(pocket_dx**2 + pocket_dy**2)

        # Skip if ball is too far from pocket
        if pocket_distance > 180:
            return None

        # The target ball needs to hit the pocket, so we need to aim for where
        # the ball should be hit to go toward the pocket
        pocket_angle = math.atan2(pocket_dy, pocket_dx)

        # For straight-in shots, we need to account for the ball's radius
        # The cue ball should hit the target ball at the correct contact point
        contact_offset = self.BALL_RADIUS * 1.1  # Slightly more than ball radius for realistic contact

        # Calculate where to aim on the target ball to send it toward the pocket
        aim_x = target_ball['x'] - math.cos(pocket_angle) * contact_offset
        aim_y = target_ball['y'] - math.sin(pocket_angle) * contact_offset

        # Check if this aim point is accessible (not blocked)
        if not self.is_aim_point_clear(cue_ball, aim_x, aim_y):
            return None

        # Calculate the angle from cue ball to aim point
        aim_dx = aim_x - cue_ball['x']
        aim_dy = aim_y - cue_ball['y']
        shot_distance = math.sqrt(aim_dx**2 + aim_dy**2)
        shot_angle = math.atan2(aim_dy, aim_dx)

        # Check if the shot path is clear
        if self.is_shot_path_blocked(cue_ball, aim_x, aim_y):
            return None

        # Calculate required power based on distance and physics
        power = self.calculate_precise_power(shot_distance, pocket_distance)

        # Calculate shot quality score
        score = self.evaluate_shot_quality(cue_ball, target_ball, pocket, shot_distance, pocket_distance)

        return {
            'angle': shot_angle,
            'power': power,
            'target': target_ball,
            'pocket': pocket,
            'score': score,
            'aim_x': aim_x,
            'aim_y': aim_y
        }

    def is_aim_point_clear(self, cue_ball, aim_x, aim_y):
        """Check if the line from cue ball to aim point is clear"""
        return not self.is_shot_path_blocked(cue_ball, aim_x, aim_y)

    def is_shot_path_blocked(self, start_x, start_y, end_x, end_y):
        """Check if any balls block the path between two points"""
        if isinstance(start_x, dict):  # If passed ball objects
            start_pos = start_x
            end_pos = start_y
            start_x, start_y = start_pos['x'], start_pos['y']
            end_x, end_y = end_pos['x'], end_pos['y']

        # Check each ball to see if it intersects the line
        for ball in self.balls:
            if ball['pocketed'] or ball['number'] == 0:  # Skip pocketed balls and cue ball
                continue

            # Calculate distance from ball center to line
            dx = end_x - start_x
            dy = end_y - start_y
            length = math.sqrt(dx**2 + dy**2)

            if length == 0:
                continue

            # Vector from start to ball
            ball_dx = ball['x'] - start_x
            ball_dy = ball['y'] - start_y

            # Project onto line
            dot = (ball_dx * dx + ball_dy * dy) / (length ** 2)
            dot = max(0, min(1, dot))  # Clamp to line segment

            # Closest point on line
            closest_x = start_x + dot * dx
            closest_y = start_y + dot * dy

            # Distance from ball to closest point
            dist_dx = ball['x'] - closest_x
            dist_dy = ball['y'] - closest_y
            distance = math.sqrt(dist_dx**2 + dist_dy**2)

            # If ball is too close to the line, it's blocked
            if distance < self.BALL_RADIUS * 1.8:  # Allow some tolerance
                return True

        return False

    def calculate_precise_power(self, shot_distance, pocket_distance):
        """Calculate precise power needed for the shot"""
        # Base power depends on shot distance
        base_power = shot_distance * 0.3  # Rough approximation

        # Adjust for pocket distance (farther pockets need more power)
        pocket_factor = pocket_distance / 100.0
        power = base_power * (0.8 + pocket_factor * 0.4)

        # Add some safety margin and clamp to reasonable range
        power = power * 1.1  # 10% safety margin
        return max(40, min(95, power))

    def evaluate_shot_quality(self, cue_ball, target_ball, pocket, shot_distance, pocket_distance):
        """Evaluate the quality of a potential shot"""
        score = 100  # Start with perfect score

        # Distance penalty (closer shots are better)
        distance_penalty = shot_distance / 200.0  # Normalize
        score -= distance_penalty * 20

        # Pocket distance bonus (balls closer to pockets are easier)
        if pocket_distance < 80:
            score += 15  # Bonus for balls very close to pockets
        elif pocket_distance < 120:
            score += 10

        # Angle quality (prefer straight-in shots over cuts)
        pocket_dx = pocket['x'] - target_ball['x']
        pocket_dy = pocket['y'] - target_ball['y']
        pocket_angle = math.atan2(pocket_dy, pocket_dx)

        shot_dx = target_ball['x'] - cue_ball['x']
        shot_dy = target_ball['y'] - cue_ball['y']
        shot_angle = math.atan2(shot_dy, shot_dx)

        angle_diff = abs(self.normalize_angle(pocket_angle - shot_angle))
        angle_diff = min(angle_diff, 2*math.pi - angle_diff)

        # Heavy penalty for extreme cut shots
        if angle_diff > math.pi/3:  # More than 60 degrees
            score -= 40
        elif angle_diff > math.pi/6:  # More than 30 degrees
            score -= 20

        # Bonus for straight-in shots
        if angle_diff < math.pi/12:  # Less than 15 degrees
            score += 10

        # Position quality (balls in the center are generally better positioned)
        table_center_x = self.TABLE_WIDTH / 2
        table_center_y = self.TABLE_HEIGHT / 2
        ball_center_dist = math.sqrt((target_ball['x'] - table_center_x)**2 +
                                   (target_ball['y'] - table_center_y)**2)

        # Slight bonus for balls near center (easier to get good shots)
        center_bonus = max(0, (200 - ball_center_dist) / 200 * 10)
        score += center_bonus

        return max(0, score)

    def is_shot_blocked(self, cue_ball, target):
        """Check if there's a ball blocking the shot"""
        for ball in self.balls:
            if ball['number'] == 0 or ball['number'] == target['number'] or ball['pocketed']:
                continue

            # Check if ball is on the line between cue and target
            # Simple check: if ball is within a narrow corridor
            dx = ball['x'] - cue_ball['x']
            dy = ball['y'] - cue_ball['y']
            target_dx = target['x'] - cue_ball['x']
            target_dy = target['y'] - cue_ball['y']

            # Normalize target direction
            target_dist = math.sqrt(target_dx*target_dx + target_dy*target_dy)
            if target_dist == 0:
                continue
            target_nx = target_dx / target_dist
            target_ny = target_dy / target_dist

            # Project ball onto target line
            dot_product = dx * target_nx + dy * target_ny
            if dot_product < 0 or dot_product > target_dist:
                continue  # Ball is not between cue and target

            # Check perpendicular distance
            perp_dist = abs(dy * target_nx - dx * target_ny)
            if perp_dist < self.BALL_RADIUS * 2.5:  # Within blocking distance
                return True

        return False

    def execute_ai_shot(self, shot):
        """Execute the AI's chosen shot"""
        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if cue_ball and shot:
            speed = shot['power'] * 0.15
            cue_ball['vx'] = math.cos(shot['angle']) * speed
            cue_ball['vy'] = math.sin(shot['angle']) * speed

            self.ai_status_label.config(text=f"AI Player {self.current_player} shot!")

            # Check for balls stopping after a delay
            self.root.after(3000, self.check_ai_turn_end)

    def make_random_ai_shot(self):
        """Make a random shot when no good shot is found"""
        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if cue_ball:
            # Random angle and power
            angle = math.pi * 2 * (0.5 - random.random())  # Random angle
            power = 30 + random.random() * 40  # Random power between 30-70
            speed = power * 0.15

            cue_ball['vx'] = math.cos(angle) * speed
            cue_ball['vy'] = math.sin(angle) * speed

            self.ai_status_label.config(text=f"AI Player {self.current_player} shot randomly!")

            self.root.after(3000, self.check_ai_turn_end)

    def check_ai_turn_end(self):
        """Check if balls have stopped and switch to next AI player"""
        if not self.balls_moving():
            # Switch to next player
            self.current_player = 2 if self.current_player == 1 else 1
            self.player_label.config(text=f"AI Player {self.current_player}'s Turn")
            self.current_ai_shot = None  # Clear visualization

            # Take next AI turn
            self.root.after(1000, self.ai_take_turn)

    def get_ball_color(self, num):
        colors = {
            1: '#FFFF00', 2: '#0000FF', 3: '#FF0000', 4: '#800080',
            5: '#FFA500', 6: '#006400', 7: '#8B0000', 8: '#000000',
            9: '#FFFF00', 10: '#0000FF', 11: '#FF0000', 12: '#800080',
            13: '#FFA500', 14: '#006400', 15: '#8B0000'
        }
        return colors.get(num, '#FFFFFF')

    def init_eight_ball(self):
        rack_x = self.TABLE_WIDTH * 0.7
        rack_y = self.TABLE_HEIGHT / 2
        ball_order = [1, 9, 2, 10, 8, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]

        self.balls = [
            {
                'id': 0,
                'x': self.TABLE_WIDTH * 0.25,
                'y': self.TABLE_HEIGHT / 2,
                'vx': 0,
                'vy': 0,
                'color': '#FFFFFF',
                'number': 0,
                'type': 'cue',
                'pocketed': False
            }
        ]

        ball_index = 0
        for row in range(5):
            for col in range(row + 1):
                if ball_index >= 15:
                    break
                x = rack_x + row * self.BALL_RADIUS * 1.73
                y = rack_y + (col - row / 2) * self.BALL_RADIUS * 2
                ball_num = ball_order[ball_index]
                self.balls.append({
                    'id': ball_num,
                    'x': x,
                    'y': y,
                    'vx': 0,
                    'vy': 0,
                    'color': self.get_ball_color(ball_num),
                    'number': ball_num,
                    'type': 'eight' if ball_num == 8 else ('solid' if ball_num <= 7 else 'stripe'),
                    'pocketed': False
                })
                ball_index += 1

        self.current_player = 1
        self.player1_balls = []
        self.player2_balls = []
        self.balls_assigned = False

    def init_nine_ball(self):
        rack_x = self.TABLE_WIDTH * 0.7
        rack_y = self.TABLE_HEIGHT / 2
        diamond_order = [1, 2, 3, 4, 9, 5, 6, 7, 8]

        self.balls = [
            {
                'id': 0,
                'x': self.TABLE_WIDTH * 0.25,
                'y': self.TABLE_HEIGHT / 2,
                'vx': 0,
                'vy': 0,
                'color': '#FFFFFF',
                'number': 0,
                'type': 'cue',
                'pocketed': False
            }
        ]

        ball_index = 0
        for row in range(5):
            balls_in_row = row + 1 if row < 3 else 5 - row
            for col in range(balls_in_row):
                if ball_index >= 9:
                    break
                x = rack_x + row * self.BALL_RADIUS * 1.73
                y = rack_y + (col - (balls_in_row - 1) / 2) * self.BALL_RADIUS * 2
                ball_num = diamond_order[ball_index]
                self.balls.append({
                    'id': ball_num,
                    'x': x,
                    'y': y,
                    'vx': 0,
                    'vy': 0,
                    'color': self.get_ball_color(ball_num),
                    'number': ball_num,
                    'type': 'numbered',
                    'pocketed': False
                })
                ball_index += 1

        self.current_player = 1

    def calculate_win_probability(self):
        if not self.balls_assigned or self.game_mode != '8ball':
            self.win_probability = {'p1': 50, 'p2': 50}
            return

        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if not cue_ball:
            self.win_probability = {'p1': 50, 'p2': 50}
            return

        p1_type = self.player1_balls[0] if self.player1_balls else None
        p2_type = self.player2_balls[0] if self.player2_balls else None

        p1_balls_left = [b for b in self.balls if b['type'] == p1_type and not b['pocketed']]
        p2_balls_left = [b for b in self.balls if b['type'] == p2_type and not b['pocketed']]

        # Simplified win probability calculation
        p1_ball_count = len(p1_balls_left)
        p2_ball_count = len(p2_balls_left)

        if p1_ball_count + p2_ball_count == 0:
            self.win_probability = {'p1': 50, 'p2': 50}
        else:
            total = p1_ball_count + p2_ball_count
            self.win_probability = {
                'p1': int((p1_ball_count / total) * 100),
                'p2': int((p2_ball_count / total) * 100)
            }

    def animate(self):
        self.update_balls()
        self.draw_table()
        self.draw_balls()
        self.draw_cue()
        self.update_ui()

        self.animation_id = self.root.after(16, self.animate)  # ~60 FPS

    def draw_table(self):
        self.canvas.delete('table')

        # Table felt
        self.canvas.create_rectangle(0, 0, self.TABLE_WIDTH, self.TABLE_HEIGHT,
                                   fill='#1a5f1a', tags='table')

        # Table border
        self.canvas.create_rectangle(15, 15, self.TABLE_WIDTH - 15, self.TABLE_HEIGHT - 15,
                                   outline='#8B4513', width=30, tags='table')

        # Pockets
        for pocket in self.POCKETS:
            self.canvas.create_oval(pocket['x'] - self.POCKET_RADIUS,
                                   pocket['y'] - self.POCKET_RADIUS,
                                   pocket['x'] + self.POCKET_RADIUS,
                                   pocket['y'] + self.POCKET_RADIUS,
                                   fill='#000000', tags='table')

        # Center line
        self.canvas.create_line(self.TABLE_WIDTH * 0.25, 40,
                               self.TABLE_WIDTH * 0.25, self.TABLE_HEIGHT - 40,
                               fill='#FFFFFF', width=2, dash=(5, 5), tags='table')

    def draw_balls(self):
        self.canvas.delete('balls')

        # Debug: print ball count
        visible_balls = [b for b in self.balls if not b['pocketed']]
        print(f"Drawing {len(visible_balls)} visible balls out of {len(self.balls)} total")

        for ball in self.balls:
            if ball['pocketed']:
                continue

            x, y = ball['x'], ball['y']

            # Ball shadow/highlight effect (simplified)
            self.canvas.create_oval(x - self.BALL_RADIUS, y - self.BALL_RADIUS,
                                   x + self.BALL_RADIUS, y + self.BALL_RADIUS,
                                   fill=ball['color'], outline='#000000',
                                   width=1, tags='balls')

            # Stripe for striped balls
            if ball['type'] == 'stripe' and ball['number'] > 8:
                self.canvas.create_oval(x - self.BALL_RADIUS, y - self.BALL_RADIUS * 0.6,
                                       x + self.BALL_RADIUS, y + self.BALL_RADIUS * 0.6,
                                       fill='#FFFFFF', outline='', tags='balls')

            # Ball number
            text_color = '#FFFFFF' if ball['number'] <= 8 else '#000000'
            if ball['number'] == 8:
                text_color = '#FFFFFF'
            self.canvas.create_text(x, y, text=str(ball['number']),
                                   fill=text_color, font=('Arial', 10, 'bold'),
                                   tags='balls')

    def draw_cue(self):
        self.canvas.delete('cue')

        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if not cue_ball or self.balls_moving():
            return

        current_angle = self.locked_angle if self.locked_angle is not None else self.aim_angle
        cue_length = 200

        # Fixed cue position (doesn't move during dragging)
        cue_offset = 30
        end_x = cue_ball['x'] - math.cos(current_angle) * (self.BALL_RADIUS + cue_offset)
        end_y = cue_ball['y'] - math.sin(current_angle) * (self.BALL_RADIUS + cue_offset)
        start_x = end_x - math.cos(current_angle) * cue_length
        start_y = end_y - math.sin(current_angle) * cue_length

        # Cue stick with gradient colors
        gradient_stops = 10
        for i in range(gradient_stops):
            ratio = i / (gradient_stops - 1)
            x1 = start_x + (end_x - start_x) * ratio
            y1 = start_y + (end_y - start_y) * ratio
            x2 = start_x + (end_x - start_x) * (ratio + 1/gradient_stops)
            y2 = start_y + (end_y - start_y) * (ratio + 1/gradient_stops)

            # Create gradient from dark brown to light brown
            r = int(139 + (245 - 139) * ratio)
            g = int(69 + (222 - 69) * ratio)
            b = int(19 + (179 - 19) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'

            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=8, tags='cue')

        # Cue tip
        tip_x = end_x
        tip_y = end_y
        tip_size = 6
        tip_color = '#FFD700'
        self.canvas.create_oval(tip_x - tip_size, tip_y - tip_size,
                               tip_x + tip_size, tip_y + tip_size,
                               fill=tip_color, outline='#8B4513', width=2, tags='cue')

        # Power indicator when dragging
        if self.is_dragging and self.power > 0:
            # Show power bar next to cue ball
            bar_width = 100
            bar_height = 8
            bar_x = cue_ball['x'] + 50
            bar_y = cue_ball['y'] - 20

            # Background bar
            self.canvas.create_rectangle(bar_x, bar_y, bar_x + bar_width, bar_y + bar_height,
                                       fill='#333333', outline='#FFFFFF', width=1, tags='cue')

            # Power fill
            fill_width = (self.power / 100) * bar_width
            self.canvas.create_rectangle(bar_x, bar_y, bar_x + fill_width, bar_y + bar_height,
                                       fill='#FFD700', outline='', tags='cue')

            # Power text
            self.canvas.create_text(bar_x + bar_width/2, bar_y - 10,
                                   text=f"Power: {int(self.power)}%",
                                   fill='#FFD700', font=('Arial', 10, 'bold'), tags='cue')

            # Show drag line from drag start to current mouse position
            self.canvas.create_line(self.drag_start['x'], self.drag_start['y'],
                                   self.cue_position['x'], self.cue_position['y'],
                                   fill='#FF6B6B', width=2, dash=(5, 5), tags='cue')

            # Show drag start point
            self.canvas.create_oval(self.drag_start['x'] - 5, self.drag_start['y'] - 5,
                                   self.drag_start['x'] + 5, self.drag_start['y'] + 5,
                                   fill='#FF6B6B', outline='#FFFFFF', width=2, tags='cue')

        # Trajectory prediction (only when not dragging)
        if not self.is_dragging:
            # Show aiming line
            aim_x = cue_ball['x'] + math.cos(current_angle) * 150
            aim_y = cue_ball['y'] + math.sin(current_angle) * 150
            self.canvas.create_line(cue_ball['x'], cue_ball['y'], aim_x, aim_y,
                                   fill='#FFFFFF', width=2, dash=(5, 5), tags='cue')

            # Show predicted path with bounces
            self.draw_trajectory(cue_ball, current_angle)

        # In AI mode, show the calculated aim point (for debugging)
        elif self.game_mode == 'ai' and hasattr(self, 'current_ai_shot') and self.current_ai_shot:
            shot = self.current_ai_shot
            if 'aim_x' in shot and 'aim_y' in shot:
                # Draw line from cue ball to aim point
                self.canvas.create_line(cue_ball['x'], cue_ball['y'], shot['aim_x'], shot['aim_y'],
                                       fill='#00FF00', width=3, tags='cue')
                # Draw aim point
                self.canvas.create_oval(shot['aim_x'] - 5, shot['aim_y'] - 5,
                                       shot['aim_x'] + 5, shot['aim_y'] + 5,
                                       fill='#00FF00', outline='#FFFFFF', width=2, tags='cue')

    def draw_trajectory(self, cue_ball, angle):
        """Draw the predicted ball trajectory with cushion bounces"""
        current_x = cue_ball['x']
        current_y = cue_ball['y']
        dir_x = math.cos(angle)
        dir_y = math.sin(angle)
        bounces = 0
        max_bounces = 3
        max_distance = 1000
        traveled_distance = 0
        margin = 35

        self.canvas.create_oval(current_x - 3, current_y - 3, current_x + 3, current_y + 3,
                               fill='#FFD700', outline='#FFFFFF', width=1, tags='cue')

        while bounces < max_bounces and traveled_distance < max_distance:
            next_x = current_x + dir_x * 10
            next_y = current_y + dir_y * 10

            # Check for cushion collisions
            hit_wall = False
            if next_x - self.BALL_RADIUS < margin:
                next_x = margin + self.BALL_RADIUS
                dir_x = -dir_x
                hit_wall = True
                bounces += 1
            elif next_x + self.BALL_RADIUS > self.TABLE_WIDTH - margin:
                next_x = self.TABLE_WIDTH - margin - self.BALL_RADIUS
                dir_x = -dir_x
                hit_wall = True
                bounces += 1

            if next_y - self.BALL_RADIUS < margin:
                next_y = margin + self.BALL_RADIUS
                dir_y = -dir_y
                hit_wall = True
                bounces += 1
            elif next_y + self.BALL_RADIUS > self.TABLE_HEIGHT - margin:
                next_y = self.TABLE_HEIGHT - margin - self.BALL_RADIUS
                dir_y = -dir_y
                hit_wall = True
                bounces += 1

            # Check for pocket hits
            near_pocket = False
            for pocket in self.POCKETS:
                dx = next_x - pocket['x']
                dy = next_y - pocket['y']
                if math.sqrt(dx*dx + dy*dy) < self.POCKET_RADIUS:
                    self.canvas.create_line(current_x, current_y, pocket['x'], pocket['y'],
                                           fill='#FF6B6B', width=2, dash=(3, 3), tags='cue')
                    near_pocket = True
                    break

            if near_pocket:
                break

            self.canvas.create_line(current_x, current_y, next_x, next_y,
                                   fill='#FFD700', width=2, tags='cue')

            if hit_wall:
                self.canvas.create_oval(next_x - 4, next_y - 4, next_x + 4, next_y + 4,
                                       fill='#FF6B6B', outline='#FFFFFF', width=1, tags='cue')

            current_x, current_y = next_x, next_y
            traveled_distance += 10

    def update_balls(self):
        # Update ball positions and handle physics
        for ball in self.balls:
            if ball['pocketed']:
                continue

            # Apply friction
            ball['vx'] *= self.FRICTION
            ball['vy'] *= self.FRICTION

            # Stop very slow balls
            if abs(ball['vx']) < 0.01:
                ball['vx'] = 0
            if abs(ball['vy']) < 0.01:
                ball['vy'] = 0

            # Update position
            ball['x'] += ball['vx']
            ball['y'] += ball['vy']

            # Handle cushion bounces
            margin = 35
            if ball['x'] - self.BALL_RADIUS < margin:
                ball['x'] = margin + self.BALL_RADIUS
                ball['vx'] = -ball['vx'] * self.CUSHION_BOUNCE
            elif ball['x'] + self.BALL_RADIUS > self.TABLE_WIDTH - margin:
                ball['x'] = self.TABLE_WIDTH - margin - self.BALL_RADIUS
                ball['vx'] = -ball['vx'] * self.CUSHION_BOUNCE

            if ball['y'] - self.BALL_RADIUS < margin:
                ball['y'] = margin + self.BALL_RADIUS
                ball['vy'] = -ball['vy'] * self.CUSHION_BOUNCE
            elif ball['y'] + self.BALL_RADIUS > self.TABLE_HEIGHT - margin:
                ball['y'] = self.TABLE_HEIGHT - margin - self.BALL_RADIUS
                ball['vy'] = -ball['vy'] * self.CUSHION_BOUNCE

        # Handle ball-to-ball collisions
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                ball1 = self.balls[i]
                ball2 = self.balls[j]

                if ball1['pocketed'] or ball2['pocketed']:
                    continue

                dx = ball2['x'] - ball1['x']
                dy = ball2['y'] - ball1['y']
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < self.BALL_RADIUS * 2:
                    # Collision response
                    angle = math.atan2(dy, dx)
                    sin_angle = math.sin(angle)
                    cos_angle = math.cos(angle)

                    # Rotate velocities
                    vx1 = ball1['vx'] * cos_angle + ball1['vy'] * sin_angle
                    vy1 = ball1['vy'] * cos_angle - ball1['vx'] * sin_angle
                    vx2 = ball2['vx'] * cos_angle + ball2['vy'] * sin_angle
                    vy2 = ball2['vy'] * cos_angle - ball2['vx'] * sin_angle

                    # Exchange x velocities
                    final_vx1 = vx2
                    final_vx2 = vx1

                    # Rotate back
                    ball1['vx'] = final_vx1 * cos_angle - vy1 * sin_angle
                    ball1['vy'] = vy1 * cos_angle + final_vx1 * sin_angle
                    ball2['vx'] = final_vx2 * cos_angle - vy2 * sin_angle
                    ball2['vy'] = vy2 * cos_angle + final_vx2 * sin_angle

                    # Separate balls
                    overlap = self.BALL_RADIUS * 2 - distance
                    separation_x = (overlap / 2) * cos_angle
                    separation_y = (overlap / 2) * sin_angle
                    ball1['x'] -= separation_x
                    ball1['y'] -= separation_y
                    ball2['x'] += separation_x
                    ball2['y'] += separation_y

        # Check for pocketing
        for ball in self.balls:
            if ball['pocketed']:
                continue

            for pocket in self.POCKETS:
                dx = ball['x'] - pocket['x']
                dy = ball['y'] - pocket['y']
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < self.POCKET_RADIUS - self.BALL_RADIUS / 2:
                    if ball['number'] == 0:  # Cue ball
                        # Return cue ball to center of table
                        ball['x'] = self.TABLE_WIDTH / 2
                        ball['y'] = self.TABLE_HEIGHT / 2
                        ball['vx'] = 0
                        ball['vy'] = 0
                        # Switch turns as penalty for pocketing cue ball
                        self.current_player = 2 if self.current_player == 1 else 1
                    else:
                        ball['pocketed'] = True
                        ball['vx'] = 0
                        ball['vy'] = 0

                        # Handle ball assignment in 8-ball
                        if self.game_mode == '8ball' and not self.balls_assigned:
                            if ball['type'] == 'solid':
                                self.player1_balls = ['solid']
                                self.player2_balls = ['stripe']
                            elif ball['type'] == 'stripe':
                                self.player1_balls = ['stripe']
                                self.player2_balls = ['solid']
                            self.balls_assigned = True
                    break

    def balls_moving(self):
        return any(not b['pocketed'] and (abs(b['vx']) > 0.01 or abs(b['vy']) > 0.01)
                  for b in self.balls)

    def handle_mouse_move(self, event):
        self.cue_position = {'x': event.x, 'y': event.y}

        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if cue_ball and not self.balls_moving():
            if not self.is_dragging:
                # Always set aiming angle based on mouse position relative to cue ball
                dx = event.x - cue_ball['x']
                dy = event.y - cue_ball['y']
                self.aim_angle = math.atan2(dy, dx)

            elif self.is_dragging:
                # When dragging, calculate power based on distance from drag start
                dx = event.x - self.drag_start['x']
                dy = event.y - self.drag_start['y']
                drag_distance = math.sqrt(dx * dx + dy * dy)

                # Power increases as you drag away from the starting point
                self.power = min(100, drag_distance * 0.5)
                self.cue_pull_distance = 30 + self.power * 2
                self.power_label.config(text=f"Power: {int(self.power)}%")

    def handle_mouse_down(self, event):
        if self.balls_moving():
            return

        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if not cue_ball:
            return

        # Allow clicking anywhere on the table to start aiming
        self.is_dragging = True
        self.drag_start = {'x': event.x, 'y': event.y}
        self.locked_angle = self.aim_angle  # Lock the current aiming angle
        self.cue_pull_distance = 30
        self.power = 0
        self.canvas.config(cursor='crosshair')
        self.power_label.config(text="Power: 0%")

    def handle_mouse_up(self, event):
        if not self.is_dragging or self.balls_moving():
            return

        cue_ball = next((b for b in self.balls if b['number'] == 0 and not b['pocketed']), None)
        if cue_ball and self.power > 1:  # Lower threshold for shooting
            speed = self.power * 0.15  # Adjusted speed multiplier
            cue_ball['vx'] = math.cos(self.locked_angle) * speed
            cue_ball['vy'] = math.sin(self.locked_angle) * speed

        self.is_dragging = False
        self.locked_angle = None
        self.cue_pull_distance = 0
        self.power = 0
        self.power_label.config(text="Power: 0%")
        self.canvas.config(cursor='crosshair')

    def update_ui(self):
        # Update player turn
        player_text = f"Player {self.current_player}'s Turn"
        if self.game_mode == 'ai':
            player_text = f"AI Player {self.current_player}'s Turn"
        elif self.balls_assigned and self.game_mode == '8ball':
            ball_type = self.player1_balls[0] if self.current_player == 1 else self.player2_balls[0]
            player_text += f" ({ball_type})"

        try:
            if hasattr(self, 'player_label') and self.player_label.winfo_exists():
                self.player_label.config(text=player_text)
        except:
            pass  # Label doesn't exist yet or was destroyed

        if self.game_mode == '8ball':
            self.calculate_win_probability()

            # Update player 1 info
            p1_type = "Not assigned"
            if self.balls_assigned:
                p1_type = "Solids (1-7)" if self.player1_balls[0] == 'solid' else "Stripes (9-15)"

            self.p1_type_label.config(text=p1_type)

            # Clear and redraw player 1 balls
            for widget in self.p1_balls_frame.winfo_children():
                widget.destroy()

            if self.balls_assigned:
                balls_to_show = [b for b in self.balls if
                               ((self.player1_balls[0] == 'solid' and b['type'] == 'solid') or
                                (self.player1_balls[0] == 'stripe' and b['type'] == 'stripe')) and
                               not b['pocketed']]

                for ball in balls_to_show:
                    ball_canvas = tk.Canvas(self.p1_balls_frame, width=24, height=24,
                                          highlightthickness=0)
                    ball_canvas.pack(side=tk.LEFT, padx=1)
                    ball_canvas.create_oval(2, 2, 22, 22, fill=ball['color'],
                                          outline='#FFFFFF', width=1)
                    text_color = '#FFFFFF' if ball['number'] <= 8 else '#000000'
                    ball_canvas.create_text(12, 12, text=str(ball['number']),
                                          fill=text_color, font=('Arial', 8, 'bold'))

            self.p1_prob_label.config(text=f"Win Probability: {self.win_probability['p1']}%")
            self.p1_prob_bar.config(value=self.win_probability['p1'])

            # Update player 2 info
            p2_type = "Not assigned"
            if self.balls_assigned:
                p2_type = "Solids (1-7)" if self.player2_balls[0] == 'solid' else "Stripes (9-15)"

            self.p2_type_label.config(text=p2_type)

            # Clear and redraw player 2 balls
            for widget in self.p2_balls_frame.winfo_children():
                widget.destroy()

            if self.balls_assigned:
                balls_to_show = [b for b in self.balls if
                               ((self.player2_balls[0] == 'solid' and b['type'] == 'solid') or
                                (self.player2_balls[0] == 'stripe' and b['type'] == 'stripe')) and
                               not b['pocketed']]

                for ball in balls_to_show:
                    ball_canvas = tk.Canvas(self.p2_balls_frame, width=24, height=24,
                                          highlightthickness=0)
                    ball_canvas.pack(side=tk.LEFT, padx=1)
                    ball_canvas.create_oval(2, 2, 22, 22, fill=ball['color'],
                                          outline='#FFFFFF', width=1)
                    text_color = '#FFFFFF' if ball['number'] <= 8 else '#000000'
                    ball_canvas.create_text(12, 12, text=str(ball['number']),
                                          fill=text_color, font=('Arial', 8, 'bold'))

            self.p2_prob_label.config(text=f"Win Probability: {self.win_probability['p2']}%")
            self.p2_prob_bar.config(value=self.win_probability['p2'])

        elif self.game_mode == '9ball':
            # Update remaining balls
            for widget in self.nine_balls_frame.winfo_children():
                widget.destroy()

            remaining_balls = sorted([b for b in self.balls if b['type'] == 'numbered' and not b['pocketed']],
                                   key=lambda x: x['number'])

            for ball in remaining_balls:
                ball_canvas = tk.Canvas(self.nine_balls_frame, width=32, height=32,
                                      highlightthickness=0)
                ball_canvas.pack(side=tk.LEFT, padx=2)
                ball_canvas.create_oval(2, 2, 30, 30, fill=ball['color'],
                                      outline='#FFFFFF', width=2)
                text_color = '#FFFFFF' if ball['number'] != 9 else '#000000'
                ball_canvas.create_text(16, 16, text=str(ball['number']),
                                      fill=text_color, font=('Arial', 10, 'bold'))

            next_ball = remaining_balls[0]['number'] if remaining_balls else 'None'
            self.next_ball_label.config(text=f"Next ball to hit: {next_ball}")

def main():
    root = tk.Tk()
    app = PoolGame(root)
    root.mainloop()

if __name__ == "__main__":
    main()
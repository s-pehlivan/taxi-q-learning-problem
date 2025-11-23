import numpy as np
import gymnasium as gym
from gymnasium import spaces

# ACTIONS
SOUTH = 0
NORTH = 1
EAST = 2
WEST = 3
PICK_UP = 4
DROP_OFF = 5

class TaxiEnvironment(gym.Env):
    metadata = {
        "render_modes": ["rgb_array", "human"],
        "render_fps": 4
    }

    def __init__(self, render_mode=None):
        self.num_rows = 6
        self.num_columns = 6
        self.locs = [(0,0), (0,5), (4,0), (5,4), (2,3)]
        
        self.vertical_walls = [
            (0,2), (1,2),
            (3,1), (4,1),
            (5,3)
        ]
        num_states = 6*6*6*5
        num_actions = 6
        self.action_space = spaces.Discrete(num_actions)
        self.observation_space = spaces.Discrete(num_states)
        self.render_mode = render_mode
        
        self.cell_size = 32 

    def encode(self, taxi_row, taxi_col, pass_loc, dest_idx):
        i = taxi_row
        i *= 6
        i += taxi_col
        i *= 6
        i += pass_loc
        i *= 5
        i += dest_idx
        return i
    
    def decode(self, i):
        out = []
        out.append(i % 5)
        i = i // 5
        out.append(i % 6)
        i = i // 6
        out.append(i % 6)
        i = i // 6
        out.append(i)
        assert 0 <= i < 6
        return reversed(out)

    def action_mask(self, state):
        mask = np.zeros(6, dtype=np.int8)
        taxi_row, taxi_col, pass_loc, dest_idx = self.decode(state)
        # Movement
        if taxi_row < self.num_rows - 1: mask[SOUTH] = 1
        if taxi_row > 0: mask[NORTH] = 1
        # East (Check wall to right)
        if taxi_col < self.num_columns - 1 and (taxi_row, taxi_col) not in self.vertical_walls:
            mask[EAST] = 1    
        # West (Check wall to left)
        if taxi_col > 0 and (taxi_row, taxi_col -1) not in self.vertical_walls:
            mask[WEST] = 1     
        # Interaction
        if pass_loc < 5 and (taxi_row, taxi_col) == self.locs[pass_loc]:
            mask[PICK_UP] = 1      
        if pass_loc == 5 and (taxi_row, taxi_col) == self.locs[dest_idx]:
            mask[DROP_OFF] = 1
        return mask

    def step(self, a):
        row, col, pass_idx, dest_idx = self.decode(self.s)
        new_row, new_col, new_pass_idx = row, col, pass_idx
        reward = -1
        terminated = False
        taxi_loc = (row, col)

        if a == SOUTH:
            new_row = min(row + 1, self.num_rows -1)
        elif a == NORTH:
            new_row = max(row - 1, 0)
        elif a == EAST:
            if (row, col) in self.vertical_walls:
                new_col = col 
            else:
                new_col = min(col + 1, self.num_columns - 1)
        elif a == WEST:
            if (row, col - 1) in self.vertical_walls:
                new_col = col
            else:
                new_col = max(col - 1, 0)
        elif a == PICK_UP:
            if pass_idx < len(self.locs) and taxi_loc == self.locs[pass_idx]:
                new_pass_idx = len(self.locs)
                reward = 10
            else:
                reward = -10
        elif a == DROP_OFF:
            if (taxi_loc == self.locs[dest_idx]) and pass_idx == len(self.locs):
                new_pass_idx = dest_idx
                terminated = True
                reward = 20
            else:
                reward = -10

        self.s = self.encode(new_row, new_col, new_pass_idx, dest_idx)
        self.lastaction = a
            
        return(int(self.s), reward, terminated, False, {"action_mask": self.action_mask(self.s)})

    def reset(self, *, seed = None, options =  None ):
        super().reset(seed=seed)
        dest_idx = self.np_random.integers(len(self.locs))
        pass_idx = self.np_random.integers(len(self.locs))
        while pass_idx == dest_idx:
            pass_idx = self.np_random.integers(len(self.locs))
        pass_loc = self.locs[pass_idx]
        dest_loc = self.locs[dest_idx] 
        while True:
            taxi_row = self.np_random.integers(self.num_rows)
            taxi_col = self.np_random.integers(self.num_columns)
            if (taxi_row, taxi_col) != pass_loc and (taxi_row, taxi_col) != dest_loc:
                break
        self.s = self.encode(taxi_row, taxi_col, pass_idx, dest_idx)
        self.lastaction = None
        return int(self.s), {"prob": 1.0, "action_mask": self.action_mask(self.s)}
    
    def render(self):
        grid = np.zeros((self.num_rows * self.cell_size, self.num_columns * self.cell_size, 3), dtype=np.uint8) + 255
        taxi_row, taxi_col, pass_idx, dest_idx = self.decode(self.s)
        def color_cell(r, c, color):
            y_start = r * self.cell_size
            y_end = (r + 1) * self.cell_size
            x_start = c * self.cell_size
            x_end = (c + 1) * self.cell_size
            grid[y_start:y_end, x_start:x_end] = color

        dr, dc = self.locs[dest_idx]
        color_cell(dr, dc, [255, 0, 255])
        if pass_idx < 5:
            pr, pc = self.locs[pass_idx]
            color_cell(pr, pc, [0, 0, 255])
        color_cell(taxi_row, taxi_col, [255, 204, 0])
        if pass_idx == 5:
             color_cell(taxi_row, taxi_col, [0, 255, 0])
        for (r, c) in self.vertical_walls:
            x = (c + 1) * self.cell_size
            y_start = r * self.cell_size
            y_end = (r + 1) * self.cell_size
            grid[y_start:y_end, x-2:x+2] = [0, 0, 0]
        for r in range(self.num_rows + 1):
            y = r * self.cell_size
            if y < grid.shape[0]:
                grid[y:y+1, :] = [200, 200, 200]
        for c in range(self.num_columns + 1):
            x = c * self.cell_size
            if x < grid.shape[1]:
                grid[:, x:x+1] = [200, 200, 200]

        return grid
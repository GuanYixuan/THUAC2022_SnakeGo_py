import assess;
from adk import *;

# written by lbr

dx = [1, 0, -1, 0]
dy = [0, 1, 0, -1]
INF = 100000000;
# constants

SPLIT_LIMIT = 10
SEARCH_LIMIT = 100
# tunable parameters


class AI:
    ctx : Context = None;
    snake : Snake = None;
    assess : "assess.assess";
    wanted_item : "dict[int,Item]" = dict();#(蛇id:物品)
    order : "dict[int,tuple[int,int]]" = dict();

    def __init__(self):
        self.ctx = None
        self.snake = None
        self.order = dict()

    def closest_food_strategy(self):
        """
        Search for the closest food and to go that direction, if legal.

        :return: the chosen direction
        """
        def calc_dist(x1 : int, y1 : int, x2 : int, y2 : int) -> "tuple[int,int]":
            """
            Calculate the Manhattan distance between snake head and item.
            And find the possible direction to the item, at most 2.

            :return: (dist, possible_direction)
            """
            pos = []
            if x1 > x2:
                pos.append(0)
            if x1 < x2:
                pos.append(2)
            if y1 > y2:
                pos.append(1)
            if y1 < y2:
                pos.append(3)
            return abs(x1 - x2) + abs(y1 - y2), pos

        valid = []
        for i in range(4):
            if self.check(i):
                valid.append(i)
        if len(valid) == 0:
            if self.snake.get_len() > 1 and self.snake.coor_list[0][0] + dx[0] == self.snake.coor_list[1][0] and self.snake.coor_list[0][1] + dy[0] == self.snake.coor_list[1][1]:
                return 1
            return 0
        # calculate the legal moves without concerning the food

        coor = self.snake.coor_list
        dist, val = INF, []
        for item in self.ctx.game_map.item_list:
            if item.type != 0:
                continue
            # search food only

            if item.time > self.ctx.turn + SEARCH_LIMIT or item.time + item.param < self.ctx.turn:
                continue
            # search valid food only

            d, pos = calc_dist(item.x, item.y, coor[0][0], coor[0][1])
            pos = [i for i in pos if i in valid]
            # use legal move only

            if len(pos) > 0 and d < dist and \
                    d + self.ctx.turn <= item.time + item.param <= d + self.ctx.turn + SPLIT_LIMIT / 2:
                dist, val = d, pos
            # search reachable food only
            # not that the span of a snake is at least SPLIT_LIMIT / 2

        # chose the closest reachable food and use legal move

        if len(val) == 0:
            val = valid
        i = random.randint(0, len(val) - 1)
        # randomly chose one if multiple available

        return val[i]

    def find_food(self) -> Item:#找一个食物
        best = [1e8,-1,-1];#[dist,Item,ind]
        for ind,food in enumerate(self.ctx.game_map.item_list):
            if food.type != 0 or food.gotten_time != -1 or self.ctx.turn >= food.time + 16:#只找还没被吃的食物
                continue;
            dist = self.assess.dist_map[food.x][food.y];
            if dist == -1:
                continue;
            if food.time - self.ctx.turn >= 25 or self.ctx.turn + dist > food.time+7:#不找那么远（时间/空间上）的食物
                continue;
            if self.ctx.turn + dist < food.time - 10:#不找太近的食物
                continue;

            if dist < best[0]:
                best = [dist,food,ind];
        if best[2] == -1:
            return -1;
        return best[1];

    def eat_strategy(self) -> int:
        if self.wanted_item.get(self.snake.id,-1) == -1:
            self.wanted_item[self.snake.id] = self.find_food();
            if self.wanted_item[self.snake.id] == -1:#没东西可吃，还没写
                return self.assess.random_step();
        
        reget_food = False;
        food = self.wanted_item[self.snake.id];
        if food.gotten_time != -1 or self.ctx.turn >= food.time + 16:
            reget_food = True;
        if self.assess.check_item_captured(food):
            reget_food = True;
        
        if reget_food:
            self.wanted_item[self.snake.id] = self.find_food();
            if self.wanted_item[self.snake.id] == -1:#没东西可吃，还没写
                return self.assess.random_step();
        
        op = self.assess.find_first((food.x,food.y));
        return op;

    def judge(self, snake : Snake, ctx : Context):
        """
        :param snake: current snake
        :param ctx: current context
        :return: the decision
        """
        self.ctx,self.snake = ctx,snake;
        self.assess = assess.assess(ctx,snake.id);
        self.assess.find_path();
        return self.eat_strategy()+1;
        


def run():
    """
    This function maintains the context, i.e. simulating the game.
    It is not necessary to understand this function for you to write an AI.
    """
    c = Client()
    # game config
    (length, width, max_round, player) = c.fetch_data()
    config = GameConfig(width=width, length=length, max_round=max_round)
    ctx = Context(config=config)
    current_player = 0

    logging.info('Assigned player %d', player)

    # read items
    item_list = c.fetch_data()
    ctx.game_map = Map(item_list, config=config)
    controller = Controller(ctx)
    # read & write operations
    playing = True
    ai = AI()
    while playing:
        if controller.ctx.turn > max_round:
            res = c.fetch_data()
            sys.stderr.write(str(res[1:]))
            break
        if current_player == 0:
            controller.round_preprocess()
        controller.round_init()
        if player == current_player:  # Your Turn
            while controller.next_snake != -1:
                current_snake = controller.current_snake_list[controller.next_snake][0]
                op = ai.judge(current_snake, controller.ctx)  # TODO: Complete the Judge Function
                logging.debug(str(op))
                if not controller.apply(op):
                    pass
                    # raise RuntimeError("Illegal Action!!!")
                c.send_data(op)
                res = c.fetch_data()
                if res[0] == -1:
                    playing = False
                    sys.stderr.write(str(res[1:]))
                    break
            controller.next_player()
        else:
            while True:
                if controller.next_snake == -1:
                    controller.next_player()
                    break
                op = c.fetch_data()
                if op[0] == -1:
                    playing = False
                    sys.stderr.write(str(op[1:]))
                    break
                controller.apply(op[0])
        current_player = 1 - current_player
    while True:
        pass

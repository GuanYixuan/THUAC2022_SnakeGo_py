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
    item_alloc : "list[int]";
    wanted_item : "dict[int,Item]" = dict();#(蛇id:物品)
    order : "dict[int,tuple[int,int]]" = dict();

    def __init__(self):
        self.ctx = None
        self.snake = None
        self.order = dict();
        self.item_alloc = [-1 for i in range(512)];

    def try_split(self) -> bool:
        if self.snake.get_len() > 18 and self.ctx.get_snake_count(self.ctx.current_player) < 4:
            logging.debug("主动分裂，长度%d" % self.snake.get_len());
            return True;
        return False;

    def try_shoot(self) -> bool:
        if not self.assess.can_shoot():
            return False;
        ass = self.assess.ray_trace_self();
        if ass[1]-ass[0] >= 2:
            logging.debug("发射激光，击毁(%d,%d)" % ass);
            return True;
        return False;

    def find_tgt(self) -> Item:#找一个东西
        best = [1e8,-1,-1];#[dist,Item,id]
        for ind,food in enumerate(self.ctx.game_map.item_list):
            if food.type != 0 or food.gotten_time != -1 or self.ctx.turn >= food.time + 16:#只找还没被吃的食物
                continue;
            dist = self.assess.dist_map[food.x][food.y];
            if dist == -1:
                continue;
            if food.time - self.ctx.turn >= 25 or self.ctx.turn + dist > food.time+16:#不找那么远（时间/空间上）的食物
                continue;
            if self.item_alloc[food.id] != -1 or self.assess.check_item_captured_team(food) != -1:#不争抢
                continue;
            # if self.ctx.turn + dist < food.time - 7:#不找太近的食物
            #     continue;

            if dist < best[0]:
                best = [dist,food,food.id];
        if best[2] != -1:
            self.item_alloc[best[2]] = self.snake.id;
            return best[1];
        
        best = [1e8,-1,-1];#[dist,Item,id]
        for ind,laser in enumerate(self.ctx.game_map.item_list):
            if laser.type != 2 or laser.gotten_time != -1 or self.ctx.turn >= laser.time + 16:#只找还没被吃的激光
                continue;
            dist = self.assess.dist_map[laser.x][laser.y];
            if dist == -1:
                continue;
            if laser.time - self.ctx.turn >= 25 or self.ctx.turn + dist > laser.time+16:#不找那么远（时间/空间上）的食物
                continue;
            if self.item_alloc[laser.id] != -1 or self.assess.check_item_captured_team(laser) != -1:#不争抢
                continue;
            if dist < best[0]:
                best = [dist,laser,laser.id];
        if best[2] != -1:
            self.item_alloc[best[2]] = self.snake.id;
            return best[1];
        return -1;

    def eat_strategy(self) -> int:
        if self.wanted_item.get(self.snake.id,-1) == -1:
            self.wanted_item[self.snake.id] = self.find_tgt();
            if self.wanted_item[self.snake.id] == -1:#没东西可吃，还没写
                logging.debug("未找到目标");
                return self.assess.random_step();
        
        reget_food = False;
        food = self.wanted_item[self.snake.id];
        if food.gotten_time != -1 or self.ctx.turn >= food.time + 16:
            reget_food = True;
        if self.assess.check_item_captured(food):
            reget_food = True;
        
        if reget_food:
            self.wanted_item[self.snake.id] = self.find_tgt();
            logging.debug("重载目标:%s" % self.wanted_item[self.snake.id]);
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
        form = "%%(levelname)6s 行数%%(lineno)4d turn:%4d 编号:%2d %%(message)s" % (self.ctx.turn,self.snake.id);
        # logging.basicConfig(filename="log.log",level=logging.DEBUG,format=form,force=True);
        logging.basicConfig(stream=sys.stdout,level=logging.DEBUG,format=form,force=True);

        if self.try_shoot():
            return 5;
        if self.try_split():
            return 6;
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
                # logging.debug(str(op))
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

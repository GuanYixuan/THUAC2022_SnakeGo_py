import assess;
from adk import *;

class AI:
    ctx : Context = None;
    snake : Snake = None;
    assess : "assess.assess";
    item_alloc : "list[int]";
    wanted_item : "dict[int,Item]" = dict();#(蛇id:物品)
    order : "dict[int,tuple[int,int]]" = dict();

    __first_mission = 0;

    def __init__(self):
        self.ctx = None
        self.snake = None
        self.order = dict();
        self.item_alloc = [-1 for i in range(512)];

    def try_split(self) -> bool:
        if self.snake.get_len() > 15 and self.ctx.get_snake_count(self.ctx.current_player) < 4 and self.assess.can_split() and self.assess.calc_snk_air(self.snake.coor_list[-1]) >= 2:
            logging.debug("主动分裂，长度%d" % self.snake.get_len());
            return True;
        if self.snake.get_len() > 13 and self.ctx.get_snake_count(self.ctx.current_player) < 3 and self.assess.can_split() and self.assess.calc_snk_air(self.snake.coor_list[-1]) >= 2:
            logging.debug("主动分裂，长度%d" % self.snake.get_len());
            return True;
        if self.snake.get_len() > 11 and self.ctx.get_snake_count(self.ctx.current_player) < 2 and self.assess.can_split() and self.assess.calc_snk_air(self.snake.coor_list[-1]) >= 2:
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
        for ind,item in enumerate(self.ctx.game_map.item_list):
            if item.type != 0 or item.gotten_time != -1 or self.ctx.turn >= item.time + 16:#只找还没被吃的食物
                continue;
            dist = self.assess.dist_map[item.x][item.y];
            if dist == -1:
                continue;
            if item.time - self.ctx.turn >= 20 or self.ctx.turn + dist > item.time+16:#不找那么远（时间/空间上）的食物
                continue;
            if self.item_alloc[item.id] != -1 or self.assess.check_item_captured_team(item) != -1:#不争抢
                continue;
            # if self.ctx.turn + dist < item.time - 7:#不找太近的食物
            #     continue;

            if dist < best[0]:
                best = [dist,item,item.id];
        if best[2] != -1:
            self.item_alloc[best[2]] = self.snake.id;
            return best[1];
        
        best = [1e8,-1,-1];#[dist,Item,id]
        for ind,item in enumerate(self.ctx.game_map.item_list):
            if item.type != 2 or item.gotten_time != -1 or self.ctx.turn >= item.time + 16:#只找还没被吃的激光
                continue;
            dist = self.assess.dist_map[item.x][item.y];
            if dist == -1:
                continue;
            if item.time - self.ctx.turn >= 20 or self.ctx.turn + dist > item.time+16:#不找那么远（时间/空间上）的食物
                continue;
            if self.item_alloc[item.id] != -1 or self.assess.check_item_captured_team(item) != -1:#不争抢
                continue;
            if dist < best[0]:
                best = [dist,item,item.id];
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
        
        reget_item = False;
        item = self.wanted_item[self.snake.id];
        if item.gotten_time != -1 or self.ctx.turn >= item.time + 16:
            reget_item = True;
        if self.assess.check_item_captured_team(item) != -1:
            reget_item = True;
        
        if reget_item:
            self.wanted_item[self.snake.id] = self.find_tgt();
            logging.debug("重载目标:%s" % self.wanted_item[self.snake.id]);
            if not self.__first_mission:
               self. __first_mission = 1;
               if self.assess.can_split():
                   return 6 - 1;
            if self.wanted_item[self.snake.id] == -1:#没东西可吃，还没写
                return self.assess.random_step();

        item = self.wanted_item[self.snake.id];
        op = self.assess.find_first((item.x,item.y));
        return op;

    def judge(self, snake : Snake, ctx : Context):
        """
        :param snake: current snake
        :param ctx: current context
        :return: the decision
        """
        self.ctx,self.snake = ctx,snake;
        
        form = "%%(levelname)6s 行数%%(lineno)4d turn:%4d 编号:%2d %%(message)s" % (self.ctx.turn,self.snake.id);
        # logging.basicConfig(filename="log.log",level=logging.DEBUG,format=form,force=True);
        # logging.basicConfig(stream=sys.stdout,level=logging.DEBUG,format=form,force=True);
        # logging.basicConfig(stream=sys.stderr,level=logging.DEBUG,format=form,force=True);
        logging.basicConfig(stream=sys.stderr,level=logging.CRITICAL,format=form,force=True);

        self.assess = assess.assess(self,ctx,snake.id);

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
        time.sleep(1);
        pass

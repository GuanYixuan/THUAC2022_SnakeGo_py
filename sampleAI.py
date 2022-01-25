import assess;
from adk import *;

class AI:
    ctx : Context;
    snake : Snake;
    assess : "assess.assess";
    item_alloc : "list[int]";
    wanted_item : "dict[int,Item]";#(蛇id:物品)
    order : "dict[int,tuple[int,int]]" = dict();

    __last_turn = -1;

    def __init__(self):
        random.seed(0);
        self.ctx = None;
        self.snake = None;
        self.order = dict();

    def time_control(self):
        pass;
        # if self.ctx.turn == 100:
        #     self.__SLOW_COST_MULT = 4;

    def total_control(self):
        self.time_control();

        self.assess.refresh_all_bfs();
        self.assess.calc_spd_map();
        self.distribute_tgt();

    __APPLE_PARAM_GAIN = 1.5;
    __LASER_AS_APPLE = 1;
    __HAS_LASER_COST = 7;
    __MAX_COST_BOUND = 17;
    __SLOW_COST_MULT = 1;
    def distribute_tgt(self):
        """
        [总控函数]为所有蛇分配目标
        """
        def sort_key(ele):
            return ele[2];
        
        self.wanted_item = dict();
        self.item_alloc = [-1 for i in range(512)];
        tgt_list : "list[tuple[int,Item,float]]" = [];#(snkid,item,cost)

        for _item in self.ctx.game_map.item_list:
            if _item.gotten_time != -1 or self.assess.check_item_captured_team(_item) != -1:#排除已被吃/将被吃
                continue;
            if _item.time - self.ctx.turn > 20:#太过久远，不考虑
                continue;
            
            for _friend in self.ctx.snake_list:
                dst = self.assess.dist_map[_friend.id][_item.x][_item.y];
                if _friend.camp != self.ctx.current_player or dst == -1 or self.ctx.turn + dst >= _item.time + 16:
                    continue;
                fastest = self.assess.tot_spd[_item.x][_item.y];

                if dst - fastest[0] > 5:#抢不过别人就不抢...
                    continue;
                snkid = _friend.id;
                cost = max(dst,_item.time-self.ctx.turn);#max(空间,时间)
                if fastest[1] != _friend.id:
                    cost += self.__SLOW_COST_MULT * (dst - fastest[0]);
                if _item.type == 0:
                    cost -= self.__APPLE_PARAM_GAIN * _item.param;                                                                                       
                else:
                    cost -= self.__APPLE_PARAM_GAIN * self.__LASER_AS_APPLE;
                    cost += self.__HAS_LASER_COST * int(self.assess.has_laser(snkid));
                
                if cost <= self.__MAX_COST_BOUND:
                    tgt_list.append((snkid,_item,cost));
        
        tgt_list.sort(key=sort_key);

        complete_cnt = 0;
        for snkid,_item,cost in tgt_list:
            if complete_cnt >= self.ctx.get_snake_count(self.ctx.current_player):
                break;
            if self.item_alloc[_item.id] != -1 or self.wanted_item.get(snkid,-1) != -1:
                continue;
            logging.debug("目标分配:蛇%2d -> %s 代价%.1f" % (snkid,_item,cost));
            self.item_alloc[_item.id] = snkid;
            self.wanted_item[snkid] = _item;

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

    # __AUTO_BUILD_EFFI_BOUND = 0.95;
    # def try_build(self) -> int:
    #     best = self.assess.get_enclosing_leng();
    #     if best[0] == -1:
    #         return -1;

    #     score = -3;
    #     score = (best[0] - self.snake.get_len() * self.__AUTO_BUILD_EFFI_BOUND) * 3;
    #     score += max(0,-(max(self.assess.safe_score)+5) * 0.2);
    #     score += 2 * int(self.ctx.get_snake_count(self.ctx.current_player) == 4);
    #     if score > 0:
    #         logging.debug("主动圈地: 利用%2d格 score:%.1f" % (best[0],score));
    #         return best[1];
    #     return -1;

    def try_shoot(self) -> bool:
        if not self.assess.can_shoot():
            return False;
        ass = self.assess.ray_trace_self();
        if ass[1]-ass[0] >= 2:
            logging.debug("发射激光，击毁(%d,%d)" % ass);
            return True;
        return False;

    def eat_strategy(self) -> int:
        if self.wanted_item.get(self.snake.id,-1) == -1:
            logging.debug("未分配到目标");
            return self.assess.random_step();

        item = self.wanted_item[self.snake.id];
        op = self.assess.find_first((item.x,item.y));
        return op;

    def judge(self, snake : Snake, ctx : Context):
        self.ctx,self.snake = ctx,snake;
        
        form = "%%(levelname)6s 行数%%(lineno)4d turn:%4d 编号:%2d %%(message)s" % (self.ctx.turn,self.snake.id);
        # logging.basicConfig(filename="log.log",level=logging.DEBUG,format=form,force=True);
        logging.basicConfig(stream=sys.stderr,level=logging.CRITICAL,format=form,force=True);

        self.assess = assess.assess(self,ctx,snake.id);

        if self.__last_turn != self.ctx.turn:
            self.__last_turn = self.ctx.turn;
            self.total_control();

        if self.try_shoot():
            return 5;
        if self.try_split():
            return 6;
        # bu = self.try_build();
        # if bu != -1:
        #     return bu + 1;
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

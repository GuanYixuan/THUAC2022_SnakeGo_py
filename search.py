from adk import *
import copy;

ACT = ((1,0),(0,1),(-1,0),(0,-1));
# constants

# class processor:
#     """
#     帮助维护node的状态
#     为了效率总得要写的...
#     会把round_preprocess,move,apply之类的都抢过来
#     """

#     def __init__(self) -> None:
#         pass;
    
class node:
    """
    搜索树中的node类，目前跟controller是一样的
    用ctx中的snk_cnt_adj属性来处理有关蛇数量的麻烦事
    """
    ctx : Context;
    map : Map;
    player : int;
    next_snake : int;
    current_snake_list : "list[tuple[Snake,bool]]";
    
    def __init__(self, ctrl: Controller):
        self.ctx = copy.deepcopy(ctrl.ctx);
        self.map = self.ctx.get_map()
        self.player = ctrl.player;
        self.next_snake = ctrl.next_snake;
        self.current_snake_list = copy.deepcopy(ctrl.current_snake_list);

    def round_preprocess(self):
        tmp_item_list = self.map.item_list.copy()
        for item in tmp_item_list:
            if item.time <= self.ctx.turn - ITEM_EXPIRE_TIME and item.gotten_time == -1:
                self.map.delete_map_item(item.id)
            if item.time == self.ctx.turn:
                snake = self.map.snake_map[item.x][item.y]
                if snake >= 0:
                    item.gotten_time = self.ctx.turn
                    self.ctx.get_snake(snake).add_item(item)
                    self.ctx.game_map.item_list.remove(item)
                else:
                    self.map.item_map[item.x][item.y] = item.id
        for snake in self.ctx.snake_list:
            for item in snake.item_list:
                if self.ctx.turn - item.gotten_time > item.param:
                    snake.delete_item(item.id)
        return

    def find_next_snake(self):
        for idx, (snake, dead) in enumerate(self.current_snake_list[self.next_snake + 1::]):
            if snake.camp == self.player and not dead:
                self.next_snake = self.next_snake + 1 + idx
                return
        self.next_snake = -1

    def next_player(self):
        self.player = self.ctx.current_player = 1 - self.ctx.current_player
        if self.player == 0:
            self.ctx.turn = 1 + self.ctx.turn
        self.next_snake = -1

    def delete_snake(self, s_id: int):
        self.ctx.delete_snake(s_id)
        temp = self.current_snake_list
        self.current_snake_list = [(i, i.id == s_id or dead) for (i, dead) in temp]

    def round_init(self):
        self.current_snake_list = [(i, False) for i in self.ctx.snake_list]
        self.find_next_snake()

    # 回合开始时controller.round_preprocess()
    # 每个玩家操作前controller.round_init()
    # 操作controller.apply(op)
    # 每个玩家操作完成后controller.next_player()
    def apply(self, op: int):
        if not self.apply_single(self.next_snake, op):
            return False
        self.find_next_snake();

        while self.next_snake == -1:
            self.next_player();
            if self.ctx.current_player == 0:
                self.round_preprocess();
            self.round_init();

            if len(self.ctx.snake_list) == 0:
                break;
        return True

    def calc(self, coor: "list[tuple[int,int]]") -> "list[tuple[int,int]]":
        g = Graph(coor, self.map.length, self.map.width)
        return g.calc()

    def apply_single(self, snake: int, op: int):
        s, _ = self.current_snake_list[snake]
        idx_in_ctx = -1
        for idx, t in enumerate(self.ctx.snake_list):
            if s.id == t.id:
                idx_in_ctx = idx
        assert (idx_in_ctx != -1)
        if op <= 4:  # move
            return self.move(idx_in_ctx, op - 1)
        elif op == 5:
            if len(self.ctx.snake_list[idx_in_ctx].item_list) == 0:
                return False
            elif self.ctx.snake_list[idx_in_ctx].item_list[0].type == 2:
                return self.fire(idx_in_ctx)
            else:
                return False
        elif op == 6:
            return self.split(idx_in_ctx)
        else:
            return False

    def get_item(self, snake: Snake, item_id: int) -> None:
        item = self.map.get_map_item(item_id)
        item.gotten_time = self.ctx.turn
        if item.type == 0:
            snake.length_bank += item.param
        else:
            snake.add_item(item)
        self.map.delete_map_item(item_id)

    def move(self, idx_in_ctx: int, direction: int):
        dx = [1, 0, -1, 0]
        dy = [0, 1, 0, -1]
        snake = self.ctx.snake_list[idx_in_ctx]
        snake_id = snake.id
        auto_grow = self.ctx.turn <= self.ctx.auto_growth_round and snake.camp == snake.id
        coor = snake.coor_list
        x, y = coor[0][0] + dx[direction], coor[0][1] + dy[direction]
        if len(coor) == 1:
            new_coor = [(x, y)]
        else:
            new_coor = [(x, y)] + coor[:-1]

        if (len(coor) > 2 or (len(coor) == 2 and (auto_grow or snake.length_bank))) and (x, y) == coor[1]:
            return False

        self.ctx.delete_snake(snake_id)

        if x < 0 or x >= self.ctx.game_map.length or y < 0 or y >= self.ctx.game_map.width \
                or self.map.wall_map[x][y] != -1:
            self.delete_snake(snake_id)
            return True

        if auto_grow:
            new_coor = new_coor + [coor[-1]]
        elif snake.length_bank:
            snake.length_bank = snake.length_bank - 1
            new_coor = new_coor + [coor[-1]]
        snake.coor_list = new_coor

        if self.map.item_map[x][y] != -1:
            self.get_item(snake, self.map.item_map[x][y])

        for i in range(len(new_coor)):
            if i == 0:
                continue
            if x == new_coor[i][0] and y == new_coor[i][1]:
                dead_snake = [snake_id]
                solid_coor = new_coor[:i]
                extra_solid = self.calc(solid_coor)
                for coor in new_coor[i:]:
                    if coor in extra_solid:
                        solid_coor.append(coor)
                        extra_solid.remove(coor)
                tmp_solid = extra_solid.copy()
                for coor in tmp_solid:
                    if self.map.snake_map[coor[0]][coor[1]] != -1:
                        dead_snake.append(self.map.snake_map[coor[0]][coor[1]])
                        self.delete_snake(dead_snake[-1])
                self.map.set_wall(solid_coor, self.player, 1)
                self.map.set_wall(extra_solid, self.player, 1)
                self.delete_snake(snake_id)
                return True

        if self.map.snake_map[x][y] != -1:
            self.delete_snake(snake_id)
            return True

        self.ctx.add_snake(snake, idx_in_ctx)
        return True

    def split(self, idx_in_ctx: int):
        def generate(pos, its, player, length_bank, index) -> int:
            ret = Snake(pos, its, player, -1)
            ret.length_bank = length_bank
            self.ctx.add_snake(ret, index)
            return ret.id

        snake = self.ctx.snake_list[idx_in_ctx]
        coor = snake.coor_list
        items = snake.item_list

        if self.ctx.get_snake_count(snake.camp) >= 4:
            return False

        if len(coor) <= 1:
            return False

        head = coor[:(len(coor) + 1) // 2]
        tail = coor[(len(coor) + 1) // 2:]
        tail = tail[::-1]

        h_item = []
        t_item = []

        for item in items:
            if item.type == 0:
                t_item.append(item)
            elif item.type == 1:
                continue
            else:
                h_item.append(item)

        snake.coor_list = head
        snake.item_list = h_item
        generate(tail, t_item, self.player, snake.length_bank, idx_in_ctx + 1)
        snake.length_bank = 0
        return True

    def fire(self, idx_in_ctx: int):
        snake = self.ctx.snake_list[idx_in_ctx]
        coor = snake.coor_list

        if len(coor) <= 1:
            return False

        snake.item_list.pop(0)
        x1, y1 = coor[0]
        x2, y2 = coor[1]
        dx, dy = x1 - x2, y1 - y2
        walls = []

        while self.map.length > x1 + dx >= 0 and self.map.width > y1 + dy >= 0:
            x1, y1 = (x1 + dx, y1 + dy)
            walls = [(x1, y1)] + walls

        self.map.set_wall(walls, -1, -1)
        return True

class search:
    """
    局部搜索模块
    【被迫考虑上了物品的掉落】
    """
    node_raw : node;
    camp : int;
    snkid : int;
    value_func : "function";
    max_turn : int;
    end_turn : int;

    debug_search_cnt : int = 0;

    def __init__(self,controller : Controller,snklst : "list[int]",snkid : int):
        self.snkid = snkid;
        self.node_raw = node(controller);
        self.camp = self.node_raw.ctx.current_player;

        remov_list = [];
        for _snake in self.node_raw.ctx.snake_list:
            remov_list.append(_snake.id);
        for i in range(len(remov_list)-1,-1,-1):
            if snklst.count(remov_list[i]) != 0:
                del remov_list[i];
        # print(remov_list);
        
        self.node_raw.ctx.snk_cnt_adj = [0,0];#维护蛇的数量
        for _id in remov_list:
            if self.node_raw.ctx.get_snake(_id) == 0:
                self.node_raw.ctx.snk_cnt_adj[0] += 1;
            else:
                self.node_raw.ctx.snk_cnt_adj[1] += 1;
            self.node_raw.delete_snake(_id);
        # print(list(map(lambda x: x.id,self.node_raw.ctx.snake_list)));

    def setup_search(self,max_turn : int,func : "function"):
        self.max_turn = max_turn;
        self.end_turn = self.node_raw.ctx.turn + self.max_turn;
        self.value_func = func;
        print("max_turn:%d" % self.end_turn);
    
    stack : "list[node]" = [];
    def search(self):
        self.stack.append(copy.deepcopy(self.node_raw));
        self.search_dfs(0);
        print("search_cnt:",self.debug_search_cnt);

    def search_dfs(self,stack_ind : int) -> "tuple[float,int]":#stack_ind同step
        """
        局部搜索，采用模拟递归的方式进行
        仅当stack_ind为0时返回(最大val,走法)
        否则返回一个float,表示对应的最大/最小值
        """
        now = self.stack[stack_ind];
        # print("dep:%d turn:%d nxt:%d" % (stack_ind,now.ctx.turn,now.next_snake));
        if stack_ind == 0:
            ans = [-1,-1];
        else:
            ans = -1;
        
        max_layer = True;#若max_layer == True，返回搜到的最大值，否则返回最小值
        
        def comp(val : "tuple[float,int]"):
            nonlocal ans,max_layer;
            if stack_ind == 0:
                if val[1] == -1:
                    return;
                
                if ans[1] == -1:
                    ans = val;
                if max_layer and val[0] > ans[0]:
                    ans = val;
                if (not max_layer) and val[0] < ans[0]:
                    ans = val;
            else:
                if ans == -1:
                    ans = val;
                if max_layer and val > ans:
                    ans = val;
                if (not max_layer) and val < ans:
                    ans = val;
        
        if now.ctx.current_player != self.camp:
            max_layer = False;

        for i in range(1,6+1):
            if len(self.stack) == stack_ind+1:
                self.stack.append(copy.deepcopy(self.stack[stack_ind]));#这里每次都copy，不太好
            else:
                self.stack[stack_ind+1] = copy.deepcopy(self.stack[stack_ind]);
            
            if self.stack[stack_ind+1].apply(i):
                self.debug_search_cnt += 1;
                #结束判定
                end = False;
                if len(self.stack[stack_ind+1].ctx.snake_list) == 0:#全死了
                    end = True;
                if self.stack[stack_ind+1].ctx.turn >= self.end_turn and now.next_snake == self.snkid:#到达指定回合数
                    end = True;
                if self.stack[stack_ind+1].ctx.get_snake(self.snkid) == None and now.next_snake == self.snkid:#蛇死了
                    end = True;
                if end:
                    if stack_ind == 0:
                        comp((self.value_func(self.stack[stack_ind+1]),i));
                    else:
                        comp(self.value_func(self.stack[stack_ind+1]));
                    continue;

                # print("step in:",i);
                val = self.search_dfs(stack_ind+1);
                if stack_ind == 0:
                    comp((val,i));
                else:
                    comp(val);
        
        return ans;

    

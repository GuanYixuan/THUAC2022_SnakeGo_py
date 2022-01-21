from adk import *
import sampleAI as AI;

ACT = ((1,0),(0,1),(-1,0),(0,-1));
INF = 100000000;
# constants

SPLIT_LIMIT = 10
SEARCH_LIMIT = 100
# tunable parameters



class assess:
    """
    估价模块
    """
    AI : "AI.AI";
    ctx : Context;
    snakes : "list[Snake]";
    this_snake : Snake;
    game_map : Map;
    x_leng : int;
    y_leng : int;
    snkid : int;
    pos : "tuple[int,int]";

    def __init__(self,AI : "AI.AI",ctx : Context,snkid : int):
        self.ctx,self.AI= ctx,AI;
        self.game_map = ctx.get_map();
        self.x_leng,self.y_leng = self.game_map.length,self.game_map.width;
        self.snakes,self.snkid,self.this_snake = ctx.snake_list,snkid,ctx.get_snake(snkid);
        self.pos = self.this_snake.coor_list[0];

        self.find_path();
        self.scan_act();
        self.calc_polite_score();
    
    def sort_key(self,ele):
            return ele[1] + 0.01*random.random();
    def calc_spd_map(self,snkid : int) -> "list[list[int]]":
        '''
        计算“速度势力图”，即哪方能先到达指定格
        返回一个二维数组，其中:
            +1表示我方在普通环境下先到达
            +2表示通过使用射线，我方先到达
        '''
        FLAG_NORM_FIRST = 1;
        FLAG_RAY_FIRST = 2;
        tmp = [[0 for y in range(self.y_leng)] for x in range(self.x_leng)];#(tmp)
        ans = [[0 for y in range(self.y_leng)] for x in range(self.x_leng)];
        
        #把蛇占据的先填上
        for sn in self.snakes:
            sid = 1;
            if sn.camp != self.ctx.current_player:
                sid = -1;
            for t in range(len(sn.coor_list)):
                x,y = sn.coor_list[t];
                tmp[x][y] = sid * (len(sn.coor_list)-t);
        
        vis = [[0 for y in range(self.y_leng)] for x in range(self.x_leng)];
        queue : "list[tuple[int,int,int,int]]" = [];#(x,y,step,comp)
        for sn in self.snakes:
            queue.append((sn.coor_list[0][0],sn.coor_list[0][1],1,sn.camp == self.ctx.current_player));
        
        while len(queue):
            x,y,step,comp = queue[0];
            del queue[0];
            vis[x][y] = 1;

            for act in ACT:
                tx,ty = x+act[0],y+act[1];
                if not self.check_mov_norm(tx,ty,snkid=snkid):#这里不对
                    continue;
                #还没写完

    act_score : "list[float]" = [-1,-1,-1,-1];
    act_list : "list[tuple[int,float]]" = [];
    def scan_act(self):#一言难尽
        """
        计算各移动策略的安全系数
        会撞死的返回-100
        【特判了len<=2的蛇】
        """
        self.__scan_act_bfs();
        self.act_score = [-1 for i in range(4)];

        x,y = self.pos;
        for i,act in enumerate(ACT):
            tx = x + act[0];
            ty = y + act[1];
            if not self.check_mov_norm(tx,ty):
                self.act_score[i] = -100;
                continue;
            if self.this_snake.get_len() <= 2:
                self.act_score[i] = 50;
                continue;
            self.__scan_act_vis = [[0 for y in range(self.y_leng)] for x in range(self.x_leng)];
            self.__scan_act_dfs(tx,ty,i);
        
        for i in range(len(ACT)):
            self.act_list.append((i,self.act_score[i]));
        
        self.act_list.sort(key=self.sort_key,reverse=True);
        # logging.debug("act_score:%s" % self.act_score);
    
    _scan_act_map : "list[list[int]]";
    __SCAN_ACT_MAX_DEPTH = 5;
    __SCAN_ACT_REDUCE_FACTOR = 0.4;
    def __scan_act_bfs(self):
        x,y = self.pos;
        def read_snk_map(nx : int,ny : int) -> int:
            if (nx,ny) == self.this_snake.coor_list[-1]:#尾巴
                if self.this_snake.length_bank:
                    return self.snkid;
                return -1;
            return self.ctx.game_map.snake_map[nx][ny];
        def find_head(nx : int,ny : int) -> float:
            ans = 1;
            for i,act in enumerate(ACT):
                tx = nx + act[0];
                ty = ny + act[1];
                if tx < 0 or ty < 0 or tx >= 16 or ty >= 16:
                    continue;
                snk = self.ctx.game_map.snake_map[tx][ty];
                if snk != -1 and snk != self.snkid:
                    if (tx,ty) == self.ctx.get_snake(snk).coor_list[0]:#是头
                        ans *= self.__SCAN_ACT_REDUCE_FACTOR;
            return ans;
        
        self._scan_act_map = [[-1 for y in range(self.y_leng)] for x in range(self.x_leng)];
        queue : "list[tuple[int,int,int,float]]" = [];#(x,y,step,val)
        queue.append((x,y,0,1));
        
        while len(queue):
            x,y,step,val = queue[0];
            del queue[0];
            if step >= self.__SCAN_ACT_MAX_DEPTH:
                continue;

            for i,act in enumerate(ACT):
                tx,ty = x+act[0],y+act[1];
                if not self.check_mov_norm(tx,ty,step):
                    continue;
                heads = find_head(tx,ty);
                if self._scan_act_map[tx][ty] == -1:
                    queue.append((tx,ty,step+1,val*heads));
                    self._scan_act_map[tx][ty] = val*heads;
    
    __scan_act_vis : "list[list[int]]";
    def __scan_act_dfs(self,x : int,y : int,ind : int):
        self.__scan_act_vis[x][y] = 1;
        self.act_score[ind] += self._scan_act_map[x][y];

        for i,act in enumerate(ACT):
            tx = x + act[0];
            ty = y + act[1];
            if tx < 0 or ty < 0 or tx >= 16 or ty >= 16:
                continue;
            if self._scan_act_map[tx][ty] == -1 or self.__scan_act_vis[tx][ty]:
                continue;
            self.__scan_act_dfs(tx,ty,ind);

    dist_map : "list[list[int]]";#保存距离，不可达格会是-1
    path_map : "list[list[int]]";#保存“如何走到这一格”，注意这里是ACT的下标，本身格会是-1
    def rev_step(self,st : int) -> int:#对行动取反，注意这里是ACT的下标
            return (2,3,0,1)[st];
    __GREEDY_DIRECTION_SCORE = 4;
    def random_step(self):
        '''
        随便走一格，返回ACT的下标
        '''
        x,y = self.pos;
        random_list : "list[tuple[int,float]]" = [];
        for i in range(len(ACT)):
            random_list.append((i,self.polite_score[i]));
        random_list.sort(key=self.sort_key,reverse=True);

        if random_list[0][1] < -80:
            return self.emergency_handle();
        logging.debug("随机漫步:%d" % random_list[0][0]);
        return random_list[0][0];
    def greedy_step(self,tgt : "tuple[int,int]"):
        '''
        贪心地向tgt走一格，返回ACT的下标
        '''
        x,y =  self.pos;
        dx,dy = tgt[0]-x,tgt[1]-y;
        greedy_score = [-100,-100,-100,-100];
        greedy_list : "list[tuple[int,float]]" = [];

        if dx > 0 and self.check_mov_norm(x+ACT[0][0],y+ACT[0][1]):
            greedy_score[0] = self.__GREEDY_DIRECTION_SCORE;
        if dx < 0 and self.check_mov_norm(x+ACT[2][0],y+ACT[2][1]):
            greedy_score[2] = self.__GREEDY_DIRECTION_SCORE;
        if dy > 0 and self.check_mov_norm(x+ACT[1][0],y+ACT[1][1]):
            greedy_score[1] = self.__GREEDY_DIRECTION_SCORE;
        if dy < 0 and self.check_mov_norm(x+ACT[3][0],y+ACT[3][1]):
            greedy_score[3] = self.__GREEDY_DIRECTION_SCORE;
        
        for i in range(len(ACT)):
            greedy_score[i] += self.polite_score[i];
            greedy_list.append((i,greedy_score[i]));
        
        greedy_list.sort(key=self.sort_key,reverse=True);

        if greedy_list[0][1] < -80:
            return self.emergency_handle();
        
        logging.debug("贪心寻路:%d" % greedy_list[0][0]);
        return greedy_list[0][0];
    def emergency_handle(self) -> int:
        def calc_leng(tgt : "tuple[int,int]") -> int:#不见得是严格的长度
            for i,pos in enumerate(self.this_snake.coor_list):
                if pos == tgt:
                    return i;
            raise;
        
        if self.can_shoot():
            ans = self.ray_trace_self();
            if ans[0] - ans[1] <= self.this_snake.get_len()/3 and ans[0] - ans[1] <= 2:#常数1/3及2
                logging.debug("紧急处理:发射激光，击毁(%d,%d)" % ans);
                return 5 - 1;
        if self.can_split():
            logging.debug("紧急处理:分裂");
            return 6 - 1;#分裂
        
        #死亡不可避，释放原目标
        tgt = self.AI.wanted_item[self.snkid];
        if tgt != -1:
            logging.debug("紧急处理:释放原目标%s" % tgt);
            self.AI.item_alloc[tgt.id] = -1;

        vaild = [];
        best = [-1,-9];#[maxl,ind]
        for i,act in enumerate(ACT):
            tx,ty = self.pos[0]+act[0],self.pos[1]+act[1];
            if tx < 0 or ty < 0 or tx >= 16 or ty >= 16:
                vaild.append(i);
                continue;
            if self.ctx.game_map.snake_map[tx][ty] != self.snkid:
                vaild.append(i);
                continue;
            if self.this_snake.get_len() > 2 and (tx,ty) == self.this_snake.coor_list[1]:#防止后退
                continue;
            if self.this_snake.get_len() == 2 and (tx,ty) == self.this_snake.coor_list[1]:#防止后退
                continue;
            leng = calc_leng((tx,ty));
            if leng > best[0]:
                best = [leng,i];
        if best[1] == -9:
            logging.debug("紧急处理:%d(防倒车)" % vaild[0]);
            return vaild[0];
        logging.debug("紧急处理:%d" % best[1]);
        return best[1];
    
    def check_act_seq(self,first : int,second : int) -> bool:
        """
        检查编号为first的蛇是否比编号为second的蛇先手
        【这一判断基于目前正在行动的蛇的id（即self.snkid）作出】
        """
        now_ind = -1;
        snks = self.ctx.snake_list;
        for ind,_snake in enumerate(snks):#相当于从now_ind搜索到结尾
            if _snake.id == self.snkid:
                now_ind = ind;
            if now_ind != -1 and _snake.id == first:
                return True;
            if now_ind != -1 and _snake.id == second:
                return False;
        
        for ind,_snake in enumerate(snks):#相当于从开头搜索到now_ind
            if now_ind != -1 and _snake.id == first:
                return True;
            if now_ind != -1 and _snake.id == second:
                return False;
        raise;
    
    attack_score : "list[float]";
    polite_score : "list[float]";
    __1_AIR_SCORE = -5;
    __NO_AIR_SCORE = -10;
    def calc_polite_score(self):
        """
        计算“谦让值”，某一个act将队友的“气”挤压到小于2，则该值减小
        """
        x,y = self.pos;
        self.polite_score = [-100,-100,-100,-100];

        for i,act in enumerate(ACT):
            tx = x + act[0];
            ty = y + act[1];

            if not self.check_mov_norm(tx,ty,0):
                continue;
            self.polite_score[i] = 0;

            extra_go = (-1,-1);
            if not self.this_snake.length_bank:
                extra_go = self.this_snake.coor_list[-1];
            
            for _friend in self.ctx.snake_list:
                if _friend.camp != self.this_snake.camp or _friend.id == self.snkid:
                    continue;
                curr = self.calc_friend_air(_friend.coor_list[0]);
                ftr = self.calc_friend_air(_friend.coor_list[0],(tx,ty),extra_go);
                if ftr < curr and ftr == 1:
                    self.polite_score[i] += self.__1_AIR_SCORE;
                if ftr < curr and ftr == 0:
                    self.polite_score[i] += self.__NO_AIR_SCORE;
        logging.debug("polite_score:%s" % self.polite_score);

    def calc_friend_air(self,pos : "tuple[int,int]",extra_block : "tuple[int,int]" = (-1,-1),extra_go : "tuple[int,int]" = (-1,-1)) -> int:
        """
        计算当前位于pos的【队友】蛇头有几个方向可走
        可添加一个额外堵塞位置extra_block及一个额外可行位置extra_go
        【这里默认extra_block是你的蛇头而extra_go是蛇尾】
        """
        ans = 0;
        x,y = pos;
        snkid = self.ctx.game_map.snake_map[x][y];
        for i,act in enumerate(ACT):
            tx = x + act[0];
            ty = y + act[1];

            if (tx,ty) == extra_block:
                continue;
            if self.check_mov_norm(tx,ty,0,snkid):
                #【默认顺序是"对手们"--"你"--"队友"，故time=0】
                ans += 1;
                continue;
            if (tx,ty) == extra_go:#检查不通过，但恰好是extra_go
                #不可能越界/撞墙，必然在撞蛇(self.snkid)
                #不可能是非法回头
                ans += 1;
                continue;
        return ans;

    def check_item_captured_team(self,item : Item) -> int:
        """
        检查物品是否被哪方的蛇占住了（可以用身子直接吃掉），没有则返回-1
        """
        x,y = item.x,item.y;
        if self.ctx.game_map.snake_map[x][y] == -1:
            return -1;
        if self.check_item_captured(item,self.ctx.game_map.snake_map[x][y]):
            return self.ctx.get_snake(self.ctx.game_map.snake_map[x][y]).camp;
        return -1;
    def check_item_captured(self,item : Item,snkid : int = -1) -> bool:
        """
        检查物品是否已经被snkid的蛇占住了（可以用身子直接吃掉）
        """
        x,y = item.x,item.y;
        if snkid == -1:
            snkid = self.snkid;

        if self.ctx.game_map.snake_map[x][y] != snkid:
            return False;
        snk = self.ctx.get_snake(snkid);
        for i,pos in enumerate(snk.coor_list):
            if pos == (x,y):
                if item.time - self.ctx.turn < snk.get_len()-i + snk.length_bank:
                    return True;
                else:
                    return False;
        raise;

    __BFS_DIRECTION_SCORE = 6;
    def find_first(self,tgt : "tuple[int,int]"):
        """
        倒推走向tgt的第一步应该怎么走，返回的是ACT的下标
        """
        x,y = tgt;
        rev = -1;
        if tgt == self.pos:#头已经在本格了，随便找一个可走的方向走
            return self.random_step();
        if self.path_map[x][y] == -1:
            return self.greedy_step(tgt);
        
        bfs_list : "list[tuple[int,float]]" = [];
        while (x,y) != self.pos:
            if self.path_map[x][y] == -1:
                raise;
            rev = self.rev_step(self.path_map[x][y]);
            x += ACT[rev][0];
            y += ACT[rev][1];
        for i in range(len(ACT)):
            if i == self.rev_step(rev):
                bfs_list.append((i,self.__BFS_DIRECTION_SCORE+self.polite_score[i]));
            else:
                bfs_list.append((i,self.polite_score[i]));
        bfs_list.sort(key=self.sort_key,reverse=True);

        if bfs_list[0][0] != self.rev_step(rev):
            logging.debug("寻路[避让]:%d 目标:(%d,%d)" % (self.rev_step(rev),tgt[0],tgt[1]));
            return bfs_list[0][0];
        logging.debug("寻路:%d 目标:(%d,%d)" % (self.rev_step(rev),tgt[0],tgt[1]));
        return bfs_list[0][0];
    def find_path(self):
        """
        跑一次从snkid所在位置到全图的bfs
        这里认为所有蛇的头是静态的
        """
        nx,ny = self.ctx.get_snake(self.snkid).coor_list[0];

        self.path_map = [[-1 for y in range(self.y_leng)] for x in range(self.x_leng)];
        self.dist_map = [[-1 for y in range(self.y_leng)] for x in range(self.x_leng)];
        queue : "list[tuple[int,int,int]]" = [];#(x,y,step)

        queue.append((nx,ny,0));#从起点开始
        self.path_map[nx][ny],self.dist_map[nx][ny] = -1,0;

        while len(queue):
            x,y,step = queue[0];
            del queue[0];

            for i,act in enumerate(ACT):
                tx,ty = x+act[0],y+act[1];
                if not self.check_mov_norm(tx,ty,step):
                    continue;
                if self.dist_map[tx][ty] == -1:
                    queue.append((tx,ty,step+1));
                    self.path_map[tx][ty] = i;
                    self.dist_map[tx][ty] = step+1;

    def get_pos_on_snake(self,pos : "tuple[int,int]") -> int:
        x,y = pos;
        snkid = self.ctx.game_map.snake_map[x][y];
        snk = self.ctx.get_snake(snkid);
        for i,_pos in enumerate(snk.coor_list):
            if pos == _pos:
                return len(snk.coor_list)-i;
    # def _get_enclosing_leng(self,snkid : int = -1) -> "tuple[int,int]":
    #     """
    #     计算id=snkid的蛇立刻主动进行固化能利用的最大身体长度
    #     """

    def check_mov_norm(self,tx : int,ty : int,time : int = 0,snkid : int = -1) -> bool:
        """
        判断id=snkid的蛇在time时间后走到(tx,ty)这一格是否可行（不会被撞死）
        """
        if snkid == -1:
            snkid = self.snkid;
        snk = self.ctx.get_snake(snkid);

        #越界/撞墙
        if tx < 0 or ty < 0 or tx >= 16 or ty >= 16 or self.ctx.game_map.wall_map[tx][ty] != -1:
            return False;
        #撞蛇
        blocking_snake = self.ctx.game_map.snake_map[tx][ty];
        self_blocking = 0;
        if blocking_snake == snkid:
            self_blocking = 1;

        if blocking_snake == -1:
            return True;

        leave_time =  self.get_pos_on_snake((tx,ty)) + snk.length_bank - self_blocking;
        if self_blocking: 
            if leave_time <= time:
                return True;
            return False;
        else:
            if leave_time >= time:
                return False;
            return True;

    def can_split(self,snkid : int = -1) -> bool:
        if snkid == -1:
            snkid = self.snkid;
        if self.ctx.get_snake_count(self.ctx.current_player) >= 4:
            return False;
        if self.ctx.get_snake(snkid).get_len() < 2:
            return False;
        return True;

    def has_laser(self,snkid : int = -1) -> bool:
        if snkid == -1:
            snkid = self.snkid;
        for _item in self.ctx.get_snake(snkid).item_list:#或许检查item_list是否为空即可
            if _item.type == 2:
                return True;
        return False;
    def can_shoot(self,snkid : int = -1) -> bool:
        '''
        判断当前蛇能不能shoot
        '''
        if snkid == -1:
            snkid = self.snkid;
        if self.ctx.get_snake(snkid).get_len() < 2 or (not self.has_laser(snkid)):
            return False
        return True;
    def ray_trace_self(self) -> "tuple[int,int]":
        '''
        如果当前蛇立即发射激光，会打掉多少(自己，对方)的墙？
        对长度为1的蛇返回(-1,-1)
        '''
        if self.this_snake.get_len() == 1:
            return (-1,-1);
        pos0,pos1 = self.this_snake.coor_list[0],self.this_snake.coor_list[1];
        return self.ray_trace(pos0,(pos0[0]-pos1[0],pos0[1]-pos1[1]));
    def ray_trace(self,pos : "tuple[int,int]",dire : "tuple[int,int]") -> "tuple[int,int]":
        '''
        从pos向dire向量方向发射激光，会打掉多少(自己，对方)的墙？
        '''
        ans = [0,0];
        tx,ty = pos;
        while tx >= 0 and ty >= 0 and tx < 16 and ty < 16:
            wall = self.ctx.game_map.wall_map[tx][ty];
            if wall != -1:
                if wall == self.ctx.current_player:
                    ans[0] += 1;
                else:
                    ans[1] += 1;
            tx += dire[0];
            ty += dire[1];
        return (ans[0],ans[1]);
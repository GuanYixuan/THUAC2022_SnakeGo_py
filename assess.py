from adk import *
import sampleAI as AI;

ACT = ((1,0),(0,1),(-1,0),(0,-1));
INF = 100000000;
# constants

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
    camp : int;
    pos : "tuple[int,int]";

    def __init__(self,AI : "AI.AI",ctx : Context,snkid : int):
        self.ctx,self.AI= ctx,AI;
        self.game_map = ctx.get_map();
        self.x_leng,self.y_leng = self.game_map.length,self.game_map.width;
        self.snakes,self.snkid,self.this_snake = ctx.snake_list,snkid,ctx.get_snake(snkid);
        self.pos = self.this_snake.coor_list[0];
        self.camp = self.ctx.current_player;

        self.dist_map,self.path_map = dict(),dict();
        self.__find_path_bfs();
        self.scan_act();
        self.__calc_P_A_score();
    
    def sort_key(self,ele):
            return ele[1] + 0.01*random.random();
    friend_spd : "list[list[tuple[int,int]]]";#(dist,snkid)
    enemy_spd : "list[list[tuple[int,int]]]";#(dist,snkid)
    tot_spd : "list[list[tuple[int,int]]]";#(dist,snkid)
    def calc_spd_map(self):
        '''
        计算“速度势力图”，即哪方能先到达指定格
        【默认蛇身/头所在格到达时间为0】
        '''
        self.friend_spd = [[(-1,-1) for y in range(self.y_leng)] for x in range(self.x_leng)];
        self.enemy_spd = [[(-1,-1) for y in range(self.y_leng)] for x in range(self.x_leng)];
        self.tot_spd = [[(-1,-1) for y in range(self.y_leng)] for x in range(self.x_leng)];
        for x in range(self.x_leng):
            for y in range(self.y_leng):
                snkid = self.game_map.snake_map[x][y]
                if snkid != -1:
                    if self.ctx.get_snake(snkid).camp == self.camp:#友方
                        self.friend_spd[x][y] = (0,snkid);
                    else:
                        self.enemy_spd[x][y] = (0,snkid);
                
                for _snake in self.snakes:
                    dst = self.dist_map[_snake.id][x][y];
                    tup = (dst,_snake.id);
                    if dst == -1:
                        continue;
                    if _snake.camp == self.camp:#友方
                        if self.friend_spd[x][y] == (-1,-1):
                            self.friend_spd[x][y] = tup;
                        elif self.friend_spd[x][y][0] > dst:#【距离相等时，依照snake_list中的顺序优先】
                            self.friend_spd[x][y] = tup;
                    else:
                        if self.enemy_spd[x][y] == (-1,-1):
                            self.enemy_spd[x][y] = tup;
                        elif self.enemy_spd[x][y][0] > dst:
                            self.enemy_spd[x][y] = tup;
        
        for x in range(self.x_leng):
            for y in range(self.y_leng):
                valf,vale = self.friend_spd[x][y][0],self.enemy_spd[x][y][0];
                if valf == -1:
                    valf = 1000;
                if vale == -1:
                    vale = 1000;
                
                if min(valf,vale) == 1000:
                    continue;
                if valf <= vale:#【敌我距离相等时，我方优先】
                    self.tot_spd[x][y] = self.friend_spd[x][y];
                else:
                    self.tot_spd[x][y] = self.enemy_spd[x][y];

    safe_score : "list[float]";
    act_score : "list[float]";
    __CRIT_AIR_PARAM = (-8,-1);
    __LOW_AIR_PARAM = (-0.8);
    def scan_act(self):
        """
        计算各移动策略的安全系数
        会撞死的返回-100
        【特判了len<=2的蛇】
        """
        self.act_score = [0 for i in range(4)];
        self.safe_score = [0 for i in range(4)];
        self._scan_act_debug = [[],[],[],[]];

        x,y = self.pos;
        will_log = True;
        for i,act in enumerate(ACT):
            tx = x + act[0];
            ty = y + act[1];
            if not self.check_nstep_norm(tx,ty):
                self.act_score[i] = -100;
                self.safe_score[i] = -100;
                continue;
            if self.this_snake.get_len() <= 2:
                self.act_score[i] = 25;
                continue;
            self.__scan_act_bfs(i);

            leng = self.this_snake.get_len() + self.this_snake.length_bank;
            if self.act_score[i] <= 4.5 or self.act_score[i] <= leng*0.75:
                self.safe_score[i] += self.__CRIT_AIR_PARAM[0] + leng*self.__CRIT_AIR_PARAM[1] + 0.3*self.act_score[i];
            elif self.act_score[i] <= 10 and self.act_score[i] <= leng*2.5:
                self.safe_score[i] += min(0,(max(10,leng*2.5)-self.act_score[i])*self.__LOW_AIR_PARAM) + 0.2*self.act_score[i];

            if self.safe_score[i] > -90 and self.safe_score[i] < -0.5:
                will_log = True;
        
        if will_log:
            logging.debug("act_score:%s" % self.act_score);
            logging.debug("safe_score:%s" % self.safe_score);
            for i in range(4):
                logging.debug("list%d : %s" % (i,self._scan_act_debug[i]));

    _scan_act_debug : "list[list[tuple[int,int]]]";
    _scan_act_map : "list[list[int]]";
    __SCAN_ACT_MAX_DEPTH = 6;
    __SCAN_ACT_REDUCE_FACTOR = (0.2,0.3);#敌,我
    def __scan_act_bfs(self,actid : int):
        def find_head(nx : int,ny : int) -> float:
            ans = 1;
            for i,act in enumerate(ACT):
                tx = nx + act[0];
                ty = ny + act[1];
                if tx < 0 or ty < 0 or tx >= 16 or ty >= 16:
                    continue;
                snk = self.game_map.snake_map[tx][ty];
                if snk != -1 and snk != self.snkid:
                    if (tx,ty) == self.ctx.get_snake(snk).coor_list[0]:#是头
                        if self.ctx.get_snake(snk).camp != self.camp:
                            ans *= self.__SCAN_ACT_REDUCE_FACTOR[0];
                        else:
                            ans *= self.__SCAN_ACT_REDUCE_FACTOR[1];
            return ans;
        rx,ry = self.pos;
        self._scan_act_map = [[-1 for y in range(self.y_leng)] for x in range(self.x_leng)];
        self._scan_act_map[rx][ry],self._scan_act_map[rx+ACT[actid][0]][ry+ACT[actid][1]] = -2,-2;
        queue : "list[tuple[int,int,int,float]]" = [];#(x,y,step,val)
        queue.append((rx+ACT[actid][0],ry+ACT[actid][1],1,1));
        
        while len(queue):
            x,y,step,val = queue[0];
            del queue[0];
            if step >= self.__SCAN_ACT_MAX_DEPTH:
                break;

            for i,act in enumerate(ACT):
                tx,ty = x+act[0],y+act[1];
                if not self.check_nstep_norm(tx,ty,step+1):
                    continue;
                heads = find_head(tx,ty);
                if self._scan_act_map[tx][ty] == -1:
                    queue.append((tx,ty,step+1,val*heads));
                    self._scan_act_map[tx][ty] = val*heads;
                    self.act_score[actid] += val*heads;
                    self._scan_act_debug[actid].append((tx,ty));

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
            random_list.append((i,self.polite_score[i]+self.attack_score[i]+self.safe_score[i]));
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
        greedy_score = [0,0,0,0];
        greedy_list : "list[tuple[int,float]]" = [];

        if dx > 0 and self.check_nstep_norm(x+ACT[0][0],y+ACT[0][1]):
            greedy_score[0] = self.__GREEDY_DIRECTION_SCORE;
        if dx < 0 and self.check_nstep_norm(x+ACT[2][0],y+ACT[2][1]):
            greedy_score[2] = self.__GREEDY_DIRECTION_SCORE;
        if dy > 0 and self.check_nstep_norm(x+ACT[1][0],y+ACT[1][1]):
            greedy_score[1] = self.__GREEDY_DIRECTION_SCORE;
        if dy < 0 and self.check_nstep_norm(x+ACT[3][0],y+ACT[3][1]):
            greedy_score[3] = self.__GREEDY_DIRECTION_SCORE;
        
        for i in range(len(ACT)):
            greedy_score[i] += self.polite_score[i] + self.attack_score[i] + self.safe_score[i];
            greedy_list.append((i,greedy_score[i]));
        
        greedy_list.sort(key=self.sort_key,reverse=True);

        if greedy_list[0][1] < -80:
            return self.emergency_handle();
        
        logging.debug("贪心寻路:%d" % greedy_list[0][0]);
        return greedy_list[0][0];
    __BUILD_EFFICIENCY_BOUND = 0.75;
    def emergency_handle(self) -> int:
        """
        处理紧急情况（蛇要死了）
        """
        if self.can_shoot():
            ans = self.ray_trace_self();
            if ans[0] - ans[1] <= self.this_snake.get_len()/3 and ans[0] - ans[1] <= 2:#常数1/3及2
                logging.debug("紧急处理:发射激光，击毁(%d,%d)" % ans);
                return 5 - 1;
        
        vaild = [];
        best = self.get_enclosing_leng();
        for i,act in enumerate(ACT):
            tx,ty = self.pos[0]+act[0],self.pos[1]+act[1];
            if tx < 0 or ty < 0 or tx >= 16 or ty >= 16:
                vaild.append(i);
                continue;
            if self.game_map.snake_map[tx][ty] != self.snkid:
                vaild.append(i);

        if best[0] >= self.__BUILD_EFFICIENCY_BOUND * (self.this_snake.get_len()+self.this_snake.length_bank):
            logging.debug("紧急处理:变现，利用了%d格蛇长" % best[0]);
            return best[1];

        if self.can_split():
            logging.debug("紧急处理:分裂");
            return 6 - 1;#分裂
        
        if best[0] < 0:
            logging.debug("紧急处理:%d(防倒车)" % vaild[0]);
            return vaild[0];
        logging.debug("紧急处理:%d" % best[1]);
        return best[1];
    def release_target(self,snkid : int = -1):
        """
        释放snkid的目标
        """
        if snkid == -1:
            snkid = self.snkid;
        tgt = self.AI.wanted_item[snkid];
        if tgt != -1:
            logging.debug("释放原目标%s" % tgt);
            self.AI.item_alloc[tgt.id] = -1;
    def check_first(self,first : int,second : int) -> bool:
        """
        检查编号为first的蛇的下一次行动是否比编号为second的蛇先
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
    __POLITE_1_AIR_PARAM = [-4.0,-0.4];
    __POLITE_NO_AIR_PARAM = [-8,-1];
    __ATTACK_1_AIR_MULT = 0.3;
    __ATTACK_NO_AIR_MULT = 0.7;
    __ATTAC_NO_AIR_NO_LASER_BONUS = 2;
    __ATTACK_NO_AIR_4_SNAKE_BONUS = 2;
    __SMALL_SNAKE_ATTACK_GAIN = [0,1.2,1.5];
    def __calc_P_A_score(self):
        """
        计算“谦让值”与“攻击值”
        某一个act将队友的“气”挤压到小于2，则polite_score减小；若是对手，则attack_score加大
        """
        x,y = self.pos;
        will_log_atk,will_log_pol = False,False;
        self.polite_score = [-100,-100,-100,-100];
        self.attack_score = [-100,-100,-100,-100];

        for i,act in enumerate(ACT):
            tx = x + act[0];
            ty = y + act[1];

            if not self.check_nstep_norm(tx,ty):
                continue;
            self.polite_score[i] = 0;
            self.attack_score[i] = 0;

            extra_go = (-1,-1);
            if not self.this_snake.length_bank:
                extra_go = self.this_snake.coor_list[-1];
            
            for _friend in self.ctx.snake_list:
                if _friend.camp != self.this_snake.camp or _friend.id == self.snkid:
                    continue;
                curr = self.calc_snk_air(_friend.coor_list[0]);
                ftr = self.calc_snk_air(_friend.coor_list[0],(tx,ty),extra_go);
                if ftr < curr and ftr == 1:
                    self.polite_score[i] += self.__POLITE_1_AIR_PARAM[0] + (_friend.get_len()+_friend.length_bank) * self.__POLITE_1_AIR_PARAM[1];
                if ftr < curr and ftr == 0:
                    self.polite_score[i] += self.__POLITE_NO_AIR_PARAM[0] + (_friend.get_len()+_friend.length_bank) * self.__POLITE_NO_AIR_PARAM[1];
            
            for _enemy in self.ctx.snake_list:
                if _enemy.camp == self.this_snake.camp:
                    continue;
                curr = self.calc_snk_air(_enemy.coor_list[0]);
                ftr = self.calc_snk_air(_enemy.coor_list[0],(tx,ty),extra_go);#可以考虑“2step后的气”
                if ftr < curr and ftr == 1:
                    self.attack_score[i] += (_enemy.get_len() + _enemy.length_bank) * self.__ATTACK_1_AIR_MULT;
                if ftr < curr and ftr == 0:
                    self.attack_score[i] += (_enemy.get_len() + _enemy.length_bank) * self.__ATTACK_NO_AIR_MULT;
                    if not self.can_split(_enemy.id):
                        self.attack_score[i] += self.__ATTACK_NO_AIR_4_SNAKE_BONUS;
                    if not self.can_shoot(_enemy.id):
                        self.attack_score[i] += self.__ATTAC_NO_AIR_NO_LASER_BONUS;
            
            for i in range(len(ACT)):
                if self.this_snake.get_len() + self.this_snake.length_bank <= 2:
                    self.attack_score[i] *= self.__SMALL_SNAKE_ATTACK_GAIN[self.this_snake.get_len() + self.this_snake.length_bank];
            
            if self.attack_score[i] > 0.5:
                will_log_atk = True;
            if self.polite_score[i] > -90 and self.polite_score[i] < -0.5:
                will_log_pol = True;

        if will_log_atk:
            logging.debug("attack_score:%s" % self.attack_score);
        if will_log_pol:
            logging.debug("polite_score:%s" % self.polite_score);

    def calc_snk_air(self,pos : "tuple[int,int]",extra_block : "tuple[int,int]" = (-1,-1),extra_go : "tuple[int,int]" = (-1,-1)) -> int:
        """
        计算当前位于pos的蛇头有几个方向可走
        可添加一个额外堵塞位置extra_block及一个额外可行位置extra_go
        【这里默认extra_block是你的蛇头而extra_go是蛇尾】
        """
        ans = 0;
        x,y = pos;
        snkid = self.game_map.snake_map[x][y];
        for i,act in enumerate(ACT):
            tx = x + act[0];
            ty = y + act[1];

            if (tx,ty) == extra_block:
                continue;
            if self.check_nstep_norm(tx,ty,1,snkid):
                #【默认顺序是"对手们"--"你"--"队友"，故time=0】
                #【需要画图来思考为什么取time=0】
                #事实上取0也不完全准确（可能会少算敌方的气），但比取1（多算）要好
                #核心是先后手的问题
                ans += 1;
                continue;
            if (tx,ty) == extra_go:#检查不通过，但恰好是extra_go
                #不可能越界/撞墙，必然在撞蛇(self.snkid)
                #不可能是非法回头
                ans += 1;
                continue;
        return ans;
    
    def get_captured_items(self,snkid : int = -1,item_tp : int = -1) -> "list[Item]":
        """
        返回已被此蛇稳吃的Item列表，可手动限定type
        """
        if snkid == -1:
            snkid = self.snkid;

        ans = [];
        for _item in self.game_map.item_list:
            if item_tp != -1 and _item.type != item_tp:
                continue;
            if _item.time - self.ctx.turn > self.ctx.get_snake(snkid).get_len() + self.ctx.get_snake(snkid).length_bank:
                continue;
            if self.check_item_captured(_item,snkid):
                ans.append(_item);
        return ans;
    def check_item_captured_team(self,item : Item) -> int:
        """
        检查物品是否被哪方的蛇占住了（可以用身子直接吃掉），没有则返回-1
        """
        x,y = item.x,item.y;
        if self.game_map.snake_map[x][y] == -1:
            return -1;
        if self.check_item_captured(item,self.game_map.snake_map[x][y]):
            return self.ctx.get_snake(self.game_map.snake_map[x][y]).camp;
        return -1;
    def check_item_captured(self,item : Item,snkid : int = -1) -> bool:
        """
        检查物品是否已经被snkid的蛇占住了（可以用身子直接吃掉）
        """
        x,y = item.x,item.y;
        if snkid == -1:
            snkid = self.snkid;

        if self.game_map.snake_map[x][y] != snkid:
            return False;
        snk = self.ctx.get_snake(snkid);
        for i,pos in enumerate(snk.coor_list):
            if pos == (x,y):
                if item.time - self.ctx.turn < snk.get_len()-i + snk.length_bank:
                    return True;
                else:
                    return False;
        raise;
    def __bank_siz_list_bfs(self,snkid : int = -1) -> "list[int]":
        """
        返回一个长度为100的数组，在寻路bfs中作为check_norm的bank参数
        """
        if snkid == -1:
            snkid = self.snkid;

        item_list = self.get_captured_items(snkid,0);
        ans = [self.ctx.get_snake(snkid).length_bank];
        for i in range(1,100):
            ans.append(ans[i-1]);
            for _item in item_list:
                if _item.time == self.ctx.turn + i:
                    ans[i] += _item.param;
        return ans;

    __BFS_DIRECTION_SCORE = 6;
    def find_first(self,tgt : "tuple[int,int]"):
        """
        倒推走向tgt的第一步应该怎么走，返回的是ACT的下标
        """
        x,y = tgt;
        rev = -1;
        if tgt == self.pos:#头已经在本格了，随便找一个可走的方向走
            return self.random_step();
        if self.path_map[self.snkid][x][y] == -1:
            return self.greedy_step(tgt);
        
        bfs_list : "list[tuple[int,float]]" = [];
        while (x,y) != self.pos:
            if self.path_map[self.snkid][x][y] == -1:
                raise;
            rev = self.rev_step(self.path_map[self.snkid][x][y]);
            x += ACT[rev][0];
            y += ACT[rev][1];
        for i in range(len(ACT)):
            if i == self.rev_step(rev):
                bfs_list.append((i,self.__BFS_DIRECTION_SCORE+self.polite_score[i]+self.attack_score[i]+self.safe_score[i]));
            else:
                bfs_list.append((i,self.polite_score[i]+self.attack_score[i]+self.safe_score[i]));
        bfs_list.sort(key=self.sort_key,reverse=True);

        if bfs_list[0][0] != self.rev_step(rev):
            logging.debug("寻路[避让]:%d 目标:(%d,%d)" % (bfs_list[0][0],tgt[0],tgt[1]));
            return bfs_list[0][0];
        logging.debug("寻路:%d 目标:(%d,%d)" % (self.rev_step(rev),tgt[0],tgt[1]));
        return bfs_list[0][0];
    dist_map : "dict[int,list[list[int]]]";#保存距离，不可达格会是-1
    path_map : "dict[int,list[list[int]]]";#保存“如何走到这一格”，注意这里是ACT的下标，本身格会是-1
    def refresh_all_bfs(self):
        """
        对所有蛇做一次bfs，并清除已死蛇的数据
        【目前仅在自己身上考虑即将吃到的食物】
        """
        self.dist_map,self.path_map = dict(),dict();
        for _snake in self.snakes:
            if _snake.id == self.snkid:
                self.__find_path_bfs(consider_food=True);
            else:
                self.__find_path_bfs(_snake.id);
    def __find_path_bfs(self,snkid : int = -1,consider_food : bool = False):
        """
        跑一次从snkid所在位置到全图的bfs
        考虑了蛇的尾部的移动
        【敌方蛇的check_mov是否应该用不同的time呢？】
        """
        will_log = False;
        if snkid == -1:
            snkid = self.snkid;
        nx,ny = self.ctx.get_snake(snkid).coor_list[0];
        bank_list = [-1 for i in range(100)];
        if consider_food:
            bank_list = self.__bank_siz_list_bfs(snkid);

        self.path_map[snkid] = [[-1 for y in range(self.y_leng)] for x in range(self.x_leng)];
        self.dist_map[snkid] = [[-1 for y in range(self.y_leng)] for x in range(self.x_leng)];
        queue : "list[tuple[int,int,int]]" = [];#(x,y,step)

        queue.append((nx,ny,0));#从起点开始
        self.path_map[snkid][nx][ny],self.dist_map[snkid][nx][ny] = -1,0;

        while len(queue):
            x,y,step = queue[0];
            del queue[0];

            if step > 45:
                will_log = True;

            for i,act in enumerate(ACT):
                tx,ty = x+act[0],y+act[1];
                if not self.check_nstep_norm(tx,ty,step+1,snkid,bank_list[step]):
                    continue;
                if self.dist_map[snkid][tx][ty] == -1:
                    queue.append((tx,ty,step+1));
                    self.path_map[snkid][tx][ty] = i;
                    self.dist_map[snkid][tx][ty] = step+1;
        
        if will_log:
            logging.debug("bfs: %s" % self.dist_map);

    def check_near(self,pos0 : "tuple[int,int]",pos1 : "tuple[int,int]") -> bool:
        """
        检验pos0与pos1是否相邻
        【对pos0==pos1，返回True】
        """
        return max(abs(pos0[0]-pos1[0]),abs(pos0[1]-pos1[1])) <= 1;
    def get_pos_on_snake(self,pos : "tuple[int,int]") -> int:
        x,y = pos;
        snkid = self.game_map.snake_map[x][y];
        snk = self.ctx.get_snake(snkid);
        for i,_pos in enumerate(snk.coor_list):
            if pos == _pos:
                return len(snk.coor_list)-i;
    def get_enclosing_leng(self,snkid : int = -1) -> "tuple[int,int]":
        """
        计算id=snkid的蛇立刻主动进行固化能利用的最大身体长度
        返回(最大长度,对应ACT下标)
        如果无法进行固化，则返回(-1,-1)
        """
        if snkid == -1:
            snkid = self.snkid;

        snk = self.ctx.get_snake(snkid);
        pos = snk.coor_list[0];
        best = (-1,-1);#[maxl,ind]
        for i,act in enumerate(ACT):
            tx,ty = pos[0]+act[0],pos[1]+act[1];
            if tx < 0 or ty < 0 or tx >= 16 or ty >= 16:
                continue;
            if self.game_map.snake_map[tx][ty] != snkid:
                continue;
            if snk.get_len() > 2 and (tx,ty) == snk.coor_list[1]:#防止后退
                continue;
            if snk.get_len() == 2 and (tx,ty) == snk.coor_list[1] and snk.length_bank:#防止后退
                continue;
            leng = snk.get_len() - self.get_pos_on_snake((tx,ty));
            if leng > best[0]:
                best = (leng,i);
        return best;

    def check_nstep_norm(self,tx : int,ty : int,step : int = 1,snkid : int = -1,bank_val : int = -1) -> bool:
        """
        判断id=snkid的蛇在接下来的第step步移动后走到(tx,ty)这一格是否不会被撞死
        """
        if snkid == -1:
            snkid = self.snkid;

        #越界/撞墙
        if tx < 0 or ty < 0 or tx >= 16 or ty >= 16 or self.game_map.wall_map[tx][ty] != -1:
            return False;
        #撞蛇
        blocking_snake = self.game_map.snake_map[tx][ty];
        if blocking_snake == -1:
            return True;
        
        if bank_val == -1:
            bank_val = self.ctx.get_snake(blocking_snake).length_bank;
        elif bank_val != -1 and blocking_snake != self.snkid:
            bank_val = self.ctx.get_snake(blocking_snake).length_bank;#仅在self_blocking时采用override
        leave_time =  self.get_pos_on_snake((tx,ty)) + bank_val;

        if blocking_snake == snkid:#self_blocking
            if leave_time <= step:
                return True;
            return False;
        
        if leave_time < step:
            return True;
        if leave_time > step:
            return False;
        if self.check_first(snkid,blocking_snake):#snkid比blocking先走
            return False;
        return True;
    def check_mov_norm(self,tx : int,ty : int,time : int = 0,snkid : int = -1,bank_val : int = -1) -> bool:
        """
        判断id=snkid的蛇在time时间后走到(tx,ty)这一格是否可行（不会被撞死）
        """
        if snkid == -1:
            snkid = self.snkid;
        snk = self.ctx.get_snake(snkid);

        #越界/撞墙
        if tx < 0 or ty < 0 or tx >= 16 or ty >= 16 or self.game_map.wall_map[tx][ty] != -1:
            return False;
        #撞蛇
        blocking_snake = self.game_map.snake_map[tx][ty];
        self_blocking = 0;
        if blocking_snake == snkid:
            self_blocking = 1;

        if blocking_snake == -1:
            return True;

        if bank_val == -1:
            bank_val = snk.length_bank;
        leave_time =  self.get_pos_on_snake((tx,ty)) + bank_val - self_blocking;
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
        if self.ctx.get_snake_count(self.ctx.get_snake(snkid).camp) >= 4:
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
            wall = self.game_map.wall_map[tx][ty];
            if wall != -1:
                if wall == self.camp:
                    ans[0] += 1;
                else:
                    ans[1] += 1;
            tx += dire[0];
            ty += dire[1];
        return (ans[0],ans[1]);
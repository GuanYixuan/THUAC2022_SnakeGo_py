import re
from tabnanny import check
from adk import *

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
    ctx : Context;
    snakes : "list[Snake]";
    this_snake : Snake;
    game_map : Map;
    x_leng : int;
    y_leng : int;
    snkid : int;
    pos : "tuple[int,int]";

    def __init__(self,ctx : Context,snkid : int):
        self.ctx = ctx;
        self.game_map = ctx.get_map();
        self.x_leng,self.y_leng = self.game_map.length,self.game_map.width;
        self.snakes,self.snkid,self.this_snake = ctx.snake_list,snkid,ctx.get_snake(snkid);
        self.pos = self.this_snake.coor_list[0];
    
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
                if not self.check_mov_norm(tx,ty,snkid):#这里不对
                    continue;
                #还没写完

    # def round_action(self,tgt : "tuple[int,int]"):
    #     """
        
    #     """

    dist_map : "list[list[int]]";#保存距离，不可达格会是-1
    path_map : "list[list[int]]";#保存“如何走到这一格”，注意这里是ACT的下标，本身格会是-1
    def rev_step(self,st : int) -> int:#对行动取反，注意这里是ACT的下标
            return (2,3,0,1)[st];
    def random_step(self):
        '''
        随便走一格，返回ACT的下标
        '''
        x,y = self.pos;
        ind = [0,1,2,3];
        random.shuffle(ind);
        for i in ind:
            if self.check_mov_norm(x+ACT[i][0],y+ACT[i][1]):
                print("随机漫步:",i);
                return i;
        return self.emergency_handle();
    def greedy_step(self,tgt : "tuple[int,int]"):
        '''
        贪心地向tgt走一格，返回ACT的下标
        '''
        x,y =  self.pos;
        dx,dy = tgt[0]-x,tgt[1]-y;

        if dx > 0 and self.check_mov_norm(x+ACT[0][0],y+ACT[0][1]):
            return 0;
        if dx < 0 and self.check_mov_norm(x+ACT[2][0],y+ACT[2][1]):
            return 2;
        if dy > 0 and self.check_mov_norm(x+ACT[1][0],y+ACT[1][1]):
            return 1;
        if dy < 0 and self.check_mov_norm(x+ACT[3][0],y+ACT[3][1]):
            return 3;
        return self.random_step();
    def emergency_handle(self) -> int:
        print("emergency!");
        def calc_leng(tgt : "tuple[int,int]") -> int:#不见得是严格的长度
            for i,pos in enumerate(self.this_snake.coor_list):
                if pos == tgt:
                    return i;
            raise;
        if self.ctx.get_snake_count(self.ctx.current_player) < 4:
            print("紧急处理:分裂");
            return 6 - 1;#分裂
        
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
            leng = calc_leng((tx,ty));
            if leng > best[0]:
                best = [leng,i];
        if best[1] == -9:
            print("紧急处理:",vaild[0]);
            return vaild[0];
        print("紧急处理:",best[1]);
        return best[1];

    def check_item_captured(self,item : Item) -> bool:
        """
        检查物品是否已经被你占住了（可以用身子直接吃掉）
        """
        x,y = item.x,item.y;
        if self.ctx.game_map.snake_map[x][y] != self.snkid:
            return False;
        for i,pos in enumerate(self.this_snake.coor_list):
            if pos == (x,y):
                if item.time - self.ctx.turn < self.this_snake.get_len()-i + self.this_snake.length_bank:
                    return True;
                else:
                    return False;
        raise;

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
        while (x,y) != self.pos:
            if self.path_map[x][y] == -1:
                raise;
            rev = self.rev_step(self.path_map[x][y]);
            x += ACT[rev][0];
            y += ACT[rev][1];
        print("寻路:",self.rev_step(rev));
        return self.rev_step(rev);
    def find_path(self):
        """
        跑一次从snkid所在位置到全图的bfs
        这里认为所有蛇是静态的
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
                if not self.check_mov_norm(tx,ty):#认为所有蛇是静态的
                    continue;
                if self.dist_map[tx][ty] == -1:
                    queue.append((tx,ty,step+1));
                    self.path_map[tx][ty] = i;
                    self.dist_map[tx][ty] = step+1;

    def check_mov_norm(self,tx : int,ty : int) -> bool:
        """
        判断【立刻】走到(tx,ty)是否可行（不会被撞死）
        """
        #越界/撞墙
        if tx < 0 or ty < 0 or tx >= 16 or ty >= 16 or self.ctx.game_map.wall_map[tx][ty] != -1:
            return False;
        #撞蛇
        if self.ctx.get_snake(self.snkid).get_len() == 2:
            if self.ctx.game_map.snake_map[tx][ty] == self.snkid and self.ctx.get_snake(self.snkid).length_bank == 0:
                return True;
            if self.ctx.game_map.snake_map[tx][ty] != -1:
                return False;
            return True;
        else:
            if self.ctx.game_map.snake_map[tx][ty] != -1:
                return False;
            return True;

    # def check_self(self, op : int):
    #     """
    #     :param op: the direction
    #     :return: True if this move is legal, could possibly result in solidification.
    #              False otherwise.
    #     """
    #     x = self.snake.coor_list[0][0] + dx[op]
    #     y = self.snake.coor_list[0][1] + dy[op]
    #     if x < 0 or y < 0 or x >= 16 or y >= 16 or self.ctx.game_map.wall_map[x][y] != -1:
    #         return False
    #     if self.snake.get_len() > 1 and x == self.snake.coor_list[1][0] and y == self.snake.coor_list[1][1]:
    #         return False
    #     if self.ctx.game_map.snake_map[x][y] != -1 and self.ctx.game_map.snake_map[x][y] != self.snake.id:
    #         return False
    #     return True

    
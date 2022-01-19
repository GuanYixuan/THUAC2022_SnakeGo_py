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
    game_map : Map;
    x_leng : int;
    y_leng : int;
    snkid : int;

    def __init__(self,ctx : Context,snkid : int = -1):
        self.ctx = ctx;
        self.game_map = ctx.get_map();
        self.x_leng,self.y_leng = self.game_map.length,self.game_map.width;
        self.snakes,self.snkid = ctx.snake_list,snkid;
    
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
                
    def find_path(self,snkid : int,tgtx : int,tgty: int) -> "tuple[int,int]":
        """
        寻路，从snkid所在位置到(tgtx,tgty)
        这里认为所有蛇是静态的
        返回(下一步走法,距离)
        """
        def rev_step(st : int) -> int:
            st += 1;
            return (-1,3,4,1,2)[st];
        
        nx,ny = self.snakes[snkid].coor_list[0];
        if nx == tgtx and ny == tgty:#已经在终点
            return (-1,0);

        vis = [[0 for y in range(self.y_leng)] for x in range(self.x_leng)];
        queue : "list[tuple[int,int,int]]" = [];#(x,y,step)

        queue.append((tgtx,tgty,0));#从终点开始

        while len(queue):
            x,y,step = queue[0];
            del queue[0];
            vis[x][y] = 1;

            for i,act in enumerate(ACT):
                tx,ty = x+act[0],y+act[1];
                if tx == nx and ty == ny:
                    return (rev_step(i),step+1);
                if not self.check_mov_norm(tx,ty,snkid):#认为所有蛇是静态的
                    continue;
                if not vis[tx][ty]:
                    queue.append((tx,ty,step+1));
        return (-1,-1);

    def check_mov_norm(self,tx : int,ty : int,snkid : int) -> bool:
        """
        判断【立刻】走到(tx,ty)是否可行（不会被撞死）
        """
        #越界/撞墙
        if tx < 0 or ty < 0 or tx >= 16 or ty >= 16 or self.ctx.game_map.wall_map[tx][ty] != -1:
            return False;
        #撞蛇
        if self.snakes[snkid].get_len() == 2:
            if self.ctx.game_map.snake_map[tx][ty] == snkid:
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

    
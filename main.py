# --utf-8--
# n1=[[1,1],[1,1]] n2=[[2,2],[2,2]] 最终情况就是每一个节点管一个数据
# 源切分后是1-256 映射时候需要0-255 (x,y)坐标点数据是y*32+x 原块就是y*32+x+1
# todo 优化 使用散列只是对新来的节点有个坐标 优化就是依照依照当前节点分布情况使用节点密度均衡的方式进行节点-资源点的分配稀缺资源优先
#  分布式的话可能两个节点同时更新 丢失一些新分的节点信息 可以使用同步锁方式 访问就锁完成后解开
# %%
import hashlib
import os
import random
import shutil
from copy import deepcopy

from faker import Faker
from file_split_merge import SplitAndCombineFiles
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator


class ISP:
    """将IP-Host-Port-P2PNode(Socket=端口服务)整合为 IP-Node"""
    ipNode = {}  # 节点{IP:Node,IP:Node,...}
    sourceServer = None
    fk = Faker()

    def __init__(self, sourceServer):
        self.sourceServer = sourceServer
        # todo test====================================================固定测试用例
        self.ipList = ['213.56.183.153', '106.62.251.53', '20.184.218.33', '69.223.34.5', '23.149.97.60',
                       '213.134.16.121', '100.43.62.88', '96.223.37.123', '171.30.70.191', '75.181.239.15',
                       '6.8.96.207', '94.5.10.42', '169.36.64.160', '168.103.101.241', '93.17.116.79', '187.115.178.15',
                       '129.148.61.128', '41.104.122.184', '78.17.210.83', '112.233.34.88', '36.93.133.122',
                       '124.223.12.3', '188.106.173.206', '120.102.167.110', '146.113.73.152', '18.63.151.132',
                       '205.46.91.221', '197.119.179.155', '144.147.231.193', '185.169.223.148', '12.183.155.130',
                       '57.103.101.32', '90.133.95.160', '60.3.168.53', '135.209.210.217', '88.6.116.55',
                       '145.74.13.130', '174.165.114.53', '118.250.218.92', '53.29.53.205']

        # todo test====================================================

    def applyNewNode(self):
        """申请新节点"""
        # todo test====================================================固定测试用例
        # ip = self.ipList.pop(0)
        ip = self.fk.ipv4()  # 随机生成ipv4 # todo 恢复====================================================
        node = CANNode(ip, self.sourceServer, self)
        self.ipNode[ip] = node
        return ip

    def IPExit(self, ip):
        """IP节点退出"""
        self.ipNode.pop(ip)


class SourceServer:
    """SourceServer将文件风格成CAN的数据容量"""
    # 校验文件 含最终合并名
    serverData = './ServerData/'
    original = serverData + 'original/'
    splitOriginal = serverData + 'splitOriginal/'
    chunk = splitOriginal + 'Chunk/'
    CRC = splitOriginal + 'CRC/'
    chunkSum = 256  # 默认资源分256块 空间为16*16

    dataName = ''
    resource = original + dataName
    onLineNode = []

    def __init__(self, dataName):
        """
        dataName文件需要放在./ServerData/original下
        Args:
            dataName:
        """
        if not os.path.exists(self.serverData): os.mkdir(self.resource)
        if not os.path.exists(self.original): os.mkdir(self.original)
        if not os.path.exists(self.splitOriginal): os.mkdir(self.splitOriginal)
        if not os.path.exists(self.chunk): os.mkdir(self.chunk)
        if not os.path.exists(self.CRC): os.mkdir(self.CRC)

        self.dataName = dataName
        self.resource = self.original + '/' + dataName
        if not os.path.exists(self.resource):
            print('所选文件不存在')
            return
        SplitAndCombineFiles().split(self.resource, chunk_size=str(self.chunkSum))  # 分割后的后缀ros 分割和合并不能用同一个对象
        self.moveChunkAndCRC(self.original, self.chunk, self.CRC)

    @staticmethod
    def moveChunkAndCRC(path, chunkPath, CRCPath):
        for file in os.listdir(path):
            if 'CRC.ros' in file:
                shutil.move(path + file, CRCPath + file)
                continue

            if '.ros' in file:
                shutil.move(path + file, chunkPath + file)

    def addNode(self, ip):
        self.onLineNode.append(ip)

    def getAllSpiltResource(self):
        return self.chunk

    def getCRCFile(self):
        return self.resource

    def nodeExit(self, ip):
        self.onLineNode.remove(ip)

    def recycleResource(self, path):
        for c in os.listdir(path):
            shutil.copy(path + c, self.splitOriginal + c)


class CANNode:
    """
        所有进入节点强行当交换节点（义务）
        ip data coordinate坐标
        x坐标使用sha1 y坐标使用MD5 空间由sourceServer.chunkSum定
        data是数据块
    """
    ip = None
    coordinate = None  # [x,y]
    sourceServer = None  # SourceServer
    jurisdiction = []  # 管辖范围 [[[xMin,yMin],[xMax,yMax]],[[xMin,yMin],[xMax,yMax]]]
    isp = None  # ISP
    cachePath = None  # 缓存路径
    neighbor = []  # 邻居的ip列表
    brothers = []
    chunkSum = 0

    def __init__(self, ip: str, sourceServer: SourceServer, isp: ISP):
        # atexit.register(self.exitCAN) 每个都手动调用的话就不用这个函数了
        self.fileName = sourceServer.dataName
        self.chunkSum = sourceServer.chunkSum
        self.ip = ip
        self.sourceServer = sourceServer
        self.isp = isp
        self.coordinate = self.getOwnCoordinate()  # 获取自己的坐标
        self.jurisdiction = []
        self.cachePath = './Cache/' + self.ip.replace('.', '-') + '/'
        self.neighbor = []  # 邻居的ip列表
        self.brothers = []
        if not os.path.exists(self.cachePath): os.mkdir(self.cachePath)
        self.joinToCAN()
        self.sourceServer.addNode(self.ip)

    def joinToCAN(self):  # 加入
        # 若p2p网络中目前没有节点 则从sourceServer下载数据
        if len(self.sourceServer.onLineNode) == 0:
            maxX = maxY = self.sourceServer.chunkSum ** (1 / 2) - 1
            self.jurisdiction.append([[0, 0], [maxX, maxY]])
            sSpiltPath = self.sourceServer.getAllSpiltResource()
            for c in os.listdir(sSpiltPath):
                shutil.copy(sSpiltPath + '/' + c, self.cachePath + '/' + c)
            return True
        else:
            currentJurisdictionIP = self.routeToOwnCoordinates()

            # 若currentJurisdictionIP-Node的坐标与自己相同则
            if self.isp.ipNode[currentJurisdictionIP].coordinate == self.coordinate:
                # 获取兄弟节点
                brotherNode = self.isp.ipNode[currentJurisdictionIP]
                # 通知同坐标节点兄弟"们"加自己同步兄弟节点
                # 复制兄弟的管辖区
                self.jurisdiction = deepcopy(brotherNode.jurisdiction)
                # 兄弟的兄弟'们'的brothers添加自己ip
                for brother in brotherNode.brothers:
                    if self.ip not in self.isp.ipNode[brother].brothers:
                        self.isp.ipNode[brother].brothers.append(self.ip)
                # 兄弟的brothers添加自己ip
                if self.ip not in brotherNode.brothers:
                    brotherNode.brothers.append(self.ip)

                # 邻居的neighbor加自己IP 直接return
                self.neighbor = deepcopy(brotherNode.neighbor)
                for nIP in self.neighbor:
                    if self.ip not in self.isp.ipNode[nIP].neighbor:
                        self.isp.ipNode[nIP].neighbor.append(self.ip)

                #  直接复制管辖区数据Cache
                brotherCachePath = brotherNode.giveShareData()
                for f in os.listdir(brotherCachePath):
                    shutil.copy(brotherCachePath + f, self.cachePath + f)
                return True
            # 否则就是节点不一样而且有邻居 比较大的几种 所以分开
            else:
                # 1.更新自己管辖区域和邻居 同时更新源节点的管辖区
                self.getOwnJurisdictionAndNeighbor(currentJurisdictionIP)
                # 2.通知源节点更新自己的的管辖范围和邻居 传入值是自己管辖区的第一个 因为自己刚加进来第一个就是刚获取的
                self.isp.ipNode[currentJurisdictionIP].newNodeUpdate()
                # 现在添加自己ip为源节点邻居就好了 源节点的兄弟们也添加自己ip为邻居
                self.isp.ipNode[currentJurisdictionIP].neighbor.append(self.ip)
                for bIP in self.isp.ipNode[currentJurisdictionIP].brothers:
                    self.isp.ipNode[bIP].neighbor.append(self.ip)
                # 3.获取属于自己的Cache
                self.getOwnJurisdictionData(currentJurisdictionIP)
                # 4.让原管辖点删除自己已接管的Cache数据
                self.isp.ipNode[currentJurisdictionIP].deleteAlreadyOutData(self.jurisdiction[0])
                return True

    def getOwnCoordinate(self):
        """
        获取自己的坐标 x坐标使用sha1 y坐标使用MD5 一共16*16 0-15
        Returns:
            [x,y]
        """
        # 先用两个Hash进行散列并转换为10进制再映射到0-15 直接取余出来为0-15 再+1则为需要
        x = int(hashlib.sha1(self.ip.encode("utf8")).hexdigest(), 16) % int(self.chunkSum ** (1 / 2))
        y = int(hashlib.md5(self.ip.encode("utf8")).hexdigest(), 16) % int(self.chunkSum ** (1 / 2))
        return [x, y]

    def routeToOwnCoordinates(self):
        """
            得到自己所在的坐标当前是谁在接管，返回这个IP。若和自己的坐标一样返回这个坐标的IP(你俩共同接管同一个资源)。
            Returns:
                IP 目标IP
        """
        p2pEntranceIP = self.sourceServer.onLineNode[
            0]  # todo 恢复random.randint(0, len(self.sourceServer.onLineNode) - 1)]  # 入口地址 固定测试用例
        return self.route(p2pEntranceIP, self.coordinate)

    @staticmethod
    def rectNormalization(vRect):  # 返回标准矩形[坐下坐标,右上坐标]
        rect = deepcopy(vRect)
        if rect[0][0] > rect[1][0]:  # 交换
            swap = rect[1][0]
            rect[1][0] = rect[0][0]
            rect[0][0] = swap
        if rect[0][1] > rect[1][1]:
            swap = rect[1][1]
            rect[1][1] = rect[0][1]
            rect[0][1] = swap
        return rect

    @staticmethod
    def isRectsOverlap(rect1, rect2):  # 标准矩形[坐下坐标,右上坐标] [[rLBX, rLBY], [rRTX, rRTY]]
        if rect1[0][0] > rect2[1][0] or rect2[0][0] > rect1[1][0]: return False
        if rect1[0][1] > rect2[1][1] or rect2[0][1] > rect1[1][1]: return False
        return True

    def route(self, routeIP, goal):
        """
            goal[x,y] 从ISP查目标IP的Node节点，根据其邻居路由到目标IP，递归调用，最终返回goal要分的IP

            Returns:
                IP 目标IP
        """
        # 在当前节点管辖区域的话直接返回这个routeIP
        for j in self.isp.ipNode[routeIP].jurisdiction:
            if (j[0][0] <= goal[0] <= j[1][0]) and (j[0][1] <= goal[1] <= j[1][1]):
                return routeIP

        while True:  # 路由过程
            node = self.isp.ipNode[routeIP]
            nodeC = node.coordinate
            # 对当前节点的邻居遍历查询
            # random.shuffle(node.neighbor) todo 恢复 固定测试用例
            for nIP in node.neighbor:
                nNode = self.isp.ipNode[nIP]
                # 先直接查管辖区域 在管辖区域的话直接返回这个IP
                for j in nNode.jurisdiction:
                    if (j[0][0] <= goal[0] <= j[1][0]) and (j[0][1] <= goal[1] <= j[1][1]):
                        return nIP

                # 若管辖区没有 则检测哪个节点坐标在从当前坐标到目标节点的路径上 再进行下一步路由 nodeC(x,y) nNodeC(x,y) goal(x,y)
                for eJ in nNode.jurisdiction:
                    eJN = self.rectNormalization(eJ)
                    r = self.rectNormalization([nodeC, goal])
                    if self.isRectsOverlap(eJN, r):
                        routeIP = nIP

    def getOwnJurisdictionAndNeighbor(self, ip):
        """
            同时做好了源节点的管辖区更新
            获取自己的管辖区 从之前管辖自己区域的那个节点(ip) ip-node 从self.isp查询
            因为有时候有些相邻区域不是等大小，所以无法直接合并，需要保存成多个块所以 但是等大小的要合并
            区域[[[xMin,yMin],[xMax,yMax]],[[xMin,yMin],[xMax,yMax]]]
            Returns:
                区域
        """
        # 即将为自己分出数据的节点
        ipNode = self.isp.ipNode[ip]
        # 遍历多个管辖块区
        for j in ipNode.jurisdiction:  # [[xMin,yMin],[xMax,yMax]]
            # 判断是否在某管辖块区的内部
            [[xMin, yMin], [xMax, yMax]] = j
            if (xMin <= self.coordinate[0] <= xMax) and (yMin <= self.coordinate[1] <= yMax):
                # 两节点同在一个分区 从两个坐标中间点分开 新节点和旧节点的管辖区都更新
                if (xMin <= ipNode.coordinate[0] <= xMax) and (yMin <= ipNode.coordinate[1] <= yMax):
                    sX, sY = self.coordinate[0], self.coordinate[1]
                    eX, eY = ipNode.coordinate[0], ipNode.coordinate[1]
                    w = abs(ipNode.coordinate[0] - self.coordinate[0])
                    h = abs(ipNode.coordinate[1] - self.coordinate[1])
                    # 同时把源数据点ipNode的管辖区域改掉
                    if w >= h:  # 按照竖着切 w>h 或 w=h
                        if ipNode.coordinate[0] < self.coordinate[0]:  # 源在新左边
                            self.jurisdiction.append([[(sX + eX) // 2 + 1, yMin], [xMax, yMax]])
                            j[1][0] = (sX + eX) // 2
                        else:  # 源在新右边
                            self.jurisdiction.append([[xMin, yMin], [((sX + eX) // 2), yMax]])
                            j[0][0] = (sX + eX) // 2 + 1
                    else:  # 按照横着切 w<h
                        if ipNode.coordinate[1] < self.coordinate[1]:  # 源在新下边
                            self.jurisdiction.append([[xMin, (sY + eY) // 2 + 1], [xMax, yMax]])
                            j[1][1] = (sY + eY) // 2
                        else:  # 源在新上边
                            self.jurisdiction.append([[xMin, yMin], [xMax, ((sY + eY) // 2)]])
                            j[0][1] = (sY + eY) // 2 + 1
                # 若和目标节点不在同一个块区 则直接将块区分给自己
                else:
                    self.jurisdiction.append(deepcopy(j))
                    ipNode.jurisdiction.remove(j)
                break

        # 更新路由表(计算自己邻居) 邻居+
        #  先复制neighbor
        self.neighbor = deepcopy(ipNode.neighbor)  # 注意传的是引用需要
        #  遍历neighbor 根据self.jurisdiction和neighbor的jurisdiction
        self.updateNeighbor()
        #   加入原管辖节点的ip为邻居
        # ipNode.neighbor.append(self.ip) 此时不能添加自己为源节点的邻居 因为后面源节点要更新邻居 自己还没创建成功 去isp查不到自己
        self.neighbor.append(ip)

    def updateNeighbor(self):
        # 根据管辖区和self.neighbor刷新self.neighbor
        # 遍历邻居 邻居中已经和自己不相邻的节点删除其neighbor中的本ip(更新邻居) 同时删除自己neighbor的这些邻居ip
        needRemove = []
        needAppend = []
        for nIP in self.neighbor:
            nNode = self.isp.ipNode[nIP]
            isNeighbor = False
            for nJ in nNode.jurisdiction:  # 遍历nNode的管辖区域[[xMin,yMin],[xMax,yMax]]
                for sJ in self.jurisdiction:
                    [[sXMin, sYMin], [sXMax, sYMax]] = sJ
                    [[nXMin, nYMin], [nXMax, nYMax]] = nJ
                    if (sXMin - 1 == nXMax) and (sYMin <= nYMax and sYMax >= nYMin):  # 自己管辖的 左边界 挨着待验证邻居的 右边界
                        isNeighbor = True
                        break

                    if (sYMin - 1 == nYMax) and (sXMin <= nXMax and sXMax >= nXMin):  # 自己管辖的 下边界 挨着待验证邻居的 上边界
                        isNeighbor = True
                        break

                    if (sXMax + 1 == nXMin) and (sYMin <= nYMax and sYMax >= nYMin):  # 自己管辖的 右边界 挨着待验证邻居的 左边界
                        isNeighbor = True
                        break

                    if (sYMax + 1 == nYMin) and (sXMin <= nXMax and sXMax >= nXMin):  # 自己管辖的 上边界 挨着待验证邻居的 下边界
                        isNeighbor = True
                        break
                if isNeighbor: break
            #   若是邻居 双方互加
            if isNeighbor:
                needAppend.append(nIP)
            #   若不是邻居了 双方互删
            else:
                needRemove.append(nIP)

        for nIP in needAppend:
            if nIP not in self.neighbor:
                self.neighbor.append(nIP)
            if self.ip not in self.isp.ipNode[nIP].neighbor:
                self.isp.ipNode[nIP].neighbor.append(self.ip)

        for nIP in needRemove:
            if nIP in self.neighbor:
                self.neighbor.remove(nIP)
            if self.ip in self.isp.ipNode[nIP].neighbor:
                self.isp.ipNode[nIP].neighbor.remove(self.ip)

    def newNodeUpdate(self):
        """
            添加时新节点通知原节点更新其数据 此函数是源节点执行的
            更新相互邻居 更新兄弟管辖区
        """
        # 更新自己双方邻居
        self.updateNeighbor()

        # 遍历兄弟 让他们都更新管辖区和更新邻居
        for bIP in self.brothers:
            bNode = self.isp.ipNode[bIP]
            # 更新兄弟管辖区
            bNode.jurisdiction = self.jurisdiction
            # 更新兄弟双方邻居
            bNode.updateNeighbor()

    def getOwnJurisdictionData(self, ip):
        """
            Args:
                ip: 原来管自己数据的那个节点IP
            Returns:
                path 返回文件块所在的路径以自己的IP命名
        """
        # 获取自己管辖区域的数据(自己刚加入CAN) 从之前管辖区域那里接管自己该管的数据 存到自己的软件缓存目录下
        ipNodeCachePath = self.isp.ipNode[ip].cachePath
        W = self.chunkSum ** (1 / 2)  # W=H
        for j in self.jurisdiction:  # j=[[xMin,yMin],[xMax,yMax]]
            [[xMin, yMin], [xMax, yMax]] = j
            [[xMin, yMin], [xMax, yMax]] = [[int(xMin), int(yMin)], [int(xMax), int(yMax)]]
            for y in range(yMin, yMax + 1):  # range(s,e+1)生成s...e
                for x in range(xMin, xMax + 1):
                    chunkNum = y * W + x + 1
                    fileChunkName = self.fileName + '-' + str(int(chunkNum)) + '.ros'
                    shutil.copy(ipNodeCachePath + fileChunkName, self.cachePath + fileChunkName)

    def deleteAlreadyOutData(self, outJurisdiction):
        """
        执行此操作之前已经在新节点中更新了管辖区域 然后根据自己的管辖区域删掉不属于自己的Cache
        删除删掉不属于自己的Cache下文件
        """
        W = self.chunkSum ** (1 / 2)  # W=H
        [[xMin, yMin], [xMax, yMax]] = outJurisdiction  # outJurisdiction=[[xMin,yMin],[xMax,yMax]]
        [[xMin, yMin], [xMax, yMax]] = [[int(xMin), int(yMin)], [int(xMax), int(yMax)]]
        for y in range(yMin, yMax + 1):  # range(s,e+1)生成s...e
            for x in range(xMin, xMax + 1):
                chunkNum = y * W + x + 1
                fileChunkName = self.fileName + '-' + str(int(chunkNum)) + '.ros'
                os.remove(self.cachePath + fileChunkName)

    @staticmethod
    def getSourceData(goalPath):
        """

        Args:
            goalPath:

        Returns:

        """
        # todo 将最终合并的文件保存到返回路径下 从源服务器获取校验 共chunkSum个文件 使用管辖区域计算缺少的块 路由到位 获取

        return 'path'

    def giveShareData(self):  # 共享缓存数据
        return self.cachePath

    def exitCAN(self):
        """退出CAN网络"""

        # 最后一个节点了 还要退出 需要将数据返回self.sourceServer
        if len(self.neighbor) == 0:
            self.sourceServer.recycleResource(self.cachePath)
        # 若有同坐标节点则兄弟"们"减去自己 邻居的neighbor消自己 直接退出
        if len(self.brothers) > 0:
            for b in self.brothers:
                self.isp.ipNode[b].brothers.remove(self.ip)
            for ip in self.neighbor:
                self.isp.ipNode[ip].neighbor.remove(self.ip)
        # 没有兄弟节点有邻居
        if (len(self.neighbor) > 0) and (len(self.brothers) == 0):
            # 计算所有邻居中那个邻居的管辖区小然后将自己的管辖区数据分给谁，打乱邻居节点以将每个可能出现的最大同概率在前面
            giveOutIP = None  #
            random.shuffle(self.neighbor)  # 打乱邻居节点以将每个可能出现的最大同概率在前面
            for ip in self.neighbor:
                minS = self.chunkSum + 1  # 最大就是self.chunkSum
                s = 0
                ipJurisdictions = self.isp.ipNode[ip].jurisdiction
                for j in ipJurisdictions:
                    s += (j[1][0] - j[0][0] + 1) * (j[1][1] - j[0][1] + 1)  # [[1,2],[2,3]] 包含4个块
                if s < minS:
                    giveOutIP = ip

            # 调用要交付节点的takeOverNeighborNode() 包括交付目标的兄弟
            self.isp.ipNode[giveOutIP].takeOverNeighborNode(self.jurisdiction, self.cachePath)
            for bIP in self.isp.ipNode[giveOutIP].brothers:
                self.isp.ipNode[bIP].takeOverNeighborNode(self.jurisdiction, self.cachePath)
            # 将giveOutIP与giveOutIP的brother从自己neighbor中删除
            if giveOutIP in self.neighbor:
                self.neighbor.remove(giveOutIP)  # 不能去掉 去掉的话giveOutIP的邻居会加入giveOutIP自己
            for gBIP in self.isp.ipNode[giveOutIP].brothers:
                if gBIP in self.neighbor:
                    self.neighbor.remove(gBIP)

            for nIP in self.neighbor:
                if self.ip in self.isp.ipNode[nIP].neighbor:
                    self.isp.ipNode[nIP].neighbor.remove(self.ip)

                # 邻居节点加入交付IP与其brothers
                if giveOutIP not in self.isp.ipNode[nIP].neighbor:
                    self.isp.ipNode[nIP].neighbor.append(giveOutIP)
                for gBIP in self.isp.ipNode[giveOutIP].brothers:
                    if gBIP not in self.isp.ipNode[nIP].neighbor:
                        self.isp.ipNode[nIP].neighbor.append(gBIP)

                # 将giveOutIP的兄弟节点也加入自己的原邻居
                for bIP in self.isp.ipNode[nIP].brothers:
                    if self.ip in self.isp.ipNode[bIP].neighbor:
                        self.isp.ipNode[bIP].neighbor.remove(self.ip)

                    # 邻居节点加入交付IP与其brothers
                    if giveOutIP not in self.isp.ipNode[bIP].neighbor:
                        self.isp.ipNode[bIP].neighbor.append(giveOutIP)
                    for gBIP in self.isp.ipNode[giveOutIP].brothers:
                        if gBIP not in self.isp.ipNode[bIP].neighbor:
                            self.isp.ipNode[bIP].neighbor.append(gBIP)

        self.sourceServer.nodeExit(self.ip)
        self.isp.IPExit(self.ip)
        shutil.rmtree(self.cachePath)  # 删除自己之前的Cache文件夹

    def takeOverNeighborNode(self, jurisdiction, cachePath):  # 即将退出节点调用的此函数
        """
            接管邻居节点 从node中获取node管辖区域 并将node管的数据从他自己的文件夹下转移到本node的Cache文件下
            Args:
                jurisdiction: CANNode 退出节点传的自己
                cachePath: 托管文件路径
        """
        # 更新管辖范围 并接管 需要计算是否合并 某一维度大小相同则可以合并
        toRemove = []
        for ej in jurisdiction:
            for sj in self.jurisdiction:
                if sj[0][0] == ej[0][0] and sj[1][0] == ej[1][0]:  # 两个管辖区域的X对齐
                    # 合并Y轴
                    if sj[0][1] < ej[0][1]:
                        sj[1][1] = ej[1][1]
                    else:
                        sj[0][1] = ej[0][1]
                    # 删除jurisdiction的ej 对比下一个ej
                    toRemove.append(ej)
                    break
                if sj[0][1] == ej[0][1] and sj[1][1] == ej[1][1]:  # 两个管辖区域的Y对齐
                    # 合并X轴
                    if sj[0][0] < ej[0][0]:
                        sj[1][0] = ej[1][0]
                    else:
                        sj[0][0] = ej[0][0]
                    # 删除jurisdiction的ej 对比下一个ej
                    toRemove.append(ej)
                    break
            if ej not in toRemove:
                self.jurisdiction.append(ej)
                toRemove.append(ej)

        # 将cachePath下的数据从他自己的文件夹下转移到本node的Cache文件下
        for c in os.listdir(cachePath):
            shutil.copy(cachePath + '/' + c, self.cachePath + '/' + c)


# %%
class Ctrl:
    def __init__(self):
        plt.figure(figsize=(10, 8))
        plt.ion()
        self.fk = Faker()
        self.sourceServerEntity = SourceServer(dataName='data.pdf')
        self.ispEntity = ISP(self.sourceServerEntity)
        self.colorDirt = {}

    def changeNetNode(self, ifAdd=True, ip=''):
        # ==========================================================
        plt.cla()
        plt.gca().xaxis.set_major_locator(MultipleLocator(1))
        plt.gca().yaxis.set_major_locator(MultipleLocator(1))
        plt.grid()
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.xlim((-1, 20))
        plt.ylim((-1, 16))
        # ==========================================================
        if ifAdd:
            newIP = self.ispEntity.applyNewNode()
            self.colorDirt[newIP] = self.fk.color()
        else:
            self.ispEntity.ipNode[ip].exitCAN()
            self.colorDirt.pop(ip)

        rectList = []
        nodeIPList = []

        for iIP in self.ispEntity.ipNode:  # 在已存在节点中迭代IP

            [cX, cY] = cCoordinate = self.ispEntity.ipNode[iIP].coordinate
            cJurisdiction = self.ispEntity.ipNode[iIP].jurisdiction  # [[[xMin,yMin],[xMax,yMax]]...]
            cNeighbor = self.ispEntity.ipNode[iIP].neighbor
            print(iIP + '\n\t自己坐标' + str(cCoordinate) + '\n\t管辖区域' + str(cJurisdiction) + '\n\t邻居' + str(cNeighbor))
            # 绘图=================================
            pC = self.colorDirt[iIP]
            for cJ in cJurisdiction:
                [[pXMin, pYMin], [pXMax, pYMax]] = cJ
                pRect = plt.Rectangle((pXMin - 0.4, pYMin - 0.4), pXMax - pXMin + 0.8, pYMax - pYMin + 0.8, color=pC)
                plt.gca().add_patch(pRect)
            plt.gca().add_patch(plt.Circle((cX, cY), 0.15, color='#fff'))
            plt.gca().add_patch(plt.Circle((cX, cY), 0.1, color='#000'))
            rectList.append(pRect)
            nodeIPList.append(iIP)
        plt.legend(rectList, nodeIPList, loc='upper right', frameon=False, prop={'size': 9})
        plt.savefig('./save.jpg')
        plt.show()
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        print('显示完毕')
        # ==========================================================


ctrl = Ctrl()
num = 12
for i in range(0, num):
    ctrl.changeNetNode()  # Add
    print('+++OK', i)
for i in range(0, num):
    keyList = [key for key in ctrl.ispEntity.ipNode.keys()]
    index = random.randint(0, num - 1)

    delIP = keyList[index]
    ctrl.changeNetNode(False, delIP)
    num -= 1
    print()

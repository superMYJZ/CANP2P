# -*- coding: UTF-8 -*-
'''
@Author:Admin
@File:test.py
@DateTime:2021/5/17 16:47
@SoftWare:PyCharm
'''

import random
import shutil

from matplotlib import cm

x = ['2', '213']
x.append('5')
print(x)
x.remove('2')
print(x)

print(random.randint(0, len(x)))

qqq = 'asfsdjgdfm{x},{y}'.format(x="=", y='+++')
print(qqq)


# %%
class A:
    x = 0

    def p(self):
        return


d = {}
a = A()
d.setdefault('2', a)
b = A()
d.setdefault('1', a)
c = A()
d.setdefault('3', a)
d.pop('3')
if d.get('99'):
    d.pop('99')

print(d)

# %%
import random, os

print(random.randint(1, 9))

x = 0.9
a = int(0.9)
print(x)
print(a)

l = ((1, 2), (2, 1))

print(l[0][1])


class A:
    x = [1, 2, 3, 4, 5, 6, 7, 8, 9]


a = A
random.shuffle(a.x)
print(a.x)

# %%
import os

x = [(1, 3), (4, 3), (8, 9)]
x.remove((4, 3))
print(len(x))
ip = '1.2.3.4'
ip = ip.replace('.', '')
print(ip)
print(os.path.exists('./Cache'))
print(os.path.exists('./ipip'))
os.mkdir('./ipip')
os.rmdir('./ipip')

# %%
from faker import Faker

fk = Faker()
ip = fk.ipv4()
ip2 = fk.ipv6()

print(type(ip))
print(ip2)

# %%
x = {'as': 1, 'we': 2}
x.pop('as')
print(x)

# %%
from file_split_merge import SplitAndCombineFiles

# SplitAndCombineFiles().merge(fileP)
# %%
import os, shutil


def moveChunkAndCRC(path, chunkPath, CRCPath):
    for file in os.listdir(path):
        if 'CRC.ros' in file:
            shutil.move(path + file, CRCPath + file)

        if '.ros' in file:
            shutil.move(path + file, chunkPath + file)


path = './Data/'
CRCPath = './ServerData/CRC/'
chunkPath = './ServerData/Chunk/'
moveChunkAndCRC(path, CRCPath, chunkPath)

# %%
import hashlib

ip = '243.1.23.56'
ox = hashlib.sha1(ip.encode("utf8")).hexdigest()
oy = hashlib.md5(ip.encode("utf8")).hexdigest()
print(ox, '---', oy)

x = int(hashlib.sha1(ip.encode("utf8")).hexdigest(), 16)
y = int(hashlib.md5(ip.encode("utf8")).hexdigest(), 16)

print(x, '---', y)


# %%
class B:
    b = ['asd']


class A:
    a = ['123', '234']


a = A()
b = B()

a.a = b.b

print(a.a, '---', b.b)
a.a.append(1)
print(a.a, '---', b.b)
# %%
a = [[1, 2], [3, 4]]
b = []
b = a
for i in b:
    i[0] = 99
    i = [0, 0]
[[a00, a01], [a10, a11]] = a
print(a00, a01, a10, a11)
# %%
57 // 2 + 100
print(abs(-23))
print(abs(3))

x = [2, 3]
y = [[9, 8]]
y.append(x)
print(y)
x[1] = 999
print(y)
x = [888, 666]
print(y)
# %%
x = [i for i in range(2, 8)]
for i in range(2, 19):
    print(i)
print(x)
# %%
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator
import numpy
from faker import Faker

Faker.seed(0)
fk = Faker()
# %%
plt.figure(figsize=(8, 8))
plt.ion()
# %%
plt.cla()
plt.gca().xaxis.set_major_locator(MultipleLocator(1))
plt.gca().yaxis.set_major_locator(MultipleLocator(1))
plt.grid()
plt.xlabel('X')
plt.ylabel('Y')
plt.xlim((-1, 16))
plt.ylim((-1, 16))
plt.gca().add_patch(plt.Rectangle((0 - 0.4, 0 - 0.4), 4 + 0.8, 5 + 0.8, color=fk.color()))
plt.gca().add_patch(plt.Circle((0, 0), 0.15, color='#fff'))
plt.gca().add_patch(plt.Circle((0, 0), 0.1, color='#000'))

# %%
plt.clf()
plt.close()
# plt.show()

# %%
x = [7, 1, 2, 3, 4, 5, 6, 8, 9]
for i in x:
    if i == 3 or i == 4 or i == 7:
        x.remove(i)
    else:
        print(i)

# %%
# 算矩形区域的左下和右上 最终两个点定一个矩形
def rectNormalization(rect):  # 返回标准矩形[坐下坐标,右上坐标]
    if rect[0][0] > rect[1][0]:  # 交换
        swap = rect[1][0]
        rect[1][0] = rect[0][0]
        rect[0][0] = swap
    if rect[0][1] > rect[1][1]:
        swap = rect[1][1]
        rect[1][1] = rect[0][1]
        rect[0][1] = swap
    return rect

print(rectNormalization([[2,4],[6,2]]))


def isRectsOverlap(rect1, rect2):  # 标准矩形[坐下坐标,右上坐标] [[rLBX, rLBY], [rRTX, rRTY]]
    if rect1[0][0] > rect2[1][0] or rect2[0][0] > rect1[1][0]: return False
    if rect1[0][1] > rect2[1][1] or rect2[0][1] > rect1[1][1]: return False
    return True

# -*- coding: UTF-8 -*-
'''
@Author:Admin
@File:febug.py
@DateTime:2021/5/28 20:40
@SoftWare:PyCharm
'''
# %%
x = [7, 1, 2, 3, 4, 5, 6, 8, 9]
toremove = []
for i in x:
    if i == 3 or i == 4 or i == 7:
        toremove.append(i)
    else:
        print(i)

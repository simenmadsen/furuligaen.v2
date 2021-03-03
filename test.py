from numpy.lib.arraysetops import unique
import requests
import pandas as pd
import numpy as np





def getBounusPoints():
    bps = [32, 31, 31, 29, 29, 18, 17]
    bonus = []
    first = False
    second = False
    third = False
    count = 0
    for i in range(len(bps)):
        if first == False:
            while (bps[i] == bps[i+1]):
                bonus.append(3)
                count += 1
            first = True
        elif second == False and count == 1:
            while (bps[i] == bps[i+1]):
                bonus.append(2)
                count += 1
            second = True
        elif third == False and count == 2:
            while (bps[i] == bps[i+1]):
                bonus.append(1)
            third = True
    return bonus

getBounusPoints()

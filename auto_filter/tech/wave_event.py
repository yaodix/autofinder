'''
daily/weekly wave and exist horizon support, the longer the better
'''
import datetime as dt
import pandas as pd
import numpy as np
from  tqdm import tqdm
import os
import sys
import pickle
import mplfinance as mpf
import matplotlib.pyplot as plt
import cv2
cur_file = os.path.abspath(__file__)
start_index = cur_file.find("auto_filter")
pro_path = cur_file[:start_index+11]
sys.path.append(pro_path)

import tech.tech_base as tech_base
import data_utils
import utils

cur_file = os.path.abspath(__file__)
start_index = cur_file.find("auto_filter")
pro_path = cur_file[:start_index+11]
sys.path.append(pro_path)

import tech.tech_base as tech_base
import data_utils

def angelThreePoint(p_center, p1, p2):
  ba = p1 - p_center
  bc = p2 - p_center

  cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
  angle = np.arccos(cosine_angle)

  return np.degrees(angle)

def waveSupportImpl(df_one, pivots, show = False):
  '''
  '''
  price_1 = np.array(df_one["Close"])
  low_pivots_index = [k for k, v in pivots.items() if v == -1]
  high_pivots_index = [k for k, v in pivots.items() if v == 1]
  if (len(low_pivots_index) < 3):
    return False, 0
  if (len(high_pivots_index) < 2):
    return False, 0
  
  # 波谷在波峰前面，否则退出
  if (high_pivots_index[-1] > low_pivots_index[-1]):
    return False, 0
  
  last_price = np.asarray(price_1)[-1]
  last_lowest_pivot_price = np.asarray(price_1)[low_pivots_index[-1]]
  if last_price > 1.05 * last_lowest_pivot_price :
    return False, 0
  
  
  # get support length
  thirdlatest_low_pivot_index = low_pivots_index[-3]
  secondlatest_low_pivot_index = low_pivots_index[-2]
  latest_low_pivot_index = low_pivots_index[-1]
  thirdlatest_low_pivot_price = np.asarray(price_1)[thirdlatest_low_pivot_index]
  secondlatest_low_pivot_price = np.asarray(price_1)[secondlatest_low_pivot_index]
  latest_low_pivot_price = np.asarray(price_1)[latest_low_pivot_index]
  if (thirdlatest_low_pivot_price - secondlatest_low_pivot_price) / thirdlatest_low_pivot_price > 0.0 or \
     (secondlatest_low_pivot_price - latest_low_pivot_price) / secondlatest_low_pivot_price > 0.03:
    return False, 0
  
  #fit line
  support_price = np.array([thirdlatest_low_pivot_price, secondlatest_low_pivot_price, latest_low_pivot_price])
  mean_support_price = np.mean(support_price)
  diff_sum = abs(thirdlatest_low_pivot_price-mean_support_price)/ thirdlatest_low_pivot_price + \
             abs(secondlatest_low_pivot_price-mean_support_price)/ secondlatest_low_pivot_price + \
             abs(latest_low_pivot_price-mean_support_price)/ latest_low_pivot_price

  
  return  True, diff_sum
  
def angleRefHorizonRatio(code_value, start_date, mid_date):
    start_index = [i for i, date in enumerate(code_value["Date"]) if date == start_date]
    mid_index = [i for i, date in enumerate(code_value["Date"]) if date == mid_date]
    price_start = code_value['Close'].iloc[start_index[0]]
    price_mid = code_value['Close'].iloc[mid_index[0]]
    price_end = code_value['Close'].iloc[-1]
    
    angle_end = angelThreePoint(np.array([start_index[0], price_start]),
                            np.array([len(code_value["Date"]), price_start]),
                            np.array([len(code_value["Date"]), price_end]))
    angle_mid = angelThreePoint(np.array([start_index[0], price_start]),
                            np.array([mid_index[0], price_start]),
                            np.array([mid_index[0], price_mid]))
    price_ratio_start = abs(price_end - price_start) / price_start
    price_ratio_mid = abs(price_end - price_mid) / price_mid
    
    return max(angle_end, angle_mid), max(price_ratio_start, price_ratio_mid)

param_config = {
  "daily": {
    "raise_ratio": 0.103,
    "decade_ratio": 0.09
  },
  "weekly": {
    "raise_ratio": 0.15,
    "decade_ratio": 0.11
  }
}
def GetWaveSupportDaily(df_dict, order_cnt = 40, show = False):
  slope_dict = {}
  horizon_dict = {}
  pivots_cnt_dict = {}
  code_list = []

  print("daily wave support")
  for code, value in tqdm(df_dict.items()):
    pivots = tech_base.get_pivots(value["Close"],  param_config["daily"]["raise_ratio"], param_config["daily"]["decade_ratio"])
    sel, diff_ratio = waveSupportImpl(value, pivots, show=show)
    if sel:
      horizon_dict[code] = diff_ratio
      # data_utils.plot_pivots(value["Close"], pivots)
      # data_utils.plot_pivot_line(value["Close"], pivots)
      # plt.show()

  hor_sort_dict =  dict(sorted(horizon_dict.items(), key=lambda x: x[1], reverse=False))
  hor_sort_dict_20 = dict(list(hor_sort_dict.items())[:order_cnt])
  
  return hor_sort_dict_20

def GetWaveSupportWeekly(df_dict, order_cnt = 10, show = False):
  slope_dict = {}
  horizon_dict = {}
  pivots_cnt_dict = {}
  for code, value in df_dict.items():
    len, start_date, mid_date, pivots_cnt = waveSupportImpl(value, param_config["weekly"]["raise_ratio"], param_config["weekly"]["decade_ratio"],show=show)
    if len > 10:
      angle, ratio= angleRefHorizonRatio(value, start_date, mid_date)
      if angle < 5 and ratio < 0.1:
        horizon_dict[code] = len
        pivots_cnt_dict[code] = pivots_cnt
      else:
        slope_dict[code] = len      
        pivots_cnt_dict[code] = pivots_cnt
  
  hor_sort_dict =  dict(sorted(horizon_dict.items(), key=lambda x: x[1], reverse=True))
  hor_sort_dict_20 = dict(list(hor_sort_dict.items())[:order_cnt])
  hor_sort_dict_20 = dict(sorted(hor_sort_dict_20.items(), key=lambda x: pivots_cnt_dict[x[0]]))
  
  slope_sort_dict =  dict(sorted(slope_dict.items(), key=lambda x: x[1], reverse=True))
  slope_sort_dict_20 = dict(list(slope_sort_dict.items())[:order_cnt])
  slope_sort_dict_20 = dict(sorted(slope_sort_dict_20.items(), key=lambda x: pivots_cnt_dict[x[0]]))
  
  
  return hor_sort_dict_20, slope_sort_dict_20


test_map = {
  # "600855": ["20240911"],  #zhong chong gufen
  # "001965": ["20241127"],  
  "601928": ["20241127"],  
  # "603050": ["20240126"],  # 缠+突破

}

def test():
  pass

if __name__ == '__main__':
  df_dict_daily = data_utils.LoadPickleData(pro_path+"/sec_data/daily.pickle")
  df_dict_weekly = data_utils.LoadPickleData(pro_path+"/sec_data/weekly.pickle")
  test_cnt = 0
  for key, val in test_map.items():
    test_cnt += val.__len__()

  test_dict = {}
  for key, val in test_map.items():
    test_dict[key] = df_dict_daily[key]
    for date in val:
      end_day = dt.datetime.date(dt.datetime.strptime(date, "%Y%m%d"))
      test_dict[key] = test_dict[key][test_dict[key]["Date"] <= end_day]
    
  # test_dict = df_dict_weekly
  test_dict = df_dict_daily
  hor20m = GetWaveSupportDaily(test_dict, show=False)
  # hor20m, slope20 = GetWaveSupportWeekly(test_dict, show=False)
  save_dir = utils.getProjectPath("auto_filter")+ "/workdata/"

  print(f"save pic hor {hor20m}\n")
  cnt = 0
  for code, ss in tqdm(hor20m.items()):
    cnt += 1
    df = test_dict[code]
    data_utils.show_stock_data_eastmoney(code, test_dict[code], save_dir= save_dir, predix="daily_hor_"+f"{cnt:03}_", days=150)

  print(f"hor {hor20m}\n")
  # print(f"slope {slope20}")

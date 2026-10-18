import pandas as pd

df = pd.read_excel("output/bares_com_geohash.xlsx")
#df = pd.read_excel("input/bares.xlsx")
print(list(pd.read_excel('output/bares_com_geohash.xlsx', nrows=0).columns))
print(df.head())
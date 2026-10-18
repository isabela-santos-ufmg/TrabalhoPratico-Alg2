import pandas as pd

df = pd.read_excel("output/bares_com_geohash.xlsx")
#df = pd.read_excel("input/bares.xlsx")
print(list(pd.read_excel("output/bares_com_geohash.xlsx", nrows=0).columns))
print(df.head())
"""
import geopandas as gpd

arquivo = gpd.read_file("data/input/BAIRRO_OFICIAL.shp", rows=5)

print("=" * 50)
print("Colunas disponíveis no shapefile:")
print(arquivo.columns.tolist())
print("=" * 50)

print(arquivo.head())

"""
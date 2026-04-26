import pandas as pd

df = pd.read_csv('relations_final.csv')

df_dedup = df.drop_duplicates()

df_dedup.to_csv('relations_final_dedup.csv', index=False, encoding='utf-8-sig')

print(f"去重前: {len(df)} 行")
print(f"去重后: {len(df_dedup)} 行")
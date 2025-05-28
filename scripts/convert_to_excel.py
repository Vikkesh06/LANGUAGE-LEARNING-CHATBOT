# -*- coding: utf-8 -*-
import pandas as pd

# Read the CSV file
df = pd.read_csv('questions.csv')

# Save to Excel
df.to_excel('chinese_questions.xlsx', index=False, engine='openpyxl') 
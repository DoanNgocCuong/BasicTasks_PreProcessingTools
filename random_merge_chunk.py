import pandas as pd
import random

def merge_chunks(input_file, sheet_name, num_rows_merger, created_num_rows):
    # Load the Excel file
    df = pd.read_excel(input_file, sheet_name=sheet_name)
    
    # Initialize an empty list to store the merged data
    merged_data = []
    
    # Loop through the range of created_num_rows
    for i in range(created_num_rows):
        # Randomly select num_rows_merger rows from the original data
        random_rows = random.sample(range(len(df)), num_rows_merger)
        # Merge the 'ID Chunking' and 'Chunking' columns for the selected rows
        merged_id_chunking = ', '.join(df.iloc[random_rows]['ID Chunking'].astype(str).values)
        merged_chunk = ', '.join(df.iloc[random_rows]['Chunking'].values)
        
        # Sort the selected rows by 'ID Chunking'
        sorted_rows = df.iloc[random_rows].sort_values(by='ID Chunking')
        
        # Merge the 'ID Chunking' and 'Chunking' columns for the sorted rows
        merged_id_chunking = ', '.join(sorted_rows['ID Chunking'].astype(str).values)
        merged_chunk = '\n-----------\n'.join(sorted_rows['Chunking'].values)
        
        # Append the merged data to the list
        merged_data.append((merged_id_chunking, merged_chunk))
    
    # Create a DataFrame from the merged data
    merged_df = pd.DataFrame({'ID Chunking': [item[0] for item in merged_data], 'Chunking': [item[1] for item in merged_data]})
    print(f"Created {len(merged_df)} rows")
    return merged_df

file_path = '3. Document Chunking.xlsx'
sheet_name = 'Chunking-MaiAnh'
# Corrected function call to match the parameters
all_merged_data = []
for i in range(2, 3):
    merged_df = merge_chunks(input_file=file_path, sheet_name=sheet_name, num_rows_merger=i, created_num_rows=200)
    all_merged_data.append(merged_df)

# Concatenate all merged DataFrames
final_merged_df = pd.concat(all_merged_data, ignore_index=True)

# Save the merged data to a new Excel file
final_merged_df.to_excel('merged_chunks.xlsx', index=False)
print("Merged data saved to merged_chunks.xlsx")
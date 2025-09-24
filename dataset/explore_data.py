import pandas as pd

def explore_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        print(f"Successfully read {file_path}")
        print("First 5 rows:")
        print(df.head())
        print("\nColumn Names:")
        print(df.columns)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

if __name__ == "__main__":
    explore_excel("Old Dataset/Documents/refined_patient_data_1000.xlsx")
    explore_excel("Old Dataset/Documents/medical_patient_transcript(100).xlsx")
    explore_excel("Old Dataset/Documents/Medical_Reports.xlsx")
    explore_excel("Old Dataset/Documents/medical_image_descriptions.xlsx")
    explore_excel("Old Dataset/Documents/image_transcription.xlsx") 
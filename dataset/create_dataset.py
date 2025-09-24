import os
import pandas as pd
import re
import sqlite3
import random
from faker import Faker
import shutil

def get_image_paths(root_folder):
    image_paths = {}
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    image_id = int(os.path.splitext(filename)[0])
                    if image_id not in image_paths:
                        image_paths[image_id] = []
                    image_paths[image_id].append(os.path.join(dirpath, filename))
                except ValueError:
                    # Handle cases where filename is not a number
                    pass
    return image_paths

def parse_transcription(transcription):
    data = {}
    if not isinstance(transcription, str):
        return data

    data['Description'] = transcription

    # Try to parse key-value format first from Medical_Reports.xlsx
    matches = re.findall(r'-\s*(.*?):\s*(.*?)\n', transcription)
    if matches:
        key_value_data = {key.strip().replace(' ', '').lower(): value.strip() for key, value in matches}
        
        if 'age' in key_value_data and key_value_data['age'].isdigit():
            data['Age'] = int(key_value_data['age'])
        if 'gender' in key_value_data:
            data['Gender'] = key_value_data['gender']
        if 'allergies' in key_value_data:
            data['Allergies'] = key_value_data['allergies']
        if 'medications' in key_value_data:
            data['Medicines'] = key_value_data['medications']
        if 'pastmedicalhistory' in key_value_data:
            data['PastMedicalHistory'] = key_value_data['pastmedicalhistory']
        if 'assessment' in key_value_data:
            data['Assessments'] = key_value_data['assessment']
        if 'diagnosis' in key_value_data:
            data['Diagnosis'] = key_value_data['diagnosis']
        if 'procedures' in key_value_data:
            data['Procedures'] = key_value_data['procedures']
        
        # If we found key-value data, we can return early
        return data

    # Fallback for other formats
    age_match = re.search(r'(\d+)-year-old', transcription)
    if age_match:
        data['Age'] = int(age_match.group(1))

    gender_match = re.search(r'-year-old\s(.*?)\s', transcription)
    if gender_match:
        gender_full = gender_match.group(1).lower()
        if 'female' in gender_full:
            data['Gender'] = 'Female'
        elif 'male' in gender_full:
            data['Gender'] = 'Male'

    allergies_match = re.search(r'allergies:(.*?)\n', transcription, re.IGNORECASE)
    if allergies_match:
        data['Allergies'] = allergies_match.group(1).strip()
    
    medicines_match = re.search(r'medications:(.*?)\n', transcription, re.IGNORECASE)
    if medicines_match:
        data['Medicines'] = medicines_match.group(1).strip()

    history_match = re.search(r'past medical history:(.*?)\n', transcription, re.IGNORECASE)
    if history_match:
        data['PastMedicalHistory'] = history_match.group(1).strip()
        
    assessment_match = re.search(r'assessment:(.*?)\n', transcription, re.IGNORECASE)
    if assessment_match:
        data['Assessments'] = assessment_match.group(1).strip()
        
    diagnosis_match = re.search(r'diagnosis:(.*?)\n', transcription, re.IGNORECASE)
    if diagnosis_match:
        data['Diagnosis'] = diagnosis_match.group(1).strip()
        
    procedures_match = re.search(r'procedures:(.*?)\n', transcription, re.IGNORECASE)
    if procedures_match:
        data['Procedures'] = procedures_match.group(1).strip()

    return data


def create_new_dataset(image_paths, num_rows=300):
    image_df = pd.read_excel('Old Dataset/Documents/image_transcription.xlsx')
    reports_df = pd.read_excel('Old Dataset/Documents/Medical_Reports.xlsx')
    refined_df = pd.read_excel('Old Dataset/Documents/refined_patient_data_1000.xlsx')
    
    merged_df = image_df.merge(reports_df, on='PATIENT ID', how='left', suffixes=('', '_report'))
    merged_df = merged_df.merge(refined_df, on='PATIENT ID', how='left', suffixes=('', '_refined'))

    new_data = []
    fake = Faker()

    # --- Medical Scenarios for Synthetic Data ---
    medical_scenarios = [
        {
            'Department': 'Cardiology',
            'Diagnosis': 'Myocardial Infarction',
            'Procedures': 'Angioplasty',
            'Medicines': ['Lisinopril', 'Simvastatin', 'Aspirin']
        },
        {
            'Department': 'Neurology',
            'Diagnosis': 'Cerebral Stroke',
            'Procedures': 'Craniotomy',
            'Medicines': ['Warfarin', 'Mannitol', 'Nimodipine']
        },
        {
            'Department': 'Oncology',
            'Diagnosis': 'Lung Cancer',
            'Procedures': 'Chemotherapy',
            'Medicines': ['Cisplatin', 'Etoposide', 'Bevacizumab']
        },
        {
            'Department': 'Orthopedics',
            'Diagnosis': 'Femur Fracture',
            'Procedures': 'Open Reduction Internal Fixation',
            'Medicines': ['Morphine', 'Cefazolin', 'Enoxaparin']
        },
        {
            'Department': 'Pulmonology',
            'Diagnosis': 'Pneumonia',
            'Procedures': 'Bronchoscopy',
            'Medicines': ['Azithromycin', 'Ceftriaxone', 'Albuterol']
        }
    ]

    # Process existing data first
    existing_patient_ids = set()
    for _, row in merged_df.iterrows():
        patient_id = row['PATIENT ID']
        existing_patient_ids.add(patient_id)
        
        transcription = row.get('PATIENT TRANSCRIPTION_report')
        if pd.isna(transcription):
            transcription = row.get('PATIENT TRANSCRIPTION_refined')
        if pd.isna(transcription):
            transcription = row.get('PATIENT TRANSCRIPTION')

        parsed_data = parse_transcription(transcription)

        image_id = row['Image ID']
        image_path_list = image_paths.get(image_id)
        old_path = random.choice(image_path_list) if image_path_list else None
        
        new_path = None
        if old_path:
            filename = os.path.basename(old_path)
            category = os.path.basename(os.path.dirname(old_path))
            new_path = os.path.join('images', category, filename)

        # --- Fill missing data for existing records ---
        diagnosis = parsed_data.get('Diagnosis')
        procedures = parsed_data.get('Procedures')
        department = parsed_data.get('Department')
        medicines = parsed_data.get('Medicines')

        if not diagnosis or not procedures:
            scenario = random.choice(medical_scenarios)
            diagnosis = scenario['Diagnosis']
            procedures = scenario['Procedures']
            department = scenario['Department']
            medicines = ', '.join(scenario['Medicines'])
        
        data_row = {
            'PatientID': patient_id,
            'Name': fake.name(),
            'Age': parsed_data.get('Age', random.randint(20, 80)),
            'Gender': parsed_data.get('Gender', random.choice(['Male', 'Female'])),
            'TreatmentDate': fake.date_between(start_date='-2y', end_date='today').strftime("%Y-%m-%d"),
            'Allergies': parsed_data.get('Allergies', random.choice(['Penicillin', 'Peanuts', 'None'])),
            'Description': parsed_data.get('Description'),
            'Medicines': medicines,
            'Assessments': parsed_data.get('Assessments', fake.sentence(nb_words=10)),
            'PastMedicalHistory': parsed_data.get('PastMedicalHistory', random.choice(['Hypertension', 'Diabetes Type 2', 'None'])),
            'DoctorName': f'Dr. {fake.last_name()}',
            'Department': department,
            'Diagnosis': diagnosis,
            'Procedures': procedures,
            'FollowUpDate': fake.date_between(start_date='today', end_date='+1y').strftime("%Y-%m-%d"),
            'ImagePath': new_path
        }
        new_data.append(data_row)

    # Generate additional synthetic data
    num_to_generate = num_rows - len(new_data)
    if num_to_generate > 0:
        for i in range(num_to_generate):
            patient_id = f"M{1000 + i}"
            while patient_id in existing_patient_ids:
                i += 1
                patient_id = f"M{1000 + i}"
            existing_patient_ids.add(patient_id)

            scenario = random.choice(medical_scenarios)
            age = random.randint(20, 80)
            gender = random.choice(['Male', 'Female'])
            history = random.choice(['Hypertension', 'Diabetes Type 2', 'Asthma', 'None'])
            
            description = (f"A {age}-year-old {gender.lower()} presented with symptoms consistent with {scenario['Diagnosis']}. "
                           f"Past medical history includes {history}. "
                           f"The patient underwent {scenario['Procedures']} and was prescribed {', '.join(scenario['Medicines'])}.")

            image_id = random.choice(list(image_paths.keys()))
            old_path = random.choice(image_paths[image_id]) if image_paths.get(image_id) else None
            
            new_path = None
            if old_path:
                filename = os.path.basename(old_path)
                category = os.path.basename(os.path.dirname(old_path))
                new_path = os.path.join('images', category, filename)

            data_row = {
                'PatientID': patient_id,
                'Name': fake.name(),
                'Age': age,
                'Gender': gender,
                'TreatmentDate': fake.date_between(start_date='-2y', end_date='today').strftime("%Y-%m-%d"),
                'Allergies': random.choice(['Penicillin', 'Peanuts', 'Dust Mites', 'Latex', 'None']),
                'Description': description,
                'Medicines': ', '.join(scenario['Medicines']),
                'Assessments': fake.sentence(nb_words=15),
                'PastMedicalHistory': history,
                'DoctorName': f'Dr. {fake.last_name()}',
                'Department': scenario['Department'],
                'Diagnosis': scenario['Diagnosis'],
                'Procedures': scenario['Procedures'],
                'FollowUpDate': fake.date_between(start_date='today', end_date='+1y').strftime("%Y-%m-%d"),
                'ImagePath': new_path
            }
            new_data.append(data_row)

    new_df = pd.DataFrame(new_data)
    
    output_path = os.path.join('documents', 'clinical_data.xlsx')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    new_df.to_excel(output_path, index=False)
    
    print(f"New dataset created at {output_path}")
    return new_df

def generate_sql_file(df):
    db_path = os.path.join('documents', 'clinical_data.db')
    sql_path = os.path.join('documents', 'clinical_data.sql')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        PatientID TEXT PRIMARY KEY,
        Name TEXT,
        Age INTEGER,
        Gender TEXT,
        TreatmentDate TEXT,
        Allergies TEXT,
        Description TEXT,
        Medicines TEXT,
        Assessments TEXT,
        PastMedicalHistory TEXT,
        DoctorName TEXT,
        Department TEXT,
        Diagnosis TEXT,
        Procedures TEXT,
        FollowUpDate TEXT,
        ImagePath TEXT
    )
    ''')

    # Insert data
    for _, row in df.iterrows():
        cursor.execute('''
        INSERT OR REPLACE INTO patients (PatientID, Name, Age, Gender, TreatmentDate, Allergies, Description, Medicines, Assessments, PastMedicalHistory, DoctorName, Department, Diagnosis, Procedures, FollowUpDate, ImagePath)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(row.fillna('')))

    conn.commit()
    
    # Save to SQL file
    with open(sql_path, 'w') as f:
        for line in conn.iterdump():
            f.write('%s\n' % line)
            
    conn.close()
    print(f"SQL file generated at {sql_path}")


if __name__ == '__main__':
    # Create new directory structure
    print("Setting up new directory structure...")
    os.makedirs('documents', exist_ok=True)
    if os.path.exists('images'):
        shutil.rmtree('images')
    shutil.copytree('Old Dataset/Images', 'images')
    print("Image files copied to /images directory.")

    image_paths = get_image_paths('Old Dataset/Images')
    print(f"Found {len(image_paths)} images with unique names.")
    
    new_df = create_new_dataset(image_paths, num_rows=300)
    print("New dataset summary:")
    print(new_df.info())
    
    generate_sql_file(new_df) 
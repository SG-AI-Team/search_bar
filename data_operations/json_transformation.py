
def transform_program_data(program_data):
    program_dict = dict()
    for program in program_data:
        program_dict[program['program_id']] = program
    return program_dict

def transform_school_data(school_data):
    school_dict = dict()
    for school in school_data:
        school_dict[school['school_id']] = school
    return school_dict

def transform_intake_data(intake_data):
    intake_dict = dict()
    for intake in intake_data:
        intake_dict[intake['program_id']] = intake
    return intake_dict

def transform_specilization_data(specilization_data):
    transformed_specilization_dict = dict()
    for specilization in specilization_data:
        pid = specilization['program_id']
        if pid not in transformed_specilization_dict:
            transformed_specilization_dict[pid] = []
        transformed_specilization_dict[pid].append(specilization['specialization'])
    return transformed_specilization_dict
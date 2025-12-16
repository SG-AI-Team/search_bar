from json_transformation import *
from parent_json_generator import *
from langchain_core.documents import Document
import re


def contains_masters_degree_terms(text):
    """
    Check if text contains any master's degree related terms or the substring " x ".
    
    Args:
        text (str): The text to search in
        
    Returns:
        bool: True if any master's degree term or " x " is found, False otherwise
    """
    if not text:
        return False
    
    # Regex pattern to match all the master's degree terms and " x "
    masters_regex = r'(?i)(MSc|MBA|All\s+Masters?\s+of\s+Science\s+are\s+available|Master|Mastères?\s+Spécialisés?®?|All\s+MSc\s+are\s+available|Double\s+Diplôme|Triple\s+diplôme|Dual\s+degree|MCs)|\s+x\s+'
    
    return bool(re.search(masters_regex, text))

def convert_list_to_string(l):
    s = ','.join(item for item in l )
    return s 

def convert_entry_level_to_string(el):
    """Convert entry level list to string format"""
    if not el:  # Handle empty list
        return []
    el_dict = {"BAC":"0","BAC1":"1","BAC2":"2","BAC3":"3","BAC4":"4", "BAC5":"5"}
    converted = []
    for item in el:
        if item in el_dict:
            converted.append(el_dict[item])
        else:
            converted.append(str(item))  # Fallback for unknown values
    return converted

def normalize_name(name):
    """Normalize names for better matching"""
    if not name:
        return ''
    return name.strip().lower()

def format_entity_values(values, entity_name):
    # Handle empty or None values
    if not values or (isinstance(values, list) and len(values) == 0):
        return f"{entity_name} Not specified"
    
    if isinstance(values, list):
        if len(values) == 1:
            return f"**{entity_name}:** {values[0]}"
        else:
            formatted_lines = [f"**{entity_name}:** {values[0]}"]
            for value in values[1:]:
                formatted_lines.append(f"**{entity_name}:** {value}")
            return '\n'.join(formatted_lines)
    else:
        return f"**{entity_name}:** {values}"

def create_program_key(program_name, school_id):
    """Create a unique key combining program name and school ID"""
    normalized_name = normalize_name(program_name)
    return f"{normalized_name}_{school_id}"

program_lookup = {}
school_lookup = {}

def extract_unique_values(intakes, field_name):
    values = []
    for intake in intakes:
        value = intake.get(field_name)
        if value:
            if isinstance(value, list):
                values.extend(value)
            else:
                values.append(value)
    return list(set(values))

def generate_md_json(program_parent, program_data, transformed_program_data, transformed_school_data, intake_data, transformed_intake_data, transformed_specilization_data):
    final_list_of_json_for_markdown = []
    program_ids_list = [program['program_id'] for program in program_data]
    program_ids_in_intakes = list(transformed_intake_data.keys())
    program_intake_groups = {}
    
    # Group intakes by program_id
    for intake in intake_data:
        pid = intake['program_id']
        if pid not in program_intake_groups:
            program_intake_groups[pid] = []
        program_intake_groups[pid].append(intake)
    
    # Use set to track processed program-school combinations
    processed_programs = set()
    
    for pid in program_ids_in_intakes:
        if pid in program_ids_list:
            school_id = transformed_program_data[pid]['school_id']
            
            # Skip excluded schools
            if school_id in [55006, 55007]:
                continue
            
            # Create unique identifier for program-school combination
            program_school_key = f"{pid}_{school_id}"
            
            # Skip if already processed
            if program_school_key in processed_programs:
                continue
            
            processed_programs.add(program_school_key)
            
            # Initialize the dictionary for this program
            dict_to_insert = {}
            
            intakes_for_program = program_intake_groups.get(pid, [])
            campuses = extract_unique_values(intakes_for_program, 'campus')
            entry_levels = extract_unique_values(intakes_for_program, 'entry_level')
            program_intakes = extract_unique_values(intakes_for_program, 'program_intake')
            intake_languages = extract_unique_values(intakes_for_program, 'intake_language')
            duration_years = extract_unique_values(intakes_for_program, 'duration')
            
            dict_to_insert['program_name'] = transformed_program_data[pid]['program_name']
            dict_to_insert['campus'] = campuses
            dict_to_insert['price'] = program_parent[pid]['price']
            dict_to_insert['entry_level'] = entry_levels
            dict_to_insert['intake'] = program_intakes
            dict_to_insert['language'] = intake_languages
            dict_to_insert['school_name'] = transformed_school_data[transformed_program_data[pid]['school_id']]['school_name']
            dict_to_insert['country'] = transformed_school_data[transformed_program_data[pid]['school_id']]['country_tenant_code']
            dict_to_insert['field_of_study'] = program_parent[pid]["school_type"]
            dict_to_insert['duration'] = max(duration_years) if duration_years else 0
            
            if transformed_school_data[transformed_program_data[pid]['school_id']].get('school_metadata') is not None and transformed_school_data[transformed_program_data[pid]['school_id']].get('school_metadata').get('rankings').get('average_fr_rank') is not None: 
                dict_to_insert['rank'] = transformed_school_data[transformed_program_data[pid]['school_id']].get('school_metadata').get('rankings').get('average_fr_rank') 
            else:
                dict_to_insert['rank'] = 0.0
                
            if pid in list(transformed_specilization_data.keys()):
                dict_to_insert['specialization'] = transformed_specilization_data[pid]
            else:
                dict_to_insert['specialization'] = None 
                
            final_list_of_json_for_markdown.append(dict_to_insert)
    
    return final_list_of_json_for_markdown



def convert_single_specialization_to_markdown(program, specialization):
    """Convert a single specialization to markdown format"""
    school_name = program['school_name']
    field_of_study = program['field_of_study']
    country = program['country']
    city = format_entity_values(program['campus'], "City")
    price = program['price']
    entry_level = format_entity_values(convert_entry_level_to_string(program['entry_level']), 'Entry Level')
    teaching_language = format_entity_values(program['language'], "Program Language")
    intake = format_entity_values(program['intake'], "Intake")
    markdown_template = f"""
## Specialization Overview
**Specialization:** {specialization}
**School:** {school_name}
**Field of Study:** {field_of_study}

## Location Details
**Country:** {country}
{city}

## Program Information
{teaching_language}
{entry_level}
**Price:** {price}
{intake}

---
"""
    return markdown_template

def convert_single_program_to_markdown(program):
    """Convert a single program to markdown format"""
    program_name = program['program_name']
    school_name = program['school_name']
    field_of_study = program['field_of_study']
    country = program['country']
    city = format_entity_values(program['campus'], "**City:**")
    price = program['price']
    entry_level = format_entity_values(convert_entry_level_to_string(program['entry_level']), '**Entry Level:**')
    teaching_language = format_entity_values(program['language'], "**program Language:**")
    intake = format_entity_values(program['intake'], "**Intake:**")
    specilization = program['specialization']
    
    if specilization is not None:
        markdown_template = f"""
# {program_name}

## Program Overview
**Program Name:** {program_name}
**School:** {school_name}
**Field of Study:** {field_of_study}

## Location Details
**Country:** {country}
{city}

## Program Information
{teaching_language}
{entry_level}
**Price:** {price}
{intake}
**specialization:** {specilization}

---
"""
    else:
        markdown_template = f"""
# {program_name}

## Program Overview
**Program Name:** {program_name}
**School:** {school_name}
**Field of Study:** {field_of_study}

## Location Details
**Country:** {country}
{city}

## Program Information
{teaching_language}
{entry_level}
**Price:** {price}
{intake}

"""

    return markdown_template

def create_specilizations_document_objects(final_list_of_json_for_markdown, school_data, program_data):
    individual_specialization_objects = []
    matched_specializations = set()
    
    # Populate the lookup dictionaries if they're empty
    if not program_lookup or not school_lookup:
        # Build school_lookup
        for school in school_data:
            school_lookup[normalize_name(school['school_name'])] = str(school['school_id'])
        
        # Build program_lookup
        for program in program_data:
            compound_key = create_program_key(program['program_name'], program['school_id'])
            program_lookup[compound_key] = str(program['program_id'])
    
    for program in final_list_of_json_for_markdown:
        if program['specialization'] is not None:
            program_name = program['program_name']
            school_name = program['school_name']
            school_id = school_lookup.get(normalize_name(school_name))
            program_id = None
            
            if school_id:
                compound_key = create_program_key(program_name, school_id)
                program_id = program_lookup.get(compound_key)
            
            if program_id and school_id:
                specializations = program['specialization']
                
                if isinstance(specializations, list):
                    for specialization in specializations:
                        unique_key = f"{program_name}_{school_name}_{specialization}"
                        
                        if unique_key not in matched_specializations:
                            metadata = {
                                'school_id': school_id,
                                'program_id': program_id,
                                'country': program['country'],
                                'duration': program['duration'],
                                'program_type': program['field_of_study'],
                                'fee': program['price'],
                                'rank': program['rank'],
                                'specialization': specialization,
                                'has_specialization': True,
                                'parent_program': program_name, 
                                'school_name': school_name
                            }
                            
                            page_content = convert_single_specialization_to_markdown(program, specialization)
                            
                            doc = Document(
                                page_content=page_content,
                                metadata=metadata
                            )
                            individual_specialization_objects.append(doc)
                            matched_specializations.add(unique_key)
                else:
                    specialization = specializations
                    unique_key = f"{program_name}_{school_name}_{specialization}"
                    
                    if unique_key not in matched_specializations:
                        metadata = {
                            'school_id': school_id,
                            'program_id': program_id,
                            'country': program['country'],
                            'duration': program['duration'],
                            'program_type': program['field_of_study'],
                            'fee': program['price'],
                            'rank': program['rank'],
                            'specialization': specialization,
                            'has_specialization': True,
                            'parent_program': program_name, 
                            'school_name': school_name
                        }   
                        page_content = convert_single_specialization_to_markdown(program, specialization)
                        doc = Document(
                            page_content=page_content,
                            metadata=metadata
                        )
                        individual_specialization_objects.append(doc)
                        matched_specializations.add(unique_key)

    individual_specialization_markdowns = []
    for doc in individual_specialization_objects:
        individual_specialization_markdowns.append(doc.page_content)

    print(f"\nGenerated {len(individual_specialization_markdowns)} individual specialization markdowns")
    double_diplomas = []
    for speec in individual_specialization_objects:  
        if contains_masters_degree_terms(speec.metadata['specialization']) and "embarqués" not in speec.metadata['specialization']:
            speec.metadata['is_double_diploma'] = "True"
            double_diplomas.append(speec)
            individual_specialization_objects.remove(speec)  

    return individual_specialization_objects, double_diplomas

def create_programs_document_objects(final_list_of_json_for_markdown, school_data, program_data):
    """Create documents with proper duplicate handling"""
    
    # Populate the lookup dictionaries if they're empty
    if not program_lookup or not school_lookup:
        # Build school_lookup
        for school in school_data:
            school_lookup[normalize_name(school['school_name'])] = str(school['school_id'])
        
        # Build program_lookup
        for program in program_data:
            compound_key = create_program_key(program['program_name'], program['school_id'])
            program_lookup[compound_key] = str(program['program_id']) 
    
    # Track which program_id + school_id combinations we've already processed
    processed_combinations = set()
    list_of_document_objects = []
    program_id_usage = {}
    
    for program in final_list_of_json_for_markdown:
        program_name = program['program_name']
        school_name = program['school_name']
        
        # Find school_id
        school_id = school_lookup.get(normalize_name(school_name))
        
        # Find program_id
        program_id = None
        if school_id:
            compound_key = create_program_key(program_name, school_id)
            program_id = program_lookup.get(compound_key)
        
        if program_id and school_id:
            # Create a unique combination key
            combination_key = f"{program_id}_{school_id}"
            
            # Only process if we haven't seen this exact combination before
            if combination_key not in processed_combinations:
                processed_combinations.add(combination_key)
                
                # Track usage for debugging
                if program_id in program_id_usage:
                    program_id_usage[program_id].append({
                        'program_name': program_name,
                        'school_name': school_name,
                        'school_id': school_id
                    })
                else:
                    program_id_usage[program_id] = [{
                        'program_name': program_name,
                        'school_name': school_name,
                        'school_id': school_id
                    }]
                
                metadata = {
                    'school_id': school_id,
                    'program_id': program_id,
                    'country': program['country'],
                    'duration': program['duration'],
                    'program_type': program['field_of_study'],
                    'fee': program['price']['price'] if isinstance(program['price'], dict) else program['price'],  # Extract price value
                    'program_year': program['price']['program_year'] if isinstance(program['price'], dict) else None,  # Extract program_year
                    'rank': program['rank'],
                    'school_name': school_name
                }
                
                page_content = convert_single_program_to_markdown(program)
                
                doc = Document(
                    page_content=page_content,
                    metadata=metadata
                )
                list_of_document_objects.append(doc)
            else:
                print(f"SKIPPED DUPLICATE: {program_name} at {school_name} (combination {combination_key} already processed)")
    
    # Report on program_id usage
    multi_use_programs = {pid: programs for pid, programs in program_id_usage.items() if len(programs) > 1}
    
    print(f"\nCreated {len(list_of_document_objects)} unique document objects")
    print(f"Program IDs used for multiple schools: {len(multi_use_programs)}")
    
    if multi_use_programs:
        print("\nProgram IDs used across multiple schools:")
        for pid, programs in multi_use_programs.items():
            print(f"  Program ID {pid} used for {len(programs)} different schools:")
            for prog in programs:
                print(f"    - {prog['program_name']} at {prog['school_name']} (School ID: {prog['school_id']})")
    
    return list_of_document_objects
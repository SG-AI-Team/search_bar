from parent_json_generator import *
from json_transformation import *
from markdown_create import * 
from vdb_create import * 
from fetch_data import get_all_data

program_data, school_data, intake_data, years_data, specilization_data = get_all_data()

transformed_program_data = transform_program_data(program_data)
transformed_school_data = transform_school_data(school_data)
transformed_intake_data = transform_intake_data(intake_data)
transformed_specilization_data = transform_specilization_data(specilization_data)

school_parent = generate_school_parent("data/school_parent_json.json", school_data)
program_parent = generate_program_parent("data/program_parent_json.json", intake_data, years_data, program_data, transformed_specilization_data)

final_list_of_json_for_markdown = generate_md_json(
    program_parent=program_parent, 
    program_data=program_data,
    transformed_program_data=transformed_program_data, 
    transformed_school_data=transformed_school_data, 
    intake_data=intake_data, 
    transformed_intake_data=transformed_intake_data, 
    transformed_specilization_data=transformed_specilization_data
)

specilization_docs, double_diplomas_docs = create_specilizations_document_objects(final_list_of_json_for_markdown, school_data, program_data)
program_docs = create_programs_document_objects(final_list_of_json_for_markdown, school_data, program_data)
vdb_documents = specilization_docs + double_diplomas_docs + program_docs
vdb = create_vdb(vdb_documents)
import json 

school_ids_list = []
the_dict_of_school_data_needed_in_programs = dict()

def generate_school_parent(output_path: str, school_data):
    school_parent_json = dict()
    for school in school_data:
        the_json_we_want_to_return = dict()
        the_json_we_want_to_return["school_id"] = school.get("school_id")
        the_json_we_want_to_return["school_name"] = school.get("school_name")
        if school["school_metadata"] is not None:
            the_json_we_want_to_return["rank"] = school["school_metadata"]["rankings"]["average_fr_rank"]
        else:
            the_json_we_want_to_return["rank"] = None
        the_json_we_want_to_return["school_logo"] = school.get("logo_pic_link")
        the_json_we_want_to_return["country_code"] = school.get("country_tenant_code")
        school_parent_json[the_json_we_want_to_return["school_id"]] = the_json_we_want_to_return
        school_ids_list.append(school['school_id'])
        the_dict_of_school_data_needed_in_programs[school['school_id']] = [school['school_type'][0], school['logo_pic_link'], school['country_tenant_code']]

    with open(output_path, 'w') as f:
        json.dump(school_parent_json, f, indent=2)

    return school_parent_json


def extract_price(intake_data, years_data, program_data):
    program_intake_year_dict = dict()
    for intake in intake_data:
        for year in years_data:
            if intake['year_id'] == year['year_id'] and intake['program_id'] == year['program_id']:
                if intake['program_id'] not in program_intake_year_dict:
                    program_intake_year_dict[intake['program_id']] = []
                program_intake_year_dict[intake['program_id']].append({
                    'price': intake['price'],
                    'program_year': year['program_year']
                })
    for program in program_data:
        if program['program_id'] not in program_intake_year_dict:
            program_intake_year_dict[program['program_id']] = [{'price': 0, 'program_year': 1}]
    return program_intake_year_dict

def map_price_with_program(program_intake_year_dict):
    price_dict = dict()
    for program_id, data_list in program_intake_year_dict.items():
        year_1_prices = [item['price'] for item in data_list if item['program_year'] == 1]
        if year_1_prices:
            price_dict[program_id] = year_1_prices
        else:
            min_year = min(item['program_year'] for item in data_list)
            min_year_prices = [item['price'] for item in data_list if item['program_year'] == min_year]
            price_dict[program_id] = min_year_prices
    return price_dict

def generate_program_parent(output_path: str, intake_data, years_data, program_data):
        
    program_intake_year_dict = extract_price(intake_data, years_data, program_data)
    price_dict = map_price_with_program(program_intake_year_dict)
    programs_parent_json = dict()
    for program in program_data:
        the_program_json = dict()
        if program['school_id'] in school_ids_list:
            the_program_json["school_logo"] = the_dict_of_school_data_needed_in_programs[program['school_id']][1]
            the_program_json["country_code"] = the_dict_of_school_data_needed_in_programs[program['school_id']][2]
            the_program_json["school_type"] = the_dict_of_school_data_needed_in_programs[program['school_id']][0]
            the_program_json["program_name"] = program.get("program_name")
            the_program_json["school_id"] = program.get("school_id")
            the_program_json["program_id"] = program.get("program_id")
            the_program_json["price"] = max(price_dict[(program.get("program_id"))])
            programs_parent_json[program['program_id']] = the_program_json
    with open(output_path, 'w') as f:
        json.dump(programs_parent_json, f, indent=2)

    return programs_parent_json


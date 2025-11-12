def exclude_ids(school_ids, program_ids, search_filter):
    filter_conditions = []
    
    if len(school_ids) > 1 and search_filter == 'schools':
        filter_conditions.append({"school_id": {"$nin": school_ids}})
    
    elif len(school_ids) == 1:
        filter_conditions.append({"school_id": {"$in": school_ids}})

    if program_ids:
        filter_conditions.append({"program_id": {"$nin": program_ids}})
    
    if len(filter_conditions) > 1:
        return {"$and": filter_conditions}
    elif len(filter_conditions) == 1:
        return filter_conditions[0]  
    else:
        return {}  

def not_exclude_ids(school_ids, program_ids):
    filter_conditions = []
    
    if school_ids:
        filter_conditions.append({"school_id": {"$in": school_ids}})
    
    if program_ids:
        filter_conditions.append({"program_id": {"$in": program_ids}})
    
    if len(filter_conditions) > 1:
        return {"$and": filter_conditions}
    elif len(filter_conditions) == 1:
        return filter_conditions[0]
    else:
        return None

def range_filter_statement(key_name, min_value, max_value):
    return {"$and": [{key_name:{"$lte":max_value}},{key_name: {"$gte":min_value}}]}

def equal_filter(key, value):
    return {key: {"$eq":value}}

def text_filter(key, value):
    return {"where_document": {"$regex": f"(?i){key}.*{value}"}}

def filters(filter_statements):
    filter_conditions = []
    
    grouped_filters = {}
    
    for filter_statement in filter_statements:
        for key, value in filter_statement.items():
            if key not in grouped_filters:
                grouped_filters[key] = []
            grouped_filters[key].append(value)
    
    # Process each category
    for category, values in grouped_filters.items():
        if category == 'program_type':
            if len(values) == 1:
                filter_conditions.append(equal_filter('program_type', values[0]))
            else:
                or_conditions = [equal_filter('program_type', val) for val in values]
                filter_conditions.append({"$or": or_conditions})
        
        elif category == 'duration':
            if len(values) == 1:
                filter_conditions.append(equal_filter('duration', values[0]))
            else:
                or_conditions = [equal_filter('duration', val) for val in values]
                filter_conditions.append({"$or": or_conditions})
        
        elif category == 'fee':
            if len(values) == 1:
                filter_conditions.append(range_filter_statement('fee', min(values[0]), max(values[0])))
            else:
                or_conditions = []
                for fee_range in values:
                    or_conditions.append(range_filter_statement('fee', min(fee_range), max(fee_range)))
                filter_conditions.append({"$or": or_conditions})
        
        elif category == 'program_language':
            if len(values) == 1:
                filter_conditions.append(text_filter('program language', values[0]))
            else:
                or_conditions = []
                # Individual conditions for each language
                for lang in values:
                    or_conditions.append({"$regex": f"(?i)program Language.*{lang}"})
                # AND condition for all languages together
                if len(values) > 1:
                    and_conditions = []
                    for lang in values:
                        and_conditions.append({"$regex": f"(?i)program Language.*{lang}"})
                    or_conditions.append({"$and": and_conditions})
                
                filter_conditions.append({"where_document": {"$or": or_conditions}})
        
        elif category == 'entry_level':
            if len(values) == 1:
                filter_conditions.append(text_filter('entry level', values[0]))
            else:
                or_conditions = []
                # Individual conditions for each level
                for level in values:
                    or_conditions.append({"$regex": f"(?i)entry level.*{level}"})
                # AND condition for all levels together
                if len(values) > 1:
                    and_conditions = []
                    for level in values:
                        and_conditions.append({"$regex": f"(?i)entry level.*{level}"})
                    or_conditions.append({"$and": and_conditions})
                
                filter_conditions.append({"where_document": {"$or": or_conditions}})
        
        elif category == 'city':
            if len(values) == 1:
                filter_conditions.append(text_filter('city', values[0]))
            else:
                or_conditions = []
                # Individual conditions for each city
                for city in values:
                    or_conditions.append({"$regex": f"(?i)city.*{city}"})
                # AND condition for all cities together
                if len(values) > 1:
                    and_conditions = []
                    for city in values:
                        and_conditions.append({"$regex": f"(?i)city.*{city}"})
                    or_conditions.append({"$and": and_conditions})
                
                filter_conditions.append({"where_document": {"$or": or_conditions}})
        
        elif category == 'country':
            if len(values) == 1:
                filter_conditions.append(text_filter('country', values[0]))
            else:
                or_conditions = []
                # Individual conditions for each country
                for country in values:
                    or_conditions.append({"$regex": f"(?i)country.*{country}"})
                # AND condition for all countries together
                if len(values) > 1:
                    and_conditions = []
                    for country in values:
                        and_conditions.append({"$regex": f"(?i)country.*{country}"})
                    or_conditions.append({"$and": and_conditions})
                
                filter_conditions.append({"where_document": {"$or": or_conditions}})
        
        elif category == 'intake':
            if len(values) == 1:
                filter_conditions.append(text_filter('intake', values[0]))
            else:
                or_conditions = []
                # Individual conditions for each intake
                for intake in values:
                    or_conditions.append({"$regex": f"(?i)intake.*{intake}"})
                # AND condition for all intakes together
                if len(values) > 1:
                    and_conditions = []
                    for intake in values:
                        and_conditions.append({"$regex": f"(?i)intake.*{intake}"})
                    or_conditions.append({"$and": and_conditions})
                
                filter_conditions.append({"where_document": {"$or": or_conditions}})
    
    return filter_conditions

def internal_filters(extracted_fields: dict):
    filter_conditions = []
    # filter_conditions.append({"program_degree": {"$in": extracted_fields['degree_level']}})
    if 'is_double_diploma' in extracted_fields and extracted_fields['is_double_diploma'] is not None:
        # Convert boolean to string since metadata stores it as string
        is_double_diploma_str = 'True' if extracted_fields['is_double_diploma'] else 'False'
        if is_double_diploma_str  == 'True':
            filter_conditions.append({
                "is_double_diploma": {"$in": [is_double_diploma_str]}
            })
        else:
            filter_conditions.append({
                "is_double_diploma": {"$nin": [is_double_diploma_str]}
                })
            
            

    return filter_conditions
    

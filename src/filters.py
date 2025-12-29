def create_multi_filter(values, filter_type, key=None):
    
    if filter_type == "equal":
        # For equal filters (program_type, duration) - use $in for OR logic
        # This handles: value1 OR value2 OR value3, etc.
        return {key: {"$in": values}}
    
    elif filter_type == "text":
        # For text filters - use regex for pattern matching
        if not key:
            raise ValueError("Key parameter is required for text filters")
        
        if len(values) == 1:
            return text_filter(key, values[0])
        
        # For multi-select: create OR conditions with regex using text_filter
        individual_conditions = []
        for val in values:
            text_filter_result = text_filter(key, val)
            # Extract the regex condition from the text_filter result
            individual_conditions.append(text_filter_result["where_document"])
        
        return {"where_document": {"$or": individual_conditions}}
    
    else:
        raise ValueError("filter_type must be 'equal' or 'text'")



def exclude_ids(school_ids, program_ids, search_filter):
    filter_conditions = []
    if search_filter == 'schools':
        if school_ids:
            filter_conditions.append({"school_id": {"$nin": school_ids}})  
    elif search_filter == 'programs':
        if program_ids:
            if len(school_ids) == 1:
                filter_conditions.append({"school_id": {"$in": school_ids}})
                filter_conditions.append({"program_id": {"$nin": program_ids}})
            else:
                filter_conditions.append({"program_id": {"$nin": program_ids}})
    else:
        if program_ids:
            filter_conditions.append({"program_id": {"$nin": program_ids}})
    
    # Return proper format
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

def range_filter_statement(key_name, list_of_values):
    return {"$and": [{key_name:{"$lte":list_of_values[1]}},{key_name: {"$gte":list_of_values[0]}}]}

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
            
            # Fix: Only do this once, not twice
            if isinstance(value, list):
                grouped_filters[key].extend(value)  # Flatten the array
            else:
                grouped_filters[key].append(value)
                
    # Process each category
    for category, values in grouped_filters.items():
        if category == 'program_type':
            if len(values) == 1:
                filter_conditions.append(equal_filter('program_type', values[0]))
            else:
                # Use $in for multiple values
                filter_conditions.append({'program_type': {'$in': values}})
        
        elif category == 'duration':
            if len(values) == 1:
                filter_conditions.append(equal_filter('duration', values[0]))
            else:
                # Use $or with individual $eq operations to handle mixed types
                or_conditions = []
                for val in values:
                    or_conditions.append({'duration': {'$eq': val}})
                filter_conditions.append({"$or": or_conditions})
        
        elif category == 'fee':
            # if len(values) == 1:
            #     filter_conditions.append(range_filter_statement('fee', values[0]))
            # else:
            filter_conditions.append(range_filter_statement('fee', values))
        
        elif category == 'program_language':
            if len(values) == 1:
                filter_conditions.append(text_filter('program language', values[0]))
            else:
                # Simple OR with regex for each value
                or_conditions = []
                for lang in values:
                    or_conditions.append({"$regex": f"(?i)program Language.*{lang}"})
                filter_conditions.append({"where_document": {"$or": or_conditions}})
        
        elif category == 'entry_level':
            if len(values) == 1:
                filter_conditions.append(text_filter('entry level', values[0]))
            else:
                # Simple OR with regex for each value
                or_conditions = []
                for level in values:
                    or_conditions.append({"$regex": f"(?i)entry level.*{level}"})
                filter_conditions.append({"where_document": {"$or": or_conditions}})
        
        elif category == 'city':
            if len(values) == 1:
                filter_conditions.append(text_filter('city', values[0]))
            else:
                # Simple OR with regex for each value
                or_conditions = []
                for city in values:
                    or_conditions.append({"$regex": f"(?i)city.*{city}"})
                filter_conditions.append({"where_document": {"$or": or_conditions}})
        
        elif category == 'country':
            if len(values) == 1:
                filter_conditions.append(text_filter('country', values[0]))
            else:
                # Simple OR with regex for each value
                or_conditions = []
                for country in values:
                    or_conditions.append({"$regex": f"(?i)country.*{country}"})
                filter_conditions.append({"where_document": {"$or": or_conditions}})
        
        elif category == 'intake':
            if len(values) == 1:
                filter_conditions.append(text_filter('intake', values[0]))
            else:
                # Simple OR with regex for each value
                or_conditions = []
                for intake in values:
                    or_conditions.append({"$regex": f"(?i)intake.*{intake}"})
                filter_conditions.append({"where_document": {"$or": or_conditions}})               
        elif category == 'school_name':
            if len(values) == 1:
                filter_conditions.append(equal_filter('school_name', values[0]))
            else:
                # Use $in for multiple values
                filter_conditions.append({'school_name': {'$in': values}})

    
    return filter_conditions


def internal_filters(extracted_fields: dict):
    filter_conditions = []
    if 'is_double_diploma' in extracted_fields and extracted_fields['is_double_diploma'] is not None:
        is_double_diploma_str = 'True' if extracted_fields['is_double_diploma'] else 'False'
        if is_double_diploma_str == 'True':
            # Show only double diploma programs
            filter_conditions.append({"is_double_diploma": {"$eq": "True"}})
        else:
            # Show only non-double diploma programs
            filter_conditions.append({"is_double_diploma": {"$ne": "True"}})
    return filter_conditions
    
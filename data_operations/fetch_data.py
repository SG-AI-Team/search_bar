import os
import json
import jwt
import requests
from datetime import datetime, timedelta, timezone

SECRET = "-_v7QkojB2-N-2u-w4OeXjBJLASKD1Sc6wQR8EHp0_9JIV6MmN6UJft20G9XUx4XuZz5eLda7xqbzja-CW09dA"
BASE_URL = "https://studentgator.xyz/"

def generate_token():
    """Generate JWT token for API authentication"""
    payload = {
        "service": "ai-agent",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=120),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def filter_test_items(data):
    """Filter out items that contain 'test' in their name (case-insensitive)"""
    if not isinstance(data, list):
        return data
    
    filtered_data = []
    for item in data:
        if isinstance(item, dict):
            # Check various possible name fields
            name_fields = ['name', 'title', 'school_name', 'program_name', 'intake_name', 'specialization']
            has_test = False
            
            for field in name_fields:
                if field in item and isinstance(item[field], str):
                    if 'test' in item[field].lower():
                        has_test = True
                        break
            
            if not has_test:
                filtered_data.append(item)
        else:
            # If item is not a dict, keep it as is
            filtered_data.append(item)
    
    return filtered_data

def filter_archived_items(data, data_type="unknown"):
    """Filter out items that have archive = True"""
    if not isinstance(data, list):
        return data
    
    filtered_data = []
    archived_count = 0
    
    for item in data:
        if isinstance(item, dict):
            # Check different ways archived might be represented
            archived_value = item.get('archive')
            
            # Check for various representations of True
            is_archived = (
                archived_value is True or
                archived_value == 'true' or
                archived_value == 'True' or
                archived_value == 1 or
                archived_value == '1'
            )
            
            if is_archived:
                archived_count += 1
                print(f"🗄️ Filtering out archived {data_type}: {item.get('name', item.get('title', item.get('school_name', item.get('program_name', 'Unknown'))))}")
                continue  # Skip archived items
            
            filtered_data.append(item)
        else:
            # If item is not a dict, keep it as is
            filtered_data.append(item)
    
    if archived_count > 0:
        print(f"🗄️ {data_type}: Removed {archived_count} archived items out of {len(data)} total")
    
    return filtered_data

def filter_related_data(all_data):
    """Filter out data related to archived schools and programs - complete cascade"""
    print("🔗 Starting complete cascade filtering...")
    
    # Step 1: Get IDs of active (non-archived) schools
    active_school_ids = set()
    for school in all_data.get('schools', []):
        if isinstance(school, dict):
            archived_value = school.get('archive')
            is_archived = (
                archived_value is True or
                archived_value == 'true' or
                archived_value == 'True' or
                archived_value == 1 or
                archived_value == '1'
            )
            
            if not is_archived:
                school_id = school.get('school_id')
                if school_id:
                    active_school_ids.add(school_id)
    
    print(f"🏫 Found {len(active_school_ids)} active schools")
    
    # Step 2: Filter programs - must be non-archived AND belong to active schools
    active_program_ids = set()
    if 'programs' in all_data:
        original_program_count = len(all_data['programs'])
        filtered_programs = []
        
        for program in all_data['programs']:
            if isinstance(program, dict):
                # Check if program itself is archived
                archived_value = program.get('archive')
                is_archived = (
                    archived_value is True or
                    archived_value == 'true' or
                    archived_value == 'True' or
                    archived_value == 1 or
                    archived_value == '1'
                )
                
                # Check if program belongs to active school
                school_id = program.get('school_id')
                
                if not is_archived and school_id in active_school_ids:
                    filtered_programs.append(program)
                    program_id = program.get('program_id')
                    if program_id:
                        active_program_ids.add(program_id)
        
        all_data['programs'] = filtered_programs
        print(f"📚 Programs: {original_program_count} -> {len(filtered_programs)} (removed {original_program_count - len(filtered_programs)})")
    
    print(f"📚 Found {len(active_program_ids)} active programs")
    
    # Step 3: Filter years - must belong to active programs
    active_year_ids = set()
    if 'years' in all_data:
        original_year_count = len(all_data['years'])
        filtered_years = []
        
        for year in all_data['years']:
            if isinstance(year, dict):
                program_id = year.get('program_id')
                if program_id in active_program_ids:
                    filtered_years.append(year)
                    year_id = year.get('year_id')
                    if year_id:
                        active_year_ids.add(year_id)
        
        all_data['years'] = filtered_years
        print(f"📅 Years: {original_year_count} -> {len(filtered_years)} (removed {original_year_count - len(filtered_years)})")
    
    print(f"📅 Found {len(active_year_ids)} active years")
    
    # Step 4: Filter intakes - must belong to active programs AND active years
    if 'intakes' in all_data:
        original_intake_count = len(all_data['intakes'])
        filtered_intakes = []
        
        for intake in all_data['intakes']:
            if isinstance(intake, dict):
                program_id = intake.get('program_id')
                year_id = intake.get('year_id')
                
                # Keep intake only if both program and year are active
                if program_id in active_program_ids and (year_id is None or year_id in active_year_ids):
                    filtered_intakes.append(intake)
        
        all_data['intakes'] = filtered_intakes
        print(f"📥 Intakes: {original_intake_count} -> {len(filtered_intakes)} (removed {original_intake_count - len(filtered_intakes)})")
    
    # Step 5: Filter specializations - must belong to active programs AND active years
    if 'specializations' in all_data:
        original_spec_count = len(all_data['specializations'])
        filtered_specializations = []
        
        for spec in all_data['specializations']:
            if isinstance(spec, dict):
                program_id = spec.get('program_id')
                year_id = spec.get('year_id')
                
                # Keep specialization only if both program and year are active
                if program_id in active_program_ids and (year_id is None or year_id in active_year_ids):
                    filtered_specializations.append(spec)
        
        all_data['specializations'] = filtered_specializations
        print(f"🎯 Specializations: {original_spec_count} -> {len(filtered_specializations)} (removed {original_spec_count - len(filtered_specializations)})")
    
    return all_data

def call_api_endpoint(endpoint):
    """Call a single API endpoint and return the response"""
    try:
        token = generate_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{BASE_URL}{endpoint}"
        
        print(f"🔗 Calling: {endpoint}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {endpoint}: {len(data.get('data', []))} items")
            return data
        else:
            print(f"❌ {endpoint} failed ({response.status_code}): {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Error calling {endpoint}: {e}")
        return None

def fetch_all_agent_apis():
    """Fetch data from all Agent APIs and save to a single JSON file"""
    print("📡 Fetching data from all Agent API endpoints...")
    
    # Define all Agent API endpoints
    agent_endpoints = {
        "schools": "agent/all-schools",
        "programs": "agent/all-programs", 
        "years": "agent/all-years",
        "intakes": "agent/all-program-intakes",
        "specializations": "agent/all-program-specializations",
    }
    
    all_data = {}
    successful_calls = []
    failed_calls = []
    total_removed_test = 0
    total_removed_archived = 0
    
    # First pass: Filter test items and directly archived items
    for name, endpoint in agent_endpoints.items():
        print(f"\n{'='*40}")
        print(f"Processing: {name.upper()}")
        print(f"{'='*40}")
        
        result = call_api_endpoint(endpoint)
        if result:
            raw_data = result.get('data', [])
            print(f"📥 Raw data count: {len(raw_data)}")
            
            # Filter test items first
            filtered_test = filter_test_items(raw_data)
            test_removed = len(raw_data) - len(filtered_test)
            total_removed_test += test_removed
            
            if test_removed > 0:
                print(f"🧹 {name}: Filtered out {test_removed} test items")
            
            # Filter directly archived items
            filtered_archived = filter_archived_items(filtered_test, name)
            archived_removed = len(filtered_test) - len(filtered_archived)
            total_removed_archived += archived_removed
            
            all_data[name] = filtered_archived
            successful_calls.append(name)
            print(f"✅ {name}: After direct filtering = {len(filtered_archived)}")
            
        else:
            all_data[name] = []
            failed_calls.append(name)
    
    # Second pass: Filter related data based on archived relationships
    print(f"\n{'='*50}")
    print("🔗 FILTERING RELATED DATA (CASCADE)")
    print(f"{'='*50}")
    
    # Store counts before cascade filtering
    before_cascade = {name: len(data) for name, data in all_data.items()}
    
    all_data = filter_related_data(all_data)
    
    # Calculate cascade removals
    cascade_removed = {}
    for name, data in all_data.items():
        if name in before_cascade:
            cascade_removed[name] = before_cascade[name] - len(data)
    
    # Final verification - check for any archived items in the final data
    print(f"\n{'='*50}")
    print("🔍 FINAL VERIFICATION")
    print(f"{'='*50}")
    
    total_archived_found = 0
    for name, data in all_data.items():
        archived_items = []
        for item in data:
            if isinstance(item, dict):
                archived_value = item.get('archive')
                is_archived = (
                    archived_value is True or
                    archived_value == 'true' or
                    archived_value == 'True' or
                    archived_value == 1 or
                    archived_value == '1'
                )
                if is_archived:
                    archived_items.append(item.get('name', item.get('title', item.get('school_name', item.get('program_name', 'Unknown')))))
        
        if archived_items:
            total_archived_found += len(archived_items)
            print(f"❌ {name} STILL HAS {len(archived_items)} ARCHIVED ITEMS:")
            for item_name in archived_items[:5]:  # Show first 5
                print(f"   - {item_name}")
        else:
            print(f"✅ {name}: No archived items found")
    
    if total_archived_found > 0:
        print(f"\n⚠️ TOTAL ARCHIVED ITEMS STILL PRESENT: {total_archived_found}")
    else:
        print(f"\n✅ SUCCESS: No archived items found in final data")
    
    # Add metadata
    metadata = {
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
        "successful_endpoints": successful_calls,
        "failed_endpoints": failed_calls,
        "total_endpoints": len(agent_endpoints),
        "success_rate": f"{len(successful_calls)}/{len(agent_endpoints)} ({len(successful_calls)/len(agent_endpoints)*100:.1f}%)",
        "filtered": "Items containing 'test' in name fields and all archived items with their relationships have been removed",
        "total_test_items_removed": total_removed_test,
        "total_archived_items_removed": total_removed_archived,
        "cascade_removed": cascade_removed,
        "archived_items_in_final_data": total_archived_found
    }
    
    # Add counts for each data type
    for name, data in all_data.items():
        metadata[f"total_{name}"] = len(data)
    
    # Combine all data
    combined_data = {
        "data": all_data,
        "metadata": metadata
    }
    
    # # Save to JSON file
    # with open(output_file, "w", encoding="utf-8") as f:
    #     json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n📊 FINAL SUMMARY:")
    print(f"✅ Successful calls: {successful_calls}")
    if failed_calls:
        print(f"❌ Failed calls: {failed_calls}")
    print(f"🧹 Total test items removed: {total_removed_test}")
    print(f"🗄️ Total directly archived items removed: {total_removed_archived}")
    print(f"🔗 Cascade filtering removed:")
    for name, count in cascade_removed.items():
        if count > 0:
            print(f"   {name}: {count} items")
    # print(f"💾 Data saved to: {output_file}")
    
    # Print final data counts
    print(f"\n📈 FINAL DATA COUNTS:")
    for name, data in all_data.items():
        if data:
            print(f"   {name}: {len(data)} items")

    with open("agent_data_full.json", "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    return combined_data


def get_all_data():
    data = fetch_all_agent_apis()
    program_data = data['data']['programs']
    school_data = data['data']['schools']
    intake_data = data['data']['intakes']
    years_data = data['data']['years']
    specilization_data = data['data']['specializations']
    
    # Transform intake_data to dictionary format expected by json_transformation
    intake_dict = {}
    for intake in intake_data:
        if isinstance(intake, dict) and 'program_id' in intake:
            program_id = intake['program_id']
            if program_id not in intake_dict:
                intake_dict[program_id] = []
            intake_dict[program_id].append(intake)
    
    return program_data, school_data, intake_data, years_data, specilization_data

# Alternative function with only core endpoints
def fetch_core_agent_apis(output_file="core_agent_data.json"):
    """Fetch data from core Agent APIs only"""
    print("📡 Fetching data from core Agent API endpoints...")
    
    core_endpoints = {
        "schools": "agent/all-schools",
        "programs": "agent/all-programs",
        "years": "agent/all-years", 
        "intakes": "agent/all-program-intakes",
        "specializations": "agent/all-program-specializations"
    }
    
    all_data = {}
    total_removed_test = 0
    total_removed_archived = 0
    
    for name, endpoint in core_endpoints.items():
        result = call_api_endpoint(endpoint)
        if result:
            raw_data = result.get('data', [])
            
            # Filter test items first
            filtered_test = filter_test_items(raw_data)
            test_removed = len(raw_data) - len(filtered_test)
            total_removed_test += test_removed
            
            # Filter archived items
            filtered_archived = filter_archived_items(filtered_test, name)
            archived_removed = len(filtered_test) - len(filtered_archived)
            total_removed_archived += archived_removed
            
            all_data[name] = filtered_archived
            
            # Print filtering info
            if test_removed > 0:
                print(f"🧹 {name}: Filtered out {test_removed} test items")
            if archived_removed > 0:
                print(f"🗄️ {name}: Filtered out {archived_removed} archived items")
        else:
            all_data[name] = []
    
    # Filter related data based on archived schools and programs
    print("🔗 Filtering related data based on archived items...")
    all_data = filter_related_data(all_data)
    
    # Save in the format expected by your existing code
    legacy_format = [
        all_data.get('schools', []),
        all_data.get('programs', [])
    ]
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(legacy_format, f, indent=2, ensure_ascii=False)
    
    print(f"🧹 Total test items removed: {total_removed_test}")
    print(f"🗄️ Total archived items removed: {total_removed_archived}")
    print(f"💾 Core data saved to: {output_file}")
    return all_data

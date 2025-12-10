from fetch_data import get_all_data
import traceback

class DataManager:
    _instance = None
    
    def __new__(cls):
        print(f"🔍 DataManager.__new__ called")
        if cls._instance is None:
            print("🆕 Creating new DataManager instance")
            cls._instance = super(DataManager, cls).__new__(cls)
            cls._instance._data_loaded = False
            cls._instance._initialize_data()
        else:
            print("♻️ Returning existing DataManager instance")
        return cls._instance
    
    def _initialize_data(self):
        """Initialize data only once when instance is created"""
        print(f"🔧 _initialize_data called, _data_loaded = {self._data_loaded}")
        if not self._data_loaded:
            print("📥 Calling load_data from _initialize_data")
            self.load_data()
        else:
            print("⚡ Data already loaded, skipping")
    
    def load_data(self):
        """Load all data once from API"""
        print("📡 Loading data from API...")
        print("📍 Call stack:")
        traceback.print_stack()
        self.program_data, self.school_data, self.intake_data, self.years_data, self.specilization_data = get_all_data()
        self._data_loaded = True
        print("✅ Data loaded successfully!")
    
    def get_program_data(self):
        return self.program_data
    
    def get_school_data(self):
        return self.school_data
    
    def get_intake_data(self):
        return self.intake_data
    
    def get_years_data(self):
        return self.years_data
    
    def get_specilization_data(self):
        return self.specilization_data
    
    def get_all_data(self):
        print("🔄 get_all_data called")
        return self.program_data, self.school_data, self.intake_data, self.years_data, self.specilization_data


print("🚀 Creating data_manager singleton")
data_manager = DataManager()

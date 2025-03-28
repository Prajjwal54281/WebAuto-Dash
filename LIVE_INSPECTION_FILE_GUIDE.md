# 📁 Live Portal Inspector - File Management Guide

## 🎯 File Locations

### **Generated Adapter Files**
```
Projects/WebAutoDash/portal_adapters/
```

### **Analysis Results**
```
Projects/WebAutoDash/portal_analyses/
```

## 📝 File Naming Conventions

### **Adapter Files**
**Pattern:** `{portal_name_clean}_live_adapter_{timestamp}.py`

**Examples:**
- Portal: `"Dr. Smith's Patient Portal"` → `dr_smiths_patient_portal_live_adapter_20240603_143052.py`
- Portal: `"Hospital-XYZ Portal"` → `hospital_xyz_portal_live_adapter_20240603_143052.py`
- Portal: `"Epic MyChart"` → `epic_mychart_live_adapter_20240603_143052.py`

**Naming Rules:**
1. Convert to lowercase
2. Replace spaces and hyphens with underscores
3. Remove special characters (keep only alphanumeric, underscore, hyphen)
4. Remove consecutive underscores
5. Remove leading/trailing underscores
6. Add timestamp for uniqueness

### **Analysis Results**
**Pattern:** `live_inspection_{timestamp}.json`

**Example:** `live_inspection_20240603_143052.json`

## 🔍 What Gets Saved

### **1. Adapter Code File (`portal_adapters/`)**
- Complete Python adapter class
- Auto-discovered selectors from live inspection
- Login methods using recorded patterns
- Patient data extraction functions
- Browser automation setup
- Ready-to-use code with WebAutoDash compatibility

### **2. Analysis Results File (`portal_analyses/`)**
- Inspection metadata (ID, timestamp, portal config)
- Recorded user actions and navigation flow
- Discovered elements (forms, tables, buttons)
- Portal characteristics analysis
- Generated selectors and patterns
- Complete inspection summary

## 🛠️ Path Resolution Logic

The system automatically resolves the correct paths:

```python
# From: backend/routes/portal_inspector_api.py
# To: portal_adapters/
adapter_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_adapters')

# From: backend/routes/portal_inspector_api.py  
# To: portal_analyses/
results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_analyses')
```

**Path Breakdown:**
- `__file__` = `Projects/WebAutoDash/backend/routes/portal_inspector_api.py`
- `os.path.dirname(__file__)` = `Projects/WebAutoDash/backend/routes/`
- `'..', '..'` = Go up two directories
- Final path = `Projects/WebAutoDash/portal_adapters/`

## 📥 Download Files

When downloading from the web interface:

### **Frontend Downloads**
- **Adapter Code:** `{portal_name_clean}_live_adapter_{timestamp}.py`
- **Full Report:** `{portal_name_clean}_inspection_results_{timestamp}.json`

### **Backend Generated Files**
- **Adapter Code:** Saved to `portal_adapters/` directory
- **Analysis Data:** Saved to `portal_analyses/` directory

## 🔧 File Structure Examples

### **Generated Adapter Structure**
```python
"""
Generated Portal Adapter for Dr. Smith's Patient Portal
Created by WebAutoDash Live Inspector on 2024-06-03 14:30:52
"""

from playwright.async_api import async_playwright
import asyncio
import json
from typing import Dict, List, Optional

class DrSmithsPatientPortalAdapter:
    def __init__(self):
        self.portal_name = "Dr. Smith's Patient Portal"
        self.portal_url = "https://portal.example.com"
        self.browser = None
        self.page = None
        
        # Auto-discovered selectors from live inspection
        self.selectors = {
            "login": {
                "username_field": "input[name='username']",
                "password_field": "input[type='password']",
                "submit_button": "button[type='submit']"
            },
            "patient_tables": {
                "table_0": {
                    "selector": "table.patient-list",
                    "headers": ["Name", "DOB", "MRN", "Last Visit"],
                    "row_count": 25
                }
            }
        }
    
    # ... rest of adapter methods
```

### **Analysis Results Structure**
```json
{
  "inspection_id": "live_inspection_20240603_143052",
  "timestamp": "2024-06-03T14:30:52.123456",
  "config": {
    "portal_name": "Dr. Smith's Patient Portal",
    "portal_url": "https://portal.example.com",
    "recording_mode": "full",
    "generate_adapter": true
  },
  "results": {
    "success": true,
    "recorded_actions": [...],
    "discovered_elements": {...},
    "portal_characteristics": {...},
    "inspection_summary": {
      "total_actions": 15,
      "pages_visited": 4,
      "elements_discovered": 23,
      "inspection_duration": 125.67
    }
  },
  "inspection_type": "live_inspection",
  "generated_files": {
    "adapter_file": "dr_smiths_patient_portal_live_adapter_20240603_143052.py",
    "adapter_path": "/path/to/portal_adapters/dr_smiths_patient_portal_live_adapter_20240603_143052.py",
    "analysis_file": "live_inspection_20240603_143052.json"
  }
}
```

## ✅ Verification

To verify files are saved correctly:

```bash
# Check adapter files
ls -la Projects/WebAutoDash/portal_adapters/

# Check analysis results  
ls -la Projects/WebAutoDash/portal_analyses/

# View recent adapter
tail -20 Projects/WebAutoDash/portal_adapters/*_live_adapter_*.py

# View recent analysis
jq . Projects/WebAutoDash/portal_analyses/live_inspection_*.json | head -50
```

## 🚀 Integration with WebAutoDash

Generated adapter files are automatically available for use in WebAutoDash:

1. **Immediate Use:** Adapter files are saved to the correct `portal_adapters/` directory
2. **WebAutoDash Detection:** System can automatically discover new adapters
3. **Job Creation:** Use generated adapters for extraction jobs
4. **Testing:** Test adapters directly from the WebAutoDash interface

The Live Portal Inspector seamlessly integrates with your existing WebAutoDash workflow! 
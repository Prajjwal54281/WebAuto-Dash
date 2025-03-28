# WebAutoDash Adapter Development Guide

## Quick Start: Adding a New Portal Adapter

When a doctor demonstrates a new portal, follow these steps to quickly create an adapter:

### 1. Copy the Template
```bash
cd /home/gsingh55/Projects/WebAutoDash/portal_adapters
cp _adapter_template.py new_portal_adapter.py
```

### 2. **CRITICAL**: Implement Required Wrapper Functions

⚠️ **IMPORTANT**: WebAutoDash orchestrator expects specific function signatures. You MUST implement these exact functions:

#### For Single Patient Extraction:
```python
async def extract_single_patient_data(page, patient_identifier, config=None):
    """
    Extract data for a specific patient
    
    Args:
        page: Playwright page object (already logged in by user)
        patient_identifier: Patient ID/MRN to search for
        config: Optional configuration dictionary
    
    Returns:
        Dictionary with patient data structure
    """
    # Your implementation here
    pass
```

#### For All Patients Extraction:
```python
async def extract_all_patients_data(page, config=None):
    """
    Extract data for all patients accessible in the portal
    
    Args:
        page: Playwright page object (already logged in by user)
        config: Optional configuration dictionary
    
    Returns:
        List of dictionaries, each containing patient data
    """
    # Your implementation here
    pass
```

⚠️ **CRITICAL POINTS**:
- Function names MUST be exactly `extract_single_patient_data` and `extract_all_patients_data`
- These are module-level functions, NOT class methods
- The `page` object is already authenticated - DO NOT handle login in these functions
- User logs in manually, then orchestrator calls these functions

### 3. **Login Workflow Understanding**

🔄 **WebAutoDash Login Workflow**:
1. User creates extraction job in WebAutoDash UI
2. Orchestrator opens browser to target URL (login page)
3. Job status becomes "AWAITING_USER_CONFIRMATION"
4. **User manually logs into the portal**
5. **User clicks "Confirm Login" in WebAutoDash UI**
6. Orchestrator calls your adapter functions with authenticated page
7. Your adapter extracts data from authenticated session

❌ **DO NOT**:
- Handle login in wrapper functions
- Try to fill username/password fields
- Navigate to login page
- Wait for login elements

✅ **DO**:
- Assume page is already authenticated
- Navigate to data pages (dashboard, patient list, etc.)
- Wait for data elements to load
- Extract patient information

### 4. **Class-based vs Function-based Adapters**

You can choose either approach:

#### Option A: Pure Functions (Recommended for simplicity)
```python
async def extract_all_patients_data(page, config=None):
    # Direct implementation
    await page.goto('http://portal.com/patients')
    # ... extraction logic
    return patients_data
```

#### Option B: Class + Wrapper Functions (Good for complex adapters)
```python
class MyPortalAdapter:
    async def extract_patients(self, page):
        # Complex logic here
        pass

# Required wrapper functions
async def extract_all_patients_data(page, config=None):
    adapter = MyPortalAdapter()
    return await adapter.extract_patients(page)
```

### 5. Standard Data Structure

Ensure your adapter returns data in this format:

```python
{
    "patient_identifier": "12345",
    "demographics": {
        "name": "John Doe",
        "date_of_birth": "1980-01-01",
        "gender": "Male",
        "mrn": "MRN12345",
        "address": "123 Main St, City, State 12345",
        "phone": "(555) 123-4567",
        "email": "john.doe@email.com"
    },
    "vitals": [
        {
            "date": "2024-01-15",
            "blood_pressure": "120/80",
            "heart_rate": "72",
            "temperature": "98.6°F",
            "weight": "170 lbs"
        }
    ],
    "medications": [
        {
            "name": "Medication Name",
            "dosage": "10mg",
            "frequency": "Once daily",
            "start_date": "2024-01-01"
        }
    ],
    "lab_results": [
        {
            "test_name": "Complete Blood Count",
            "date": "2024-01-10",
            "results": {
                "WBC": "5.5 K/uL",
                "RBC": "4.5 M/uL",
                "Hemoglobin": "14.0 g/dL"
            },
            "document_url": "https://portal.com/lab-result.pdf",  # Optional
            "file_size": "2.3 MB"  # Optional
        }
    ],
    "allergies": [
        {
            "allergen": "Penicillin",
            "reaction": "Rash",
            "severity": "Moderate"
        }
    ],
    "medical_history": [
        {
            "condition": "Hypertension",
            "diagnosed_date": "2020-03-15",
            "status": "Active"
        }
    ],
    "appointments": [
        {
            "date": "2024-02-15",
            "time": "10:00 AM",
            "provider": "Dr. Smith",
            "type": "Follow-up"
        }
    ]
}
```

### 6. **Development Best Practices**

#### Start with Mock Data
```python
async def extract_all_patients_data(page, config=None):
    try:
        # Wait for page to be ready
        await page.wait_for_load_state('networkidle')
        
        # Try to find patient elements
        try:
            await page.wait_for_selector('table, .patient-list, .patient-row', timeout=10000)
        except:
            # Take screenshot for debugging
            await page.screenshot(path='debug_portal.png')
            # Return mock data for initial testing
            return [{"patient_identifier": "MOCK001", "demographics": {...}}]
        
        # Real extraction logic here...
        
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise
```

#### Gradual Selector Development
1. **Start with mock data** to test workflow
2. **Analyze portal structure** using browser dev tools
3. **Update selectors gradually** one section at a time
4. **Test each section** before moving to next

### 7. Common Playwright Patterns

#### Waiting for Elements:
```python
# Wait for element to be visible
await page.wait_for_selector('[data-testid="patient-list"]', state='visible')

# Wait for navigation
await page.wait_for_load_state('networkidle')

# Wait with timeout
await page.wait_for_selector('.patient-row', timeout=10000)
```

#### Extracting Data:
```python
# Get text content
name = await page.locator('[data-testid="patient-name"]').text_content()

# Get multiple elements
rows = await page.locator('.patient-row').all()
for row in rows:
    patient_id = await row.locator('.patient-id').text_content()
```

#### Navigation:
```python
# Click and wait for navigation
await page.click('[data-testid="patient-link"]')
await page.wait_for_load_state('networkidle')

# Search for patient
await page.fill('[data-testid="search-input"]', patient_identifier)
await page.click('[data-testid="search-button"]')
```

### 8. Register the Adapter

Add the adapter to WebAutoDash database:

```bash
curl -X POST http://localhost:5005/api/admin/adapters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Portal Name",
    "description": "Description of the portal and what it extracts",
    "script_filename": "new_portal_adapter.py"
  }'
```

### 9. Test the Adapter

1. **Create a test job** through the WebAutoDash UI:
   - Go to http://localhost:3008
   - Click "Jobs" → "New Job"
   - Select your new adapter
   - Enter the portal URL
   - Choose extraction mode

2. **Monitor the job**:
   - Watch for "AWAITING_USER_CONFIRMATION" status
   - Log into the portal manually when browser opens
   - Click "Confirm Login" in WebAutoDash
   - Monitor extraction progress

### 10. Debugging Tips

#### Check Logs:
```bash
tail -f /home/gsingh55/Projects/WebAutoDash/logs/orchestrator.log
```

#### Common Issues and Solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| "Adapter missing extract_all_patients_data function" | Wrong function name or not module-level | Ensure exact function names at module level |
| "Timeout waiting for selector" | Wrong selectors or portal not loaded | Analyze portal HTML, update selectors |
| "Login failed" | Trying to handle login in adapter | Remove login logic, rely on manual login |
| "Page not authenticated" | User didn't complete login | Ensure manual login before confirmation |

#### Error Prevention Checklist:
- [ ] Function names are exactly `extract_single_patient_data` and `extract_all_patients_data`
- [ ] Functions are at module level (not inside classes)
- [ ] No login logic in wrapper functions
- [ ] Proper error handling and logging
- [ ] Screenshot capture for debugging
- [ ] Mock data fallback for initial testing

### 11. **Portal Analysis Template**

Before coding, fill out the Portal Analysis Template:
```bash
cp /home/gsingh55/Projects/WebAutoDash/templates/PORTAL_ANALYSIS_TEMPLATE.md \
   /home/gsingh55/Projects/WebAutoDash/portal_analyses/YOUR_PORTAL_ANALYSIS.md
```

This helps identify selectors and understand portal structure before coding.

---

## 🚨 **CRITICAL REMINDERS**

1. **NEVER handle login in wrapper functions** - User logs in manually
2. **ALWAYS use exact function names** - `extract_single_patient_data` and `extract_all_patients_data`
3. **ALWAYS test with mock data first** - Get workflow working before real extraction
4. **ALWAYS take screenshots on errors** - Helps debug selector issues
5. **ALWAYS follow the data structure** - Consistent data format required

Following these guidelines will prevent the class/wrapper function issues encountered with the MediMind adapter.

## Ready to Go!

With this guide, you can quickly create adapters for new portals as doctors demonstrate them. The key is to:

1. **Copy the template**
2. **Implement the two required functions**
3. **Follow the standard data structure**
4. **Register and test**

The WebAutoDash system handles all the orchestration, browser management, and UI display automatically! 
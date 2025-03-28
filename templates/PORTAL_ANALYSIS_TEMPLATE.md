# 📋 PORTAL ANALYSIS TEMPLATE

**Portal Name:** _______________
**Analysis Date:** _______________
**Analyst:** _______________

---

## 🚨 **CRITICAL ADAPTER DEVELOPMENT INSTRUCTIONS**

⚠️ **READ THIS BEFORE STARTING ADAPTER DEVELOPMENT** ⚠️

### **WebAutoDash Adapter Requirements**

After completing this analysis, you MUST implement your adapter with these exact specifications:

#### **REQUIRED FUNCTION SIGNATURES**
Your adapter MUST contain exactly these two module-level functions:

```python
async def extract_single_patient_data(page, patient_identifier: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Extract data for a specific patient
    
    Args:
        page: Playwright page object (already authenticated by user)
        patient_identifier: Patient ID/MRN to search for
        config: Optional configuration dictionary
    
    Returns:
        Dictionary with patient data structure
    """
    # Your implementation here

async def extract_all_patients_data(page, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Extract data for all patients accessible in the portal
    
    Args:
        page: Playwright page object (already authenticated by user)
        config: Optional configuration dictionary
    
    Returns:
        List of dictionaries, each containing patient data
    """
    # Your implementation here
```

#### **CRITICAL RULES - FAILURE TO FOLLOW CAUSES ERRORS**
❌ **DO NOT**:
- Use class-based adapters without wrapper functions
- Handle login in your adapter functions
- Try to fill username/password fields
- Navigate to login page in your functions

✅ **DO**:
- Use exact function names: `extract_single_patient_data` and `extract_all_patients_data`
- Make functions module-level (not inside classes)
- Assume page is already authenticated
- Use selectors identified in this analysis
- Start with mock data, then replace with real extraction

#### **LOGIN WORKFLOW**
🔄 **How WebAutoDash Works**:
1. User creates job → Browser opens to target URL
2. **User manually logs in** → Clicks "Confirm Login" in WebAutoDash
3. Your adapter functions are called with authenticated page
4. Extract data using selectors from this analysis

---

## 🔐 SECTION 1: LOGIN PAGE ANALYSIS
**Portal URL:** _______________

### 1.1 USERNAME FIELD
- Field Type: _______________
- Name attribute: _______________
- ID attribute: _______________
- Class attribute: _______________
- Placeholder text: _______________
- CSS Selector: _______________

### 1.2 PASSWORD FIELD
- Field Type: _______________
- Name attribute: _______________
- ID attribute: _______________
- Class attribute: _______________
- Placeholder text: _______________
- CSS Selector: _______________

### 1.3 SUBMIT BUTTON
- Button Type: _______________
- Button Text: _______________
- ID attribute: _______________
- Class attribute: _______________
- CSS Selector: _______________

### 1.4 FORM DETAILS
- Form action URL: _______________
- Form method: _______________
- Hidden fields: _______________
- Post-login redirect URL: _______________

---

## 🏠 SECTION 2: POST-LOGIN NAVIGATION

### 2.1 LANDING PAGE
- URL after login: _______________
- Page title: _______________
- Main heading: _______________

### 2.2 NAVIGATION TO PATIENTS
- Navigation method: _______________
- Menu item text: _______________
- Menu item selector: _______________
- Patient list URL: _______________

### 2.3 PATIENT ACCESS METHOD
- Display type: [list/search/dashboard/other] _______________
- Search available: [Yes/No] _______________
- Search field selector: _______________

---

## 👥 SECTION 3: PATIENT LIST/SEARCH

### 3.1 PATIENT DISPLAY
- Display format: [table/cards/list] _______________
- Patients per page: _______________
- Pagination: [Yes/No] _______________
- Pagination selector: _______________

### 3.2 PATIENT IDENTIFIERS
- Patient name selector: _______________
- Patient ID/MRN selector: _______________
- Patient row selector: _______________

### 3.3 PATIENT DETAIL ACCESS
- Access method: [click/button/link] _______________
- Detail link selector: _______________
- Opens in: [same tab/new tab] _______________

---

## 🏥 SECTION 4: PATIENT DETAILS PAGE

### 4.1 DEMOGRAPHICS
- Section selector: _______________
- Name selector: _______________
- DOB selector: _______________
- Gender selector: _______________
- MRN selector: _______________
- Address selector: _______________
- Phone selector: _______________
- Email selector: _______________

### 4.2 VITALS
- Section selector: _______________
- Display format: [table/list/cards] _______________
- Blood pressure selector: _______________
- Heart rate selector: _______________
- Temperature selector: _______________
- Weight selector: _______________
- Date selector: _______________

### 4.3 MEDICATIONS
- Section selector: _______________
- Display format: [table/list/cards] _______________
- Medication name selector: _______________
- Dosage selector: _______________
- Frequency selector: _______________
- Start date selector: _______________

### 4.4 LAB RESULTS
- Section selector: _______________
- Display format: [table/list/cards] _______________
- Test name selector: _______________
- Test date selector: _______________
- Results selector: _______________
- Reference range selector: _______________

### 4.5 ALLERGIES
- Section selector: _______________
- Display format: [table/list/cards] _______________
- Allergen selector: _______________
- Reaction selector: _______________
- Severity selector: _______________

### 4.6 MEDICAL HISTORY
- Section selector: _______________
- Display format: [table/list/cards] _______________
- Condition selector: _______________
- Date selector: _______________
- Status selector: _______________

### 4.7 APPOINTMENTS
- Section selector: _______________
- Display format: [table/list/cards] _______________
- Date selector: _______________
- Time selector: _______________
- Provider selector: _______________
- Type selector: _______________

---

## ⚙️ SECTION 5: TECHNICAL DETAILS

### 5.1 LOADING BEHAVIOR
- Loading spinners: [Yes/No] _______________
- Loading spinner selector: _______________
- Average load time: _______________

### 5.2 DYNAMIC CONTENT
- AJAX loading: [Yes/No] _______________
- Scroll required: [Yes/No] _______________
- Infinite scroll: [Yes/No] _______________

### 5.3 SPECIAL FEATURES
- Modals/Popups: [Yes/No] _______________
- Tabs: [Yes/No] _______________
- Tab selectors: _______________

---

## 📊 SECTION 6: SAMPLE DATA

### 6.1 EXAMPLE PATIENT
- Name: _______________
- ID/MRN: _______________
- DOB: _______________

### 6.2 DATA FORMATS
- Date format: _______________
- Time format: _______________
- Special formatting: _______________

---

## 🧪 SECTION 7: TESTING NOTES

### 7.1 VERIFIED SELECTORS
- Tested selectors: _______________
- Working selectors: _______________
- Failed selectors: _______________

### 7.2 EDGE CASES
- Empty data handling: _______________
- Error scenarios: _______________
- Special cases: _______________

---

## ✅ COMPLETION CHECKLIST
- [ ] Login page analyzed
- [ ] Navigation mapped
- [ ] Patient list understood
- [ ] Demographics extraction planned
- [ ] Vitals extraction planned
- [ ] Medications extraction planned
- [ ] Lab results extraction planned
- [ ] Allergies extraction planned
- [ ] Medical history extraction planned
- [ ] Appointments extraction planned
- [ ] Selectors tested in browser console
- [ ] Sample data documented
- [ ] Edge cases identified

---

## 🛠️ **ADAPTER DEVELOPMENT NEXT STEPS**

### **Step 1: Create Adapter File**
```bash
cd /home/gsingh55/Projects/WebAutoDash/portal_adapters
cp _adapter_template.py YOUR_PORTAL_NAME_adapter.py
```

### **Step 2: Implement Required Functions**
Use the selectors from this analysis to implement:

#### **For All Patients (Section 3 selectors)**:
```python
async def extract_all_patients_data(page, config=None):
    try:
        # Navigate to patient list (Section 2.2)
        await page.goto('YOUR_PATIENT_LIST_URL')
        await page.wait_for_load_state('networkidle')
        
        # Wait for patient data (Section 3.2)
        await page.wait_for_selector('YOUR_PATIENT_ROW_SELECTOR', timeout=10000)
        
        patients_data = []
        # Get all patient rows
        patient_rows = await page.query_selector_all('YOUR_PATIENT_ROW_SELECTOR')
        
        for row in patient_rows:
            # Extract basic info from row
            patient_id = await row.query_selector('YOUR_PATIENT_ID_SELECTOR')
            detail_link = await row.query_selector('YOUR_DETAIL_LINK_SELECTOR')
            
            if detail_link:
                # Click to get detailed data
                await detail_link.click()
                await page.wait_for_load_state('networkidle')
                
                # Extract detailed patient data using Section 4 selectors
                patient_data = await extract_patient_details(page)
                patients_data.append(patient_data)
                
                # Navigate back to list
                await page.go_back()
                await page.wait_for_load_state('networkidle')
        
        return patients_data
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise
```

#### **For Single Patient**:
```python
async def extract_single_patient_data(page, patient_identifier, config=None):
    try:
        # Use search if available (Section 2.3)
        if 'YOUR_SEARCH_SELECTOR':
            await page.fill('YOUR_SEARCH_SELECTOR', patient_identifier)
            await page.keyboard.press('Enter')
        
        # Find and click patient
        patient_row = await page.query_selector(f'YOUR_PATIENT_ROW_SELECTOR containing {patient_identifier}')
        detail_link = await patient_row.query_selector('YOUR_DETAIL_LINK_SELECTOR')
        await detail_link.click()
        
        # Extract detailed data
        return await extract_patient_details(page)
    except Exception as e:
        logger.error(f"Single patient extraction failed: {str(e)}")
        raise
```

### **Step 3: Extract Patient Details Function**
Use Section 4 selectors for detailed extraction:

```python
async def extract_patient_details(page):
    # Wait for patient details page
    await page.wait_for_selector('YOUR_DEMOGRAPHICS_SECTION_SELECTOR')
    
    return {
        "patient_identifier": await page.text_content('YOUR_MRN_SELECTOR'),
        "demographics": {
            "name": await page.text_content('YOUR_NAME_SELECTOR'),
            "date_of_birth": await page.text_content('YOUR_DOB_SELECTOR'),
            "gender": await page.text_content('YOUR_GENDER_SELECTOR'),
            # ... use all Section 4.1 selectors
        },
        "medications": await extract_medications(page),
        "lab_results": await extract_lab_results(page),
        "allergies": await extract_allergies(page),
        "medical_history": await extract_medical_history(page),
        "appointments": await extract_appointments(page),
    }
```

### **Step 4: Register and Test**
```bash
curl -X POST http://localhost:5005/api/admin/adapters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "YOUR_PORTAL_NAME",
    "description": "Portal adapter based on analysis",
    "script_filename": "YOUR_PORTAL_NAME_adapter.py"
  }'
```

### **Error Prevention Checklist**
- [ ] Function names are exactly `extract_single_patient_data` and `extract_all_patients_data`
- [ ] Functions are module-level (not inside classes)
- [ ] No login logic in functions
- [ ] Used selectors from this analysis
- [ ] Added proper error handling
- [ ] Included screenshot capture for debugging

---

**Analysis Status:** [Complete/In Progress/Not Started]
**Ready for Adapter Development:** [Yes/No]
**Additional Notes:** _______________
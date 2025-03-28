# 🚨 EMERGENCY: Doctor Visit Portal Inspection Guide

## 🎯 Goal: Quickly inspect the doctor's portal and generate working adapter

### ⚡ STEP 1: Portal Access (1 minute)
1. **Open doctor's portal** in Chrome/Firefox
2. **Take note of the URL** (e.g., `https://portal.doctoroffice.com`)
3. **Screenshot the login page** for reference

### ⚡ STEP 2: Quick Element Inspection (2 minutes)

#### Login Form:
1. **Right-click username field** → Inspect → Copy selector
   - Look for: `#username`, `input[name="username"]`, etc.
2. **Right-click password field** → Inspect → Copy selector  
   - Look for: `#password`, `input[type="password"]`, etc.
3. **Right-click login button** → Inspect → Copy selector
   - Look for: `button[type="submit"]`, `#login-btn`, etc.

#### Patient Data:
1. **After login, find patient list/table**
2. **Right-click on patient table** → Inspect → Copy selector
   - Look for: `table`, `.patient-table`, `#patients`, etc.
3. **Right-click on first patient row** → Inspect → Copy selector
   - Look for: `tbody tr`, `.patient-row`, etc.

### ⚡ STEP 3: Navigation Pattern (1 minute)
1. **Click on a patient** - note the URL pattern
   - Example: `/patients/123/summary`
2. **Navigate to different sections** (meds, labs, etc.)
   - Note URLs: `/patients/123/medications`, `/patients/123/labs`

### ⚡ STEP 4: Quick Adapter Modification (2 minutes)

**Edit the emergency adapter file:**

```python
# In doctor_visit_emergency_adapter.py

# MODIFY THESE:
self.base_url = "DOCTOR_PORTAL_URL_HERE"
self.login_selectors = {
    "username": "USERNAME_SELECTOR_HERE",  # From Step 2
    "password": "PASSWORD_SELECTOR_HERE",  # From Step 2  
    "submit": "SUBMIT_BUTTON_SELECTOR_HERE"  # From Step 2
}

# In _extract_all_patients method:
patient_table = await page.query_selector('TABLE_SELECTOR_HERE')  # From Step 2
```

### ⚡ STEP 5: Quick Test (1 minute)

```bash
cd Projects/WebAutoDash
python portal_adapters/doctor_visit_emergency_adapter.py
```

## 🆘 If Portal Uses Different Structure:

### For Card-Based Portals:
- Look for `.card`, `.patient-card`, `div[class*="patient"]`
- Copy card container selector

### For List-Based Portals:  
- Look for `ul`, `li`, `.list-item`
- Copy list item selector

### For Complex Portals:
- **Take screenshots of each page**
- **Copy page HTML** (Ctrl+U → Save As → html)
- **Use fallback text extraction**

## 🔧 Emergency Selectors (Common Patterns):

```css
/* Login */
#username, input[name="username"], input[type="text"]
#password, input[name="password"], input[type="password"]  
button[type="submit"], .login-btn, #login

/* Patient Tables */
table, .patient-table, .data-table
tbody tr, .patient-row, tr[data-patient]

/* Patient Info */
.patient-info, .patient-details, .summary
.demographics, .patient-card
```

## 🚀 Quick Commands:

```bash
# Test adapter
cd Projects/WebAutoDash
python portal_adapters/doctor_visit_emergency_adapter.py

# Add to database  
python -c "from models import db, PortalAdapter; from app import create_app; app=create_app(); app.app_context().push(); adapter=PortalAdapter(name='Doctor Visit', script_filename='doctor_visit_emergency_adapter.py', is_active=True); db.session.add(adapter); db.session.commit(); print('✅ Adapter added!')"
```

## 📞 If You Get Stuck:
1. **Screenshot everything** - login, dashboard, patient page
2. **Save HTML source** of key pages  
3. **Note any error messages**
4. **Basic text extraction** works as fallback

**Remember: Getting ANY data extraction working is better than nothing!** 
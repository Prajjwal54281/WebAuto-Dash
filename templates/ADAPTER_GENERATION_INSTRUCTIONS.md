# 🛠️ ADAPTER GENERATION INSTRUCTIONS

## Using Your Analysis to Create Adapters

### Step 1: Complete Portal Analysis
Fill out the Portal Analysis Template completely

### Step 2: Provide Analysis to Developer
Share the completed analysis with these key sections:
- All CSS selectors
- Navigation flow
- Data structure
- Sample data

### Step 3: Adapter Development Process
The developer will create:
1. `{portal_name}_adapter.py` file
2. Registration in WebAutoDash
3. Test job for validation

### Step 4: Testing Workflow
1. Create test job in WebAutoDash
2. Manual login when prompted
3. Verify data extraction
4. Iterate if needed

## Required Information Checklist

### Must Have:
- [ ] Login form selectors
- [ ] Navigation to patients
- [ ] Patient list/search method
- [ ] Demographics selectors
- [ ] At least one medical data section

### Nice to Have:
- [ ] All medical data sections
- [ ] Error handling scenarios
- [ ] Loading states
- [ ] Pagination handling

### Critical for Success:
- [ ] Tested selectors in browser console
- [ ] Verified navigation flow manually
- [ ] Sample data provided
- [ ] Edge cases documented

## File Locations

### Templates (Copy from here):
- `/home/gsingh55/Projects/WebAutoDash/templates/PORTAL_ANALYSIS_TEMPLATE.md`

### Completed Analyses (Save here):
- `/home/gsingh55/Projects/WebAutoDash/portal_analyses/{PORTAL_NAME}_ANALYSIS.md`

### Generated Adapters (Created here):
- `/home/gsingh55/Projects/WebAutoDash/portal_adapters/{portal_name}_adapter.py`
- `/home/gsingh55/Projects/WebAutoDash/backend/portal_adapters/{portal_name}_adapter.py`

## Workflow Summary

1. **Copy** template from `templates/`
2. **Fill out** analysis completely
3. **Save** to `portal_analyses/`
4. **Share** with developer
5. **Test** generated adapter
6. **Iterate** if needed
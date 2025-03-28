"""
🎓 PRACTICE ADAPTER: Learn Portal Development Skills
This adapter uses httpbin.org to teach you the fundamentals of portal automation
before you work with real medical portals.

Author: Learning Exercise
Created: 2024-01-15
Purpose: Educational - Practice web automation skills
"""

import asyncio
from playwright.async_api import Page
import time
import json

async def extract_single_patient_data(page, patient_identifier, config=None):
    """
    🎓 PRACTICE: Extract data from httpbin.org/html
    This simulates extracting a single patient's data
    
    Args:
        page: Playwright page object (already logged in)
        patient_identifier: Patient ID to search for
        config: Optional configuration parameters
    
    Returns:
        dict: Structured patient data
    """
    
    try:
        print(f"🎓 PRACTICE: Starting extraction for patient {patient_identifier}")
        
        # Step 1: Navigate to the test page (simulates portal navigation)
        await page.goto('https://httpbin.org/html')
        await page.wait_for_load_state('networkidle')
        print("✅ Navigated to practice portal")
        
        # Step 2: Extract the page title (simulating patient name)
        title = await page.locator('h1').text_content()
        print(f"✅ Extracted title: {title}")
        
        # Step 3: Extract all paragraph text (simulating medical data)
        paragraphs = await page.locator('p').all()
        medical_notes = []
        for p in paragraphs:
            text = await p.text_content()
            if text and text.strip():
                medical_notes.append(text.strip())
        print(f"✅ Extracted {len(medical_notes)} medical notes")
        
        # Step 4: Simulate navigating to lab results page
        await page.goto('https://httpbin.org/json')
        await page.wait_for_load_state('networkidle')
        lab_response = await page.locator('body').text_content()
        print("✅ Simulated lab results extraction")
        
        # Step 5: Return structured data (this is the key part!)
        patient_data = {
            "patient_identifier": patient_identifier,
            "demographics": {
                "name": f"Practice Patient {patient_identifier}",
                "extracted_title": title,
                "source_url": "https://httpbin.org/html",
                "mrn": f"MRN{patient_identifier}",
                "date_of_birth": "1990-01-15",
                "gender": "Unknown",
                "phone": "555-0123",
                "email": f"{patient_identifier.lower()}@example.com"
            },
            "medical_notes": medical_notes,
            "vitals": [
                {
                    "date": "2024-01-15",
                    "blood_pressure": "120/80",
                    "heart_rate": "72 bpm",
                    "temperature": "98.6°F",
                    "weight": "150 lbs"
                }
            ],
            "lab_results": [
                {
                    "test_name": "Practice Blood Panel",
                    "date": "2024-01-15",
                    "results": {
                        "hemoglobin": "14.2 g/dL",
                        "glucose": "95 mg/dL",
                        "cholesterol": "180 mg/dL"
                    },
                    "reference_range": "Normal",
                    "status": "Completed",
                    "notes": "All values within normal range"
                },
                {
                    "test_name": "Liver Function Panel",
                    "date": "2024-01-10",
                    "results": {
                        "ALT": "25 U/L",
                        "AST": "22 U/L",
                        "bilirubin": "0.8 mg/dL"
                    },
                    "reference_range": "Normal",
                    "status": "Completed"
                }
            ],
            "medications": [
                {
                    "name": "Practice Medication A",
                    "dosage": "10mg",
                    "frequency": "Once daily",
                    "start_date": "2024-01-01",
                    "prescriber": "Dr. Practice"
                },
                {
                    "name": "Practice Medication B",
                    "dosage": "5mg",
                    "frequency": "Twice daily",
                    "start_date": "2023-12-15",
                    "prescriber": "Dr. Learning"
                }
            ],
            "allergies": [
                {
                    "allergen": "Practice Allergen",
                    "reaction": "Mild rash",
                    "severity": "Mild",
                    "date_identified": "2023-06-01"
                }
            ],
            "medical_history": [
                {
                    "condition": "Practice Condition",
                    "diagnosed_date": "2023-01-01",
                    "status": "Active",
                    "notes": "Under monitoring"
                }
            ],
            "appointments": [
                {
                    "date": "2024-02-01",
                    "time": "10:00 AM",
                    "provider": "Dr. Practice",
                    "type": "Follow-up",
                    "status": "Scheduled"
                }
            ],
            "extraction_metadata": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "adapter_version": "practice_v1.0",
                "extraction_mode": "single_patient",
                "portal_response_sample": lab_response[:100] if lab_response else "No response"
            }
        }
        
        print(f"🎉 PRACTICE: Successfully extracted data for {patient_identifier}")
        return patient_data
        
    except Exception as e:
        print(f"❌ PRACTICE ERROR: {str(e)}")
        return {
            "patient_identifier": patient_identifier,
            "error": str(e),
            "demographics": {},
            "lab_results": [],
            "medications": [],
            "allergies": [],
            "medical_history": [],
            "appointments": [],
            "extraction_metadata": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error_occurred": True
            }
        }

async def extract_all_patients_data(page, config=None):
    """
    🎓 PRACTICE: Extract data for multiple "patients"
    This simulates extracting all patients' data from a portal
    
    Args:
        page: Playwright page object (already logged in)
        config: Optional configuration parameters
    
    Returns:
        list: List of patient data dictionaries
    """
    
    try:
        print("🎓 PRACTICE: Starting all-patients extraction")
        
        # Simulate multiple patients in the portal
        patient_ids = ["PRACTICE001", "PRACTICE002", "PRACTICE003", "PRACTICE004"]
        all_patients = []
        
        for i, patient_id in enumerate(patient_ids):
            print(f"🔄 Processing patient {i+1}/{len(patient_ids)}: {patient_id}")
        
            # Extract data for each patient
            patient_data = await extract_single_patient_data(page, patient_id, config)
            
            # Add some variation to make each patient unique
            if patient_id == "PRACTICE002":
                patient_data["demographics"]["name"] = "John Practice Doe"
                patient_data["demographics"]["gender"] = "Male"
                patient_data["lab_results"][0]["results"]["glucose"] = "110 mg/dL"
                patient_data["medications"].append({
                    "name": "Diabetes Medication",
                    "dosage": "500mg",
                    "frequency": "Twice daily",
                    "start_date": "2024-01-05"
                })
            elif patient_id == "PRACTICE003":
                patient_data["demographics"]["name"] = "Jane Practice Smith"
                patient_data["demographics"]["gender"] = "Female"
                patient_data["lab_results"][0]["results"]["hemoglobin"] = "12.8 g/dL"
                patient_data["allergies"].append({
                    "allergen": "Penicillin",
                    "reaction": "Severe allergic reaction",
                    "severity": "Severe"
                })
            elif patient_id == "PRACTICE004":
                patient_data["demographics"]["name"] = "Bob Practice Wilson"
                patient_data["demographics"]["gender"] = "Male"
                patient_data["vitals"][0]["blood_pressure"] = "140/90"
                patient_data["medical_history"].append({
                    "condition": "Hypertension",
                    "diagnosed_date": "2023-08-15",
                    "status": "Active"
                })
            
            all_patients.append(patient_data)
            
            # Add a small delay to simulate real portal timing
            await asyncio.sleep(0.5)
        
        print(f"🎉 PRACTICE: Successfully extracted data for {len(all_patients)} patients")
        return all_patients
        
    except Exception as e:
        print(f"❌ PRACTICE ERROR in all-patients extraction: {str(e)}")
        return []

# 🎓 LEARNING HELPER FUNCTIONS

async def practice_element_finding(page):
    """
    🎓 LEARNING HELPER: Practice finding different types of elements
    This function teaches you how to locate elements on web pages
    """
    
    print("🎓 LEARNING: Practicing element finding...")
    
    try:
        # Navigate to a form page for practice
        await page.goto('https://httpbin.org/forms/post')
        await page.wait_for_load_state('networkidle')
        
        # Practice finding different types of form elements
        form_elements = {
            "email_field": await page.locator('input[name="email"]').count(),
            "password_field": await page.locator('input[name="password"]').count(),
            "submit_button": await page.locator('input[type="submit"]').count(),
            "all_inputs": await page.locator('input').count(),
            "form_element": await page.locator('form').count()
        }
        
        print("🎓 Element Finding Results:")
        for element_type, count in form_elements.items():
            print(f"  ✅ {element_type}: {count} found")
        
        # Practice extracting attributes
        if form_elements["email_field"] > 0:
            email_placeholder = await page.locator('input[name="email"]').get_attribute('placeholder')
            print(f"  📝 Email field placeholder: {email_placeholder}")
        
        return form_elements
        
    except Exception as e:
        print(f"❌ Error in element finding practice: {str(e)}")
        return {}

async def practice_form_interaction(page, patient_identifier):
    """
    🎓 LEARNING HELPER: Practice interacting with forms
    This teaches you how to fill forms and submit them
    """
    
    print(f"🎓 LEARNING: Practicing form interaction for {patient_identifier}...")
    
    try:
        # Navigate to a form page
        await page.goto('https://httpbin.org/forms/post')
        await page.wait_for_load_state('networkidle')
        
        # Fill out the form (simulating patient search)
        await page.fill('input[name="email"]', f'{patient_identifier}@practice.com')
        await page.fill('input[name="password"]', 'practice123')
        print("✅ Filled form fields")
        
        # Submit the form
        await page.click('input[type="submit"]')
        await page.wait_for_load_state('networkidle')
        print("✅ Submitted form")
        
        # Extract the response
        response_text = await page.locator('body').text_content()
        
        return {
            "patient_identifier": patient_identifier,
            "form_submitted": True,
            "response_preview": response_text[:200] if response_text else "No response",
            "interaction_successful": True
        }
        
    except Exception as e:
        print(f"❌ Error in form interaction practice: {str(e)}")
        return {
            "patient_identifier": patient_identifier,
            "form_submitted": False,
            "error": str(e),
            "interaction_successful": False
        }

# 🎓 MAIN LEARNING FUNCTION
async def run_learning_exercises(page):
    """
    🎓 COMPREHENSIVE LEARNING: Run all practice exercises
    Call this function to practice all the skills you'll need
    """
    
    print("🎓 STARTING COMPREHENSIVE LEARNING EXERCISES")
    print("=" * 50)
    
    # Exercise 1: Element Finding
    print("\n📚 Exercise 1: Element Finding")
    await practice_element_finding(page)
    
    # Exercise 2: Form Interaction
    print("\n📚 Exercise 2: Form Interaction")
    await practice_form_interaction(page, "LEARNING001")
    
    # Exercise 3: Single Patient Extraction
    print("\n📚 Exercise 3: Single Patient Extraction")
    single_result = await extract_single_patient_data(page, "LEARNING001")
    print(f"✅ Single patient extraction: {'SUCCESS' if single_result.get('patient_identifier') else 'FAILED'}")
    
    # Exercise 4: Multiple Patients Extraction
    print("\n📚 Exercise 4: Multiple Patients Extraction")
    all_results = await extract_all_patients_data(page)
    print(f"✅ All patients extraction: {len(all_results)} patients extracted")
    
    print("\n🎉 LEARNING EXERCISES COMPLETED!")
    print("You're now ready to work with real medical portals!")
    
    return {
        "exercises_completed": 4,
        "single_patient_success": bool(single_result.get('patient_identifier')),
        "all_patients_count": len(all_results),
        "ready_for_real_portals": True
} 
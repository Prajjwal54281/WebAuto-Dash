"""
Epic MyChart Portal Adapter
Extracts patient data from Epic MyChart patient portals
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

async def extract_single_patient_data(page, patient_identifier: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Extract data for a single patient from Epic MyChart
    
    Args:
        page: Playwright page object
        patient_identifier: Patient identifier (MRN, DOB, or name)
        config: Optional configuration dictionary
    
    Returns:
        Dictionary containing extracted patient data
    """
    try:
        logger.info(f"Starting Epic MyChart single patient extraction for: {patient_identifier}")
        
        # Wait for page to be fully loaded
        await page.wait_for_load_state('networkidle')
        
        # Initialize result structure
        patient_data = {
            "extraction_timestamp": datetime.now().isoformat(),
            "portal_type": "Epic MyChart",
            "patient_identifier": patient_identifier,
            "demographics": {},
            "lab_results": [],
            "medications": [],
            "appointments": [],
            "allergies": [],
            "immunizations": [],
            "vitals": [],
            "medical_history": [],
            "documents": []
        }
        
        # Navigate to patient summary/dashboard
        try:
            # Look for common Epic MyChart navigation elements
            dashboard_selectors = [
                'a[href*="summary"]',
                'a[href*="dashboard"]',
                '.patient-summary',
                '[data-testid="patient-summary"]'
            ]
            
            for selector in dashboard_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await page.wait_for_load_state('networkidle')
                    break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not navigate to patient summary: {e}")
        
        # Extract Demographics
        patient_data["demographics"] = await extract_demographics(page)
        
        # Extract Lab Results
        patient_data["lab_results"] = await extract_lab_results(page)
        
        # Extract Medications
        patient_data["medications"] = await extract_medications(page)
        
        # Extract Appointments
        patient_data["appointments"] = await extract_appointments(page)
        
        # Extract Allergies
        patient_data["allergies"] = await extract_allergies(page)
        
        # Extract Immunizations
        patient_data["immunizations"] = await extract_immunizations(page)
        
        # Extract Vitals
        patient_data["vitals"] = await extract_vitals(page)
        
        # Extract Medical History
        patient_data["medical_history"] = await extract_medical_history(page)
        
        # Extract Documents
        patient_data["documents"] = await extract_documents(page)
        
        logger.info(f"Epic MyChart extraction completed for patient: {patient_identifier}")
        return patient_data
        
    except Exception as e:
        logger.error(f"Error in Epic MyChart single patient extraction: {str(e)}")
        raise Exception(f"Epic MyChart extraction failed: {str(e)}")

async def extract_all_patients_data(page, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Extract data for all patients accessible in Epic MyChart
    Note: Epic MyChart typically shows only the logged-in patient's data
    
    Args:
        page: Playwright page object
        config: Optional configuration dictionary
    
    Returns:
        List of dictionaries containing extracted patient data
    """
    try:
        logger.info("Starting Epic MyChart all patients extraction")
        
        # Epic MyChart typically only shows the current patient's data
        # We'll extract the current patient's data
        current_patient_data = await extract_single_patient_data(page, "current_patient", config)
        
        return [current_patient_data]
        
    except Exception as e:
        logger.error(f"Error in Epic MyChart all patients extraction: {str(e)}")
        raise Exception(f"Epic MyChart all patients extraction failed: {str(e)}")

async def extract_demographics(page) -> Dict[str, Any]:
    """Extract patient demographics"""
    demographics = {}
    
    try:
        # Common Epic MyChart demographic selectors
        demo_selectors = {
            "name": [
                '.patient-name',
                '[data-testid="patient-name"]',
                '.demographics .name',
                'h1.patient-header'
            ],
            "dob": [
                '.patient-dob',
                '[data-testid="date-of-birth"]',
                '.demographics .dob',
                'span:contains("DOB")'
            ],
            "mrn": [
                '.patient-mrn',
                '[data-testid="mrn"]',
                '.demographics .mrn',
                'span:contains("MRN")'
            ],
            "gender": [
                '.patient-gender',
                '[data-testid="gender"]',
                '.demographics .gender'
            ],
            "address": [
                '.patient-address',
                '[data-testid="address"]',
                '.demographics .address'
            ],
            "phone": [
                '.patient-phone',
                '[data-testid="phone"]',
                '.demographics .phone'
            ]
        }
        
        for field, selectors in demo_selectors.items():
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and text.strip():
                            demographics[field] = text.strip()
                            break
                except:
                    continue
        
        logger.info(f"Extracted demographics: {len(demographics)} fields")
        
    except Exception as e:
        logger.error(f"Error extracting demographics: {e}")
    
    return demographics

async def extract_lab_results(page) -> List[Dict[str, Any]]:
    """Extract lab results"""
    lab_results = []
    
    try:
        # Navigate to lab results section
        lab_nav_selectors = [
            'a[href*="lab"]',
            'a[href*="results"]',
            '.nav-lab-results',
            '[data-testid="lab-results"]'
        ]
        
        for selector in lab_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract lab result entries
        lab_entries = await page.query_selector_all('.lab-result, .test-result, [data-testid="lab-entry"]')
        
        for entry in lab_entries:
            try:
                lab_result = {}
                
                # Extract test name
                name_element = await entry.query_selector('.test-name, .lab-name, .result-name')
                if name_element:
                    lab_result["test_name"] = await name_element.text_content()
                
                # Extract result value
                value_element = await entry.query_selector('.test-value, .lab-value, .result-value')
                if value_element:
                    lab_result["value"] = await value_element.text_content()
                
                # Extract reference range
                range_element = await entry.query_selector('.reference-range, .normal-range')
                if range_element:
                    lab_result["reference_range"] = await range_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.test-date, .lab-date, .result-date')
                if date_element:
                    lab_result["date"] = await date_element.text_content()
                
                # Extract status/flag
                status_element = await entry.query_selector('.test-status, .lab-flag, .abnormal-flag')
                if status_element:
                    lab_result["status"] = await status_element.text_content()
                
                if lab_result:
                    lab_results.append(lab_result)
                    
            except Exception as e:
                logger.warning(f"Error extracting lab result entry: {e}")
                continue
        
        logger.info(f"Extracted {len(lab_results)} lab results")
        
    except Exception as e:
        logger.error(f"Error extracting lab results: {e}")
    
    return lab_results

async def extract_medications(page) -> List[Dict[str, Any]]:
    """Extract medications"""
    medications = []
    
    try:
        # Navigate to medications section
        med_nav_selectors = [
            'a[href*="medication"]',
            'a[href*="prescriptions"]',
            '.nav-medications',
            '[data-testid="medications"]'
        ]
        
        for selector in med_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract medication entries
        med_entries = await page.query_selector_all('.medication, .prescription, [data-testid="medication-entry"]')
        
        for entry in med_entries:
            try:
                medication = {}
                
                # Extract medication name
                name_element = await entry.query_selector('.med-name, .medication-name, .drug-name')
                if name_element:
                    medication["name"] = await name_element.text_content()
                
                # Extract dosage
                dose_element = await entry.query_selector('.dosage, .dose, .strength')
                if dose_element:
                    medication["dosage"] = await dose_element.text_content()
                
                # Extract frequency
                freq_element = await entry.query_selector('.frequency, .directions')
                if freq_element:
                    medication["frequency"] = await freq_element.text_content()
                
                # Extract prescriber
                prescriber_element = await entry.query_selector('.prescriber, .doctor')
                if prescriber_element:
                    medication["prescriber"] = await prescriber_element.text_content()
                
                # Extract start date
                start_element = await entry.query_selector('.start-date, .prescribed-date')
                if start_element:
                    medication["start_date"] = await start_element.text_content()
                
                if medication:
                    medications.append(medication)
                    
            except Exception as e:
                logger.warning(f"Error extracting medication entry: {e}")
                continue
        
        logger.info(f"Extracted {len(medications)} medications")
        
    except Exception as e:
        logger.error(f"Error extracting medications: {e}")
    
    return medications

async def extract_appointments(page) -> List[Dict[str, Any]]:
    """Extract appointments"""
    appointments = []
    
    try:
        # Navigate to appointments section
        appt_nav_selectors = [
            'a[href*="appointment"]',
            'a[href*="visits"]',
            '.nav-appointments',
            '[data-testid="appointments"]'
        ]
        
        for selector in appt_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract appointment entries
        appt_entries = await page.query_selector_all('.appointment, .visit, [data-testid="appointment-entry"]')
        
        for entry in appt_entries:
            try:
                appointment = {}
                
                # Extract appointment type
                type_element = await entry.query_selector('.appt-type, .visit-type')
                if type_element:
                    appointment["type"] = await type_element.text_content()
                
                # Extract date/time
                datetime_element = await entry.query_selector('.appt-datetime, .visit-date')
                if datetime_element:
                    appointment["datetime"] = await datetime_element.text_content()
                
                # Extract provider
                provider_element = await entry.query_selector('.provider, .doctor')
                if provider_element:
                    appointment["provider"] = await provider_element.text_content()
                
                # Extract location
                location_element = await entry.query_selector('.location, .clinic')
                if location_element:
                    appointment["location"] = await location_element.text_content()
                
                # Extract status
                status_element = await entry.query_selector('.status, .appt-status')
                if status_element:
                    appointment["status"] = await status_element.text_content()
                
                if appointment:
                    appointments.append(appointment)
                    
            except Exception as e:
                logger.warning(f"Error extracting appointment entry: {e}")
                continue
        
        logger.info(f"Extracted {len(appointments)} appointments")
        
    except Exception as e:
        logger.error(f"Error extracting appointments: {e}")
    
    return appointments

async def extract_allergies(page) -> List[Dict[str, Any]]:
    """Extract allergies"""
    allergies = []
    
    try:
        # Look for allergies section
        allergy_entries = await page.query_selector_all('.allergy, .allergies .item, [data-testid="allergy-entry"]')
        
        for entry in allergy_entries:
            try:
                allergy = {}
                
                # Extract allergen
                allergen_element = await entry.query_selector('.allergen, .allergy-name')
                if allergen_element:
                    allergy["allergen"] = await allergen_element.text_content()
                
                # Extract reaction
                reaction_element = await entry.query_selector('.reaction, .allergy-reaction')
                if reaction_element:
                    allergy["reaction"] = await reaction_element.text_content()
                
                # Extract severity
                severity_element = await entry.query_selector('.severity, .allergy-severity')
                if severity_element:
                    allergy["severity"] = await severity_element.text_content()
                
                if allergy:
                    allergies.append(allergy)
                    
            except Exception as e:
                logger.warning(f"Error extracting allergy entry: {e}")
                continue
        
        logger.info(f"Extracted {len(allergies)} allergies")
        
    except Exception as e:
        logger.error(f"Error extracting allergies: {e}")
    
    return allergies

async def extract_immunizations(page) -> List[Dict[str, Any]]:
    """Extract immunizations"""
    immunizations = []
    
    try:
        # Navigate to immunizations section
        imm_nav_selectors = [
            'a[href*="immunization"]',
            'a[href*="vaccination"]',
            '.nav-immunizations',
            '[data-testid="immunizations"]'
        ]
        
        for selector in imm_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract immunization entries
        imm_entries = await page.query_selector_all('.immunization, .vaccination, [data-testid="immunization-entry"]')
        
        for entry in imm_entries:
            try:
                immunization = {}
                
                # Extract vaccine name
                name_element = await entry.query_selector('.vaccine-name, .immunization-name')
                if name_element:
                    immunization["vaccine"] = await name_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.vaccine-date, .immunization-date')
                if date_element:
                    immunization["date"] = await date_element.text_content()
                
                # Extract provider
                provider_element = await entry.query_selector('.provider, .administered-by')
                if provider_element:
                    immunization["provider"] = await provider_element.text_content()
                
                if immunization:
                    immunizations.append(immunization)
                    
            except Exception as e:
                logger.warning(f"Error extracting immunization entry: {e}")
                continue
        
        logger.info(f"Extracted {len(immunizations)} immunizations")
        
    except Exception as e:
        logger.error(f"Error extracting immunizations: {e}")
    
    return immunizations

async def extract_vitals(page) -> List[Dict[str, Any]]:
    """Extract vital signs"""
    vitals = []
    
    try:
        # Look for vitals section
        vital_entries = await page.query_selector_all('.vital, .vitals .item, [data-testid="vital-entry"]')
        
        for entry in vital_entries:
            try:
                vital = {}
                
                # Extract vital type
                type_element = await entry.query_selector('.vital-type, .vital-name')
                if type_element:
                    vital["type"] = await type_element.text_content()
                
                # Extract value
                value_element = await entry.query_selector('.vital-value, .measurement')
                if value_element:
                    vital["value"] = await value_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.vital-date, .measurement-date')
                if date_element:
                    vital["date"] = await date_element.text_content()
                
                if vital:
                    vitals.append(vital)
                    
            except Exception as e:
                logger.warning(f"Error extracting vital entry: {e}")
                continue
        
        logger.info(f"Extracted {len(vitals)} vitals")
        
    except Exception as e:
        logger.error(f"Error extracting vitals: {e}")
    
    return vitals

async def extract_medical_history(page) -> List[Dict[str, Any]]:
    """Extract medical history"""
    medical_history = []
    
    try:
        # Look for medical history section
        history_entries = await page.query_selector_all('.medical-history .item, .problem, [data-testid="history-entry"]')
        
        for entry in history_entries:
            try:
                history_item = {}
                
                # Extract condition
                condition_element = await entry.query_selector('.condition, .problem-name')
                if condition_element:
                    history_item["condition"] = await condition_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.onset-date, .problem-date')
                if date_element:
                    history_item["date"] = await date_element.text_content()
                
                # Extract status
                status_element = await entry.query_selector('.status, .problem-status')
                if status_element:
                    history_item["status"] = await status_element.text_content()
                
                if history_item:
                    medical_history.append(history_item)
                    
            except Exception as e:
                logger.warning(f"Error extracting medical history entry: {e}")
                continue
        
        logger.info(f"Extracted {len(medical_history)} medical history items")
        
    except Exception as e:
        logger.error(f"Error extracting medical history: {e}")
    
    return medical_history

async def extract_documents(page) -> List[Dict[str, Any]]:
    """Extract documents and reports"""
    documents = []
    
    try:
        # Navigate to documents section
        doc_nav_selectors = [
            'a[href*="document"]',
            'a[href*="reports"]',
            '.nav-documents',
            '[data-testid="documents"]'
        ]
        
        for selector in doc_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract document entries
        doc_entries = await page.query_selector_all('.document, .report, [data-testid="document-entry"]')
        
        for entry in doc_entries:
            try:
                document = {}
                
                # Extract document name
                name_element = await entry.query_selector('.doc-name, .document-title')
                if name_element:
                    document["name"] = await name_element.text_content()
                
                # Extract document type
                type_element = await entry.query_selector('.doc-type, .document-type')
                if type_element:
                    document["type"] = await type_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.doc-date, .document-date')
                if date_element:
                    document["date"] = await date_element.text_content()
                
                # Extract download link
                link_element = await entry.query_selector('a[href*="download"], a[href*="view"]')
                if link_element:
                    document["download_url"] = await link_element.get_attribute('href')
                
                if document:
                    documents.append(document)
                    
            except Exception as e:
                logger.warning(f"Error extracting document entry: {e}")
                continue
        
        logger.info(f"Extracted {len(documents)} documents")
        
    except Exception as e:
        logger.error(f"Error extracting documents: {e}")
    
    return documents 
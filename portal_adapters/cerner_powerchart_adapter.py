"""
Cerner PowerChart Portal Adapter
Extracts patient data from Cerner PowerChart patient portals
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

async def extract_single_patient_data(page, patient_identifier: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Extract data for a single patient from Cerner PowerChart
    
    Args:
        page: Playwright page object
        patient_identifier: Patient identifier (MRN, DOB, or name)
        config: Optional configuration dictionary
    
    Returns:
        Dictionary containing extracted patient data
    """
    try:
        logger.info(f"Starting Cerner PowerChart single patient extraction for: {patient_identifier}")
        
        # Wait for page to be fully loaded
        await page.wait_for_load_state('networkidle')
        
        # Initialize result structure
        patient_data = {
            "extraction_timestamp": datetime.now().isoformat(),
            "portal_type": "Cerner PowerChart",
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
        
        # Navigate to patient chart if needed
        try:
            # Look for common Cerner PowerChart navigation elements
            chart_selectors = [
                'a[href*="chart"]',
                'a[href*="patient"]',
                '.patient-chart',
                '[data-testid="patient-chart"]',
                '.chart-tab'
            ]
            
            for selector in chart_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await page.wait_for_load_state('networkidle')
                    break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not navigate to patient chart: {e}")
        
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
        
        logger.info(f"Cerner PowerChart extraction completed for patient: {patient_identifier}")
        return patient_data
        
    except Exception as e:
        logger.error(f"Error in Cerner PowerChart single patient extraction: {str(e)}")
        raise Exception(f"Cerner PowerChart extraction failed: {str(e)}")

async def extract_all_patients_data(page, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Extract data for all patients accessible in Cerner PowerChart
    
    Args:
        page: Playwright page object
        config: Optional configuration dictionary
    
    Returns:
        List of dictionaries containing extracted patient data
    """
    try:
        logger.info("Starting Cerner PowerChart all patients extraction")
        
        all_patients = []
        
        # Navigate to patient list/search
        try:
            patient_list_selectors = [
                'a[href*="patient-list"]',
                'a[href*="search"]',
                '.patient-search',
                '[data-testid="patient-list"]'
            ]
            
            for selector in patient_list_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await page.wait_for_load_state('networkidle')
                    break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not navigate to patient list: {e}")
        
        # Find patient entries
        patient_entries = await page.query_selector_all('.patient-entry, .patient-row, [data-testid="patient-item"]')
        
        for i, entry in enumerate(patient_entries):
            try:
                # Extract patient identifier
                patient_id = f"patient_{i+1}"
                
                # Click on patient to view their chart
                await entry.click()
                await page.wait_for_load_state('networkidle')
                
                # Extract patient data
                patient_data = await extract_single_patient_data(page, patient_id, config)
                all_patients.append(patient_data)
                
                # Add politeness delay
                await page.wait_for_timeout(2000)
                
                # Navigate back to patient list
                back_selectors = [
                    'button[title*="back"]',
                    'a[href*="patient-list"]',
                    '.back-button',
                    '[data-testid="back"]'
                ]
                
                for selector in back_selectors:
                    try:
                        await page.click(selector, timeout=3000)
                        await page.wait_for_load_state('networkidle')
                        break
                    except:
                        continue
                
            except Exception as e:
                logger.warning(f"Error extracting patient {i+1}: {e}")
                continue
        
        logger.info(f"Cerner PowerChart extraction completed for {len(all_patients)} patients")
        return all_patients
        
    except Exception as e:
        logger.error(f"Error in Cerner PowerChart all patients extraction: {str(e)}")
        raise Exception(f"Cerner PowerChart all patients extraction failed: {str(e)}")

async def extract_demographics(page) -> Dict[str, Any]:
    """Extract patient demographics"""
    demographics = {}
    
    try:
        # Common Cerner PowerChart demographic selectors
        demo_selectors = {
            "name": [
                '.patient-name',
                '[data-testid="patient-name"]',
                '.demographics-name',
                '.chart-header .name'
            ],
            "dob": [
                '.patient-dob',
                '[data-testid="dob"]',
                '.demographics-dob',
                '.birth-date'
            ],
            "mrn": [
                '.patient-mrn',
                '[data-testid="mrn"]',
                '.medical-record-number',
                '.patient-id'
            ],
            "gender": [
                '.patient-gender',
                '[data-testid="gender"]',
                '.demographics-gender',
                '.sex'
            ],
            "address": [
                '.patient-address',
                '[data-testid="address"]',
                '.demographics-address',
                '.home-address'
            ],
            "phone": [
                '.patient-phone',
                '[data-testid="phone"]',
                '.demographics-phone',
                '.contact-phone'
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
            '.lab-tab',
            '[data-testid="lab-results"]',
            '.results-tab'
        ]
        
        for selector in lab_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract lab result entries
        lab_entries = await page.query_selector_all('.lab-result, .result-row, [data-testid="lab-entry"], .test-result')
        
        for entry in lab_entries:
            try:
                lab_result = {}
                
                # Extract test name
                name_element = await entry.query_selector('.test-name, .lab-name, .result-name, .component-name')
                if name_element:
                    lab_result["test_name"] = await name_element.text_content()
                
                # Extract result value
                value_element = await entry.query_selector('.test-value, .lab-value, .result-value, .numeric-result')
                if value_element:
                    lab_result["value"] = await value_element.text_content()
                
                # Extract reference range
                range_element = await entry.query_selector('.reference-range, .normal-range, .ref-range')
                if range_element:
                    lab_result["reference_range"] = await range_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.test-date, .lab-date, .result-date, .collection-date')
                if date_element:
                    lab_result["date"] = await date_element.text_content()
                
                # Extract status/flag
                status_element = await entry.query_selector('.test-status, .lab-flag, .abnormal-flag, .result-flag')
                if status_element:
                    lab_result["status"] = await status_element.text_content()
                
                # Extract units
                units_element = await entry.query_selector('.units, .test-units, .measurement-units')
                if units_element:
                    lab_result["units"] = await units_element.text_content()
                
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
            'a[href*="meds"]',
            '.medication-tab',
            '[data-testid="medications"]',
            '.meds-tab'
        ]
        
        for selector in med_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract medication entries
        med_entries = await page.query_selector_all('.medication, .med-row, [data-testid="medication-entry"], .prescription')
        
        for entry in med_entries:
            try:
                medication = {}
                
                # Extract medication name
                name_element = await entry.query_selector('.med-name, .medication-name, .drug-name, .generic-name')
                if name_element:
                    medication["name"] = await name_element.text_content()
                
                # Extract dosage
                dose_element = await entry.query_selector('.dosage, .dose, .strength, .medication-dose')
                if dose_element:
                    medication["dosage"] = await dose_element.text_content()
                
                # Extract frequency
                freq_element = await entry.query_selector('.frequency, .directions, .sig, .administration')
                if freq_element:
                    medication["frequency"] = await freq_element.text_content()
                
                # Extract route
                route_element = await entry.query_selector('.route, .administration-route')
                if route_element:
                    medication["route"] = await route_element.text_content()
                
                # Extract prescriber
                prescriber_element = await entry.query_selector('.prescriber, .doctor, .ordering-provider')
                if prescriber_element:
                    medication["prescriber"] = await prescriber_element.text_content()
                
                # Extract start date
                start_element = await entry.query_selector('.start-date, .prescribed-date, .order-date')
                if start_element:
                    medication["start_date"] = await start_element.text_content()
                
                # Extract status
                status_element = await entry.query_selector('.status, .med-status, .order-status')
                if status_element:
                    medication["status"] = await status_element.text_content()
                
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
            'a[href*="schedule"]',
            '.appointment-tab',
            '[data-testid="appointments"]',
            '.schedule-tab'
        ]
        
        for selector in appt_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract appointment entries
        appt_entries = await page.query_selector_all('.appointment, .appt-row, [data-testid="appointment-entry"], .visit')
        
        for entry in appt_entries:
            try:
                appointment = {}
                
                # Extract appointment type
                type_element = await entry.query_selector('.appt-type, .visit-type, .appointment-type')
                if type_element:
                    appointment["type"] = await type_element.text_content()
                
                # Extract date/time
                datetime_element = await entry.query_selector('.appt-datetime, .visit-date, .appointment-time')
                if datetime_element:
                    appointment["datetime"] = await datetime_element.text_content()
                
                # Extract provider
                provider_element = await entry.query_selector('.provider, .doctor, .attending-physician')
                if provider_element:
                    appointment["provider"] = await provider_element.text_content()
                
                # Extract location
                location_element = await entry.query_selector('.location, .clinic, .department')
                if location_element:
                    appointment["location"] = await location_element.text_content()
                
                # Extract status
                status_element = await entry.query_selector('.status, .appt-status, .visit-status')
                if status_element:
                    appointment["status"] = await status_element.text_content()
                
                # Extract reason
                reason_element = await entry.query_selector('.reason, .chief-complaint, .visit-reason')
                if reason_element:
                    appointment["reason"] = await reason_element.text_content()
                
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
        # Navigate to allergies section
        allergy_nav_selectors = [
            'a[href*="allerg"]',
            '.allergy-tab',
            '[data-testid="allergies"]',
            '.allergies-tab'
        ]
        
        for selector in allergy_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract allergy entries
        allergy_entries = await page.query_selector_all('.allergy, .allergy-row, [data-testid="allergy-entry"]')
        
        for entry in allergy_entries:
            try:
                allergy = {}
                
                # Extract allergen
                allergen_element = await entry.query_selector('.allergen, .allergy-name, .substance')
                if allergen_element:
                    allergy["allergen"] = await allergen_element.text_content()
                
                # Extract reaction
                reaction_element = await entry.query_selector('.reaction, .allergy-reaction, .adverse-reaction')
                if reaction_element:
                    allergy["reaction"] = await reaction_element.text_content()
                
                # Extract severity
                severity_element = await entry.query_selector('.severity, .allergy-severity, .reaction-severity')
                if severity_element:
                    allergy["severity"] = await severity_element.text_content()
                
                # Extract onset date
                onset_element = await entry.query_selector('.onset-date, .allergy-date, .reaction-date')
                if onset_element:
                    allergy["onset_date"] = await onset_element.text_content()
                
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
            '.immunization-tab',
            '[data-testid="immunizations"]',
            '.vaccines-tab'
        ]
        
        for selector in imm_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract immunization entries
        imm_entries = await page.query_selector_all('.immunization, .vaccine-row, [data-testid="immunization-entry"]')
        
        for entry in imm_entries:
            try:
                immunization = {}
                
                # Extract vaccine name
                name_element = await entry.query_selector('.vaccine-name, .immunization-name, .vaccine-type')
                if name_element:
                    immunization["vaccine"] = await name_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.vaccine-date, .immunization-date, .administration-date')
                if date_element:
                    immunization["date"] = await date_element.text_content()
                
                # Extract provider
                provider_element = await entry.query_selector('.provider, .administered-by, .administering-provider')
                if provider_element:
                    immunization["provider"] = await provider_element.text_content()
                
                # Extract lot number
                lot_element = await entry.query_selector('.lot-number, .vaccine-lot, .batch-number')
                if lot_element:
                    immunization["lot_number"] = await lot_element.text_content()
                
                # Extract site
                site_element = await entry.query_selector('.administration-site, .injection-site')
                if site_element:
                    immunization["site"] = await site_element.text_content()
                
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
        # Navigate to vitals section
        vital_nav_selectors = [
            'a[href*="vital"]',
            '.vitals-tab',
            '[data-testid="vitals"]',
            '.vital-signs-tab'
        ]
        
        for selector in vital_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract vital entries
        vital_entries = await page.query_selector_all('.vital, .vital-row, [data-testid="vital-entry"]')
        
        for entry in vital_entries:
            try:
                vital = {}
                
                # Extract vital type
                type_element = await entry.query_selector('.vital-type, .vital-name, .measurement-type')
                if type_element:
                    vital["type"] = await type_element.text_content()
                
                # Extract value
                value_element = await entry.query_selector('.vital-value, .measurement, .vital-measurement')
                if value_element:
                    vital["value"] = await value_element.text_content()
                
                # Extract units
                units_element = await entry.query_selector('.units, .vital-units, .measurement-units')
                if units_element:
                    vital["units"] = await units_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.vital-date, .measurement-date, .taken-date')
                if date_element:
                    vital["date"] = await date_element.text_content()
                
                # Extract time
                time_element = await entry.query_selector('.vital-time, .measurement-time, .taken-time')
                if time_element:
                    vital["time"] = await time_element.text_content()
                
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
        # Navigate to medical history section
        history_nav_selectors = [
            'a[href*="history"]',
            'a[href*="problem"]',
            '.history-tab',
            '[data-testid="medical-history"]',
            '.problems-tab'
        ]
        
        for selector in history_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract history entries
        history_entries = await page.query_selector_all('.medical-history .item, .problem, [data-testid="history-entry"], .diagnosis')
        
        for entry in history_entries:
            try:
                history_item = {}
                
                # Extract condition
                condition_element = await entry.query_selector('.condition, .problem-name, .diagnosis-name')
                if condition_element:
                    history_item["condition"] = await condition_element.text_content()
                
                # Extract ICD code
                icd_element = await entry.query_selector('.icd-code, .diagnosis-code, .problem-code')
                if icd_element:
                    history_item["icd_code"] = await icd_element.text_content()
                
                # Extract onset date
                date_element = await entry.query_selector('.onset-date, .problem-date, .diagnosis-date')
                if date_element:
                    history_item["date"] = await date_element.text_content()
                
                # Extract status
                status_element = await entry.query_selector('.status, .problem-status, .diagnosis-status')
                if status_element:
                    history_item["status"] = await status_element.text_content()
                
                # Extract provider
                provider_element = await entry.query_selector('.provider, .diagnosing-provider')
                if provider_element:
                    history_item["provider"] = await provider_element.text_content()
                
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
            '.documents-tab',
            '[data-testid="documents"]',
            '.reports-tab'
        ]
        
        for selector in doc_nav_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state('networkidle')
                break
            except:
                continue
        
        # Extract document entries
        doc_entries = await page.query_selector_all('.document, .report, [data-testid="document-entry"], .clinical-document')
        
        for entry in doc_entries:
            try:
                document = {}
                
                # Extract document name
                name_element = await entry.query_selector('.doc-name, .document-title, .report-name')
                if name_element:
                    document["name"] = await name_element.text_content()
                
                # Extract document type
                type_element = await entry.query_selector('.doc-type, .document-type, .report-type')
                if type_element:
                    document["type"] = await type_element.text_content()
                
                # Extract date
                date_element = await entry.query_selector('.doc-date, .document-date, .report-date')
                if date_element:
                    document["date"] = await date_element.text_content()
                
                # Extract author
                author_element = await entry.query_selector('.author, .document-author, .report-author')
                if author_element:
                    document["author"] = await author_element.text_content()
                
                # Extract status
                status_element = await entry.query_selector('.status, .document-status, .report-status')
                if status_element:
                    document["status"] = await status_element.text_content()
                
                # Extract download link
                link_element = await entry.query_selector('a[href*="download"], a[href*="view"], a[href*="open"]')
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
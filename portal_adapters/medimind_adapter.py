"""
MediMind Portal Adapter
Extracts patient data from the MediMind portal running on localhost:3004
Supports comprehensive data extraction including demographics, medications, lab results, allergies, problems, and appointments.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MediMindAdapter:
    def __init__(self):
        self.name = "MediMind Portal"
        self.base_url = "http://localhost:3004"
        self.login_url = f"{self.base_url}/login"
        self.dashboard_url = f"{self.base_url}/dashboard"
        
        # Extraction configuration - Extended timeouts for manual login workflow
        self.extraction_timeout = 120000  # 2 minutes (was 30 seconds)
        self.navigation_timeout = 30000   # 30 seconds (was 10 seconds)
        self.element_timeout = 30000      # 30 seconds (was 15 seconds)
        
    async def extract_patient_data(self, target_url: str, credentials: Dict[str, str], 
                                 extraction_mode: str = "ALL_PATIENTS", 
                                 patient_identifier: Optional[str] = None) -> Dict[str, Any]:
        """
        Main extraction method for MediMind portal
        
        Args:
            target_url: Portal URL (should be login page)
            credentials: Dictionary with 'username' and 'password'
            extraction_mode: 'ALL_PATIENTS' or 'SINGLE_PATIENT'
            patient_identifier: Patient ID/MRN for single patient extraction
            
        Returns:
            Dictionary containing extracted patient data
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=500)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                # Step 1: Login to the portal
                await self._perform_login(page, credentials)
                
                # Step 2: Navigate to dashboard
                await self._navigate_to_dashboard(page)
                
                # Step 3: Extract patient data based on mode
                if extraction_mode == "SINGLE_PATIENT" and patient_identifier:
                    patients_data = await self._extract_single_patient(page, patient_identifier)
                else:
                    patients_data = await self._extract_all_patients(page)
                
                return {
                    "extraction_timestamp": datetime.now().isoformat(),
                    "portal_name": self.name,
                    "extraction_mode": extraction_mode,
                    "total_patients": len(patients_data),
                    "patients": patients_data,
                    "status": "success"
                }
                
            except Exception as e:
                logger.error(f"Extraction failed: {str(e)}")
                return {
                    "extraction_timestamp": datetime.now().isoformat(),
                    "portal_name": self.name,
                    "status": "error",
                    "error_message": str(e),
                    "patients": []
                }
                
            finally:
                await browser.close()

    async def _perform_login(self, page: Page, credentials: Dict[str, str]) -> None:
        """Perform login to MediMind portal"""
        logger.info("Navigating to MediMind login page...")
        await page.goto(self.login_url, wait_until='networkidle')
        
        # Fill username field
        await page.fill('#username', credentials['username'])
        logger.info(f"Entered username: {credentials['username']}")
        
        # Fill password field
        await page.fill('#password', credentials['password'])
        logger.info("Entered password")
        
        # Click submit button
        await page.click('button[type="submit"]')
        logger.info("Clicked login button")
        
        # Wait for redirect to dashboard
        await page.wait_for_url(f"{self.base_url}/dashboard", timeout=self.navigation_timeout)
        logger.info("Successfully logged in and redirected to dashboard")

    async def _navigate_to_dashboard(self, page: Page) -> None:
        """Navigate to the dashboard page"""
        await page.goto(self.dashboard_url, wait_until='networkidle')
        
        # Wait for the page to load - be more flexible with selectors
        try:
            # Wait for any of these common elements that might indicate a loaded dashboard
            await page.wait_for_function(
                """() => {
                    return document.readyState === 'complete' && 
                           document.body.innerText.length > 0
                }""",
                timeout=self.element_timeout
            )
            logger.info("Dashboard page loaded successfully")
        except Exception as e:
            logger.warning(f"Dashboard wait timeout, but continuing: {str(e)}")

    async def _extract_all_patients(self, page: Page) -> List[Dict[str, Any]]:
        """Extract data for all patients visible on the dashboard"""
        patients_data = []
        
        # Take a screenshot for debugging
        try:
            await page.screenshot(path='medimind_debug_dashboard.png')
            logger.info("📸 Dashboard screenshot saved for debugging")
        except Exception as e:
            logger.warning(f"Failed to save screenshot: {e}")
        
        # Save page HTML for analysis
        try:
            page_content = await page.content()
            with open('medimind_dashboard_content.html', 'w', encoding='utf-8') as f:
                f.write(page_content)
            logger.info("📄 Dashboard HTML saved for analysis")
        except Exception as e:
            logger.warning(f"Failed to save HTML: {e}")
        
        # Get all text content to understand what's on the page
        try:
            visible_text = await page.text_content('body')
            logger.info(f"📝 Dashboard contains {len(visible_text) if visible_text else 0} characters of text")
            if visible_text:
                logger.info(f"📋 First 300 chars: {visible_text[:300]}")
        except Exception as e:
            logger.warning(f"Failed to get page text: {e}")
        
        # Try multiple strategies to find patient data
        
        # Strategy 1: Look for specific patient row data-testids (original approach)
        try:
            patient_rows = await page.query_selector_all('[data-testid^="patient-row-"]')
            if patient_rows:
                logger.info(f"✅ Strategy 1: Found {len(patient_rows)} patient rows with data-testid")
                return await self._extract_from_patient_rows(page, patient_rows)
        except Exception as e:
            logger.info(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Look for table rows (more generic)
        try:
            # Look for tables that might contain patient data
            tables = await page.query_selector_all('table')
            logger.info(f"🔍 Strategy 2: Found {len(tables)} tables on page")
            
            for i, table in enumerate(tables):
                rows = await table.query_selector_all('tr')
                if len(rows) > 1:  # Has header + data rows
                    logger.info(f"📋 Table {i+1} has {len(rows)} rows")
                    # Try to extract from this table
                    table_data = await self._extract_from_table(page, table)
                    if table_data:
                        logger.info(f"✅ Strategy 2: Successfully extracted {len(table_data)} patients from table {i+1}")
                        return table_data
        except Exception as e:
            logger.info(f"Strategy 2 failed: {e}")
        
        # Strategy 3: Look for patient links or cards
        try:
            # Look for links that might lead to patient pages
            patient_links = await page.query_selector_all('a[href*="/patient"], a[href*="/summary"], a[href*="patient"]')
            logger.info(f"🔗 Strategy 3: Found {len(patient_links)} potential patient links")
            
            if patient_links:
                return await self._extract_from_patient_links(page, patient_links)
        except Exception as e:
            logger.info(f"Strategy 3 failed: {e}")
        
        # Strategy 4: Look for any cards or divs that might contain patient info
        try:
            # Look for common card-like structures
            cards = await page.query_selector_all('.card, .patient-card, [class*="patient"], [class*="card"]')
            logger.info(f"💳 Strategy 4: Found {len(cards)} potential patient cards")
            
            if cards:
                return await self._extract_from_patient_cards(page, cards)
        except Exception as e:
            logger.info(f"Strategy 4 failed: {e}")
        
        # Strategy 5: Check if this is actually a login page or empty dashboard
        current_url = page.url
        logger.info(f"🌐 Current URL: {current_url}")
        
        if 'login' in current_url.lower():
            raise Exception("Still on login page - please ensure you've logged in successfully before confirming")
        
        # If all strategies fail, provide a helpful error with debugging info
        page_title = await page.title()
        logger.error(f"❌ All extraction strategies failed. Page title: {page_title}")
        
        # Give user extended time to manually inspect the page
        logger.info("⏳ Keeping browser open for 60 seconds for manual inspection...")
        logger.info("🔍 Please check what's displayed on the page and verify you're logged in correctly.")
        await asyncio.sleep(60)
        
        raise Exception(f"Could not locate any patient data on dashboard. Page title: '{page_title}'. Please check the MediMind portal structure.")

    async def _extract_single_patient(self, page: Page, patient_identifier: str) -> List[Dict[str, Any]]:
        """Extract data for a specific patient by ID"""
        # Use search functionality if available
        search_input = await page.query_selector('input[data-testid="search-input"]')
        if search_input:
            await search_input.fill(patient_identifier)
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(2000)  # Wait for search results

        # Try to find the specific patient
        all_patients = await self._extract_all_patients(page)
        return [p for p in all_patients if patient_identifier.lower() in str(p).lower()]

    async def _extract_from_patient_rows(self, page: Page, patient_rows) -> List[Dict[str, Any]]:
        """Extract from data-testid patient rows"""
        patients_data = []
        logger.info(f"Found {len(patient_rows)} patients on dashboard")
        
        for i, row in enumerate(patient_rows):
            try:
                # Extract basic patient info from row
                patient_id = await row.query_selector('td:nth-child(1)')
                first_name = await row.query_selector('td:nth-child(2)')
                last_name = await row.query_selector('td:nth-child(3)')
                
                patient_id_text = await patient_id.text_content() if patient_id else "Unknown"
                first_name_text = await first_name.text_content() if first_name else ""
                last_name_text = await last_name.text_content() if last_name else ""
                
                # Find and click the "View Profile" link
                view_profile_link = await row.query_selector('a[href^="/patients/"][href$="/summary"]')
                if view_profile_link:
                    # Extract detailed patient data
                    patient_data = await self._extract_patient_details(page, view_profile_link, 
                                                                     patient_id_text, first_name_text, last_name_text)
                    patients_data.append(patient_data)
                    
                    # Navigate back to dashboard for next patient
                    await page.goto(self.dashboard_url, wait_until='networkidle')
                    await page.wait_for_selector('[data-testid^="patient-row-"]', timeout=self.element_timeout)
                    
                    # Re-query patient rows as page was reloaded
                    patient_rows = await page.query_selector_all('[data-testid^="patient-row-"]')
                
            except Exception as e:
                logger.error(f"Error extracting patient {i+1}: {str(e)}")
                continue
                
        return patients_data

    async def _extract_from_table(self, page: Page, table) -> List[Dict[str, Any]]:
        """Extract patient data from a table element"""
        patients_data = []
        
        try:
            rows = await table.query_selector_all('tr')
            if len(rows) < 2:  # Need header + at least one data row
                return []
            
            # Skip header row, process data rows
            for i, row in enumerate(rows[1:], 1):
                try:
                    cells = await row.query_selector_all('td, th')
                    if len(cells) < 2:  # Need at least some data
                        continue
                    
                    # Extract text from cells
                    cell_texts = []
                    for cell in cells:
                        text = await cell.text_content()
                        cell_texts.append(text.strip() if text else "")
                    
                    # Look for patient links in this row
                    patient_link = await row.query_selector('a[href*="patient"], a[href*="summary"]')
                    
                    # Create patient data
                    patient_data = {
                        "patient_id": cell_texts[0] if len(cell_texts) > 0 else f"Patient_{i}",
                        "first_name": cell_texts[1] if len(cell_texts) > 1 else "",
                        "last_name": cell_texts[2] if len(cell_texts) > 2 else "",
                        "demographics": {
                            "row_data": cell_texts,
                            "extraction_method": "table"
                        },
                        "profile_link": await patient_link.get_attribute('href') if patient_link else None
                    }
                    
                    patients_data.append(patient_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing table row {i}: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(patients_data)} patients from table")
            return patients_data
            
        except Exception as e:
            logger.warning(f"Error extracting from table: {e}")
            return []

    async def _extract_from_patient_links(self, page: Page, patient_links) -> List[Dict[str, Any]]:
        """Extract patient data from patient links"""
        patients_data = []
        
        try:
            for i, link in enumerate(patient_links[:10]):  # Limit to first 10 to avoid timeout
                try:
                    link_text = await link.text_content()
                    link_href = await link.get_attribute('href')
                    
                    # Try to extract patient info from link text or surrounding context
                    patient_data = {
                        "patient_id": f"Patient_{i+1}",
                        "link_text": link_text.strip() if link_text else "",
                        "profile_link": link_href,
                        "demographics": {
                            "extraction_method": "link",
                            "link_context": link_text
                        }
                    }
                    
                    # Try to get more context from parent element
                    parent = await link.query_selector('xpath=..')
                    if parent:
                        parent_text = await parent.text_content()
                        patient_data["parent_context"] = parent_text.strip() if parent_text else ""
                    
                    patients_data.append(patient_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing patient link {i}: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(patients_data)} patients from links")
            return patients_data
            
        except Exception as e:
            logger.warning(f"Error extracting from patient links: {e}")
            return []

    async def _extract_from_patient_cards(self, page: Page, cards) -> List[Dict[str, Any]]:
        """Extract patient data from card elements"""
        patients_data = []
        
        try:
            for i, card in enumerate(cards[:10]):  # Limit to first 10
                try:
                    card_text = await card.text_content()
                    
                    # Look for patient links within card
                    patient_link = await card.query_selector('a[href*="patient"], a[href*="summary"]')
                    
                    patient_data = {
                        "patient_id": f"Patient_{i+1}",
                        "card_content": card_text.strip() if card_text else "",
                        "demographics": {
                            "extraction_method": "card",
                            "card_text": card_text
                        },
                        "profile_link": await patient_link.get_attribute('href') if patient_link else None
                    }
                    
                    patients_data.append(patient_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing patient card {i}: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(patients_data)} patients from cards")
            return patients_data
            
        except Exception as e:
            logger.warning(f"Error extracting from patient cards: {e}")
            return []

    async def _extract_patient_details(self, page: Page, profile_link, patient_id: str, 
                                     first_name: str, last_name: str) -> Dict[str, Any]:
        """Extract detailed patient information from patient detail page"""
        # Click the profile link
        await profile_link.click()
        await page.wait_for_load_state('networkidle')
        
        # Wait for patient summary component
        await page.wait_for_selector('[data-testid="patient-summary-component"]', timeout=self.element_timeout)
        
        logger.info(f"Extracting details for patient: {first_name} {last_name} (ID: {patient_id})")
        
        # Extract demographics
        demographics = await self._extract_demographics(page)
        
        # Extract medications
        medications = await self._extract_medications(page)
        
        # Extract lab results
        lab_results = await self._extract_lab_results(page)
        
        # Extract allergies
        allergies = await self._extract_allergies(page)
        
        # Extract medical history/problems
        medical_history = await self._extract_medical_history(page)
        
        # Extract appointments
        appointments = await self._extract_appointments(page)
        
        return {
            "patient_id": patient_id.strip(),
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "full_name": f"{first_name.strip()} {last_name.strip()}",
            "demographics": demographics,
            "medications": medications,
            "lab_results": lab_results,
            "allergies": allergies,
            "medical_history": medical_history,
            "appointments": appointments,
            "extraction_timestamp": datetime.now().isoformat()
        }

    async def _extract_demographics(self, page: Page) -> Dict[str, str]:
        """Extract patient demographics"""
        demographics = {}
        
        try:
            # Extract name
            name_element = await page.query_selector('[data-testid="summary-name"]')
            demographics["name"] = await name_element.text_content() if name_element else ""
            
            # Extract DOB
            dob_element = await page.query_selector('[data-testid="summary-dob"]')
            demographics["date_of_birth"] = await dob_element.text_content() if dob_element else ""
            
            # Extract gender
            gender_element = await page.query_selector('[data-testid="summary-gender"]')
            demographics["gender"] = await gender_element.text_content() if gender_element else ""
            
            # Extract MRN from header
            mrn_element = await page.query_selector('[data-testid="patient-name-header"]')
            demographics["mrn"] = await mrn_element.text_content() if mrn_element else ""
            
            # Extract address
            address_element = await page.query_selector('[data-testid="summary-address"]')
            demographics["address"] = await address_element.text_content() if address_element else ""
            
            # Extract phone
            phone_element = await page.query_selector('[data-testid="summary-phone"]')
            demographics["phone"] = await phone_element.text_content() if phone_element else ""
            
            # Extract email
            email_element = await page.query_selector('[data-testid="summary-email"]')
            demographics["email"] = await email_element.text_content() if email_element else ""
            
        except Exception as e:
            logger.error(f"Error extracting demographics: {str(e)}")
            
        return demographics

    async def _extract_medications(self, page: Page) -> List[Dict[str, str]]:
        """Extract patient medications"""
        medications = []
        
        try:
            # Check if medications section exists
            medications_section = await page.query_selector('[data-testid="medications-list-component"]')
            if not medications_section:
                return medications
            
            # Get all medication rows
            medication_rows = await page.query_selector_all('[data-testid^="medication-row-"]')
            
            for row in medication_rows:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 6:
                        medication = {
                            "name": await cells[0].text_content() or "",
                            "dosage": await cells[1].text_content() or "",
                            "frequency": await cells[4].text_content() or "",
                            "start_date": await cells[5].text_content() or ""
                        }
                        medications.append(medication)
                except Exception as e:
                    logger.error(f"Error extracting medication row: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting medications: {str(e)}")
            
        return medications

    async def _extract_lab_results(self, page: Page) -> List[Dict[str, str]]:
        """Extract patient lab results"""
        lab_results = []
        
        try:
            # Check if lab results section exists
            lab_section = await page.query_selector('[data-testid="lab-results-component"]')
            if not lab_section:
                return lab_results
            
            # Get all lab result rows
            lab_rows = await page.query_selector_all('[data-testid^="lab-result-row-"]')
            
            for row in lab_rows:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 6:
                        lab_result = {
                            "test_name": await cells[0].text_content() or "",
                            "result": await cells[1].text_content() or "",
                            "reference_range": await cells[4].text_content() or "",
                            "date": await cells[5].text_content() or ""
                        }
                        lab_results.append(lab_result)
                except Exception as e:
                    logger.error(f"Error extracting lab result row: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting lab results: {str(e)}")
            
        return lab_results

    async def _extract_allergies(self, page: Page) -> List[Dict[str, str]]:
        """Extract patient allergies"""
        allergies = []
        
        try:
            # Check if allergies section exists
            allergies_section = await page.query_selector('[data-testid="allergies-list-component"]')
            if not allergies_section:
                return allergies
            
            # Get all allergy rows
            allergy_rows = await page.query_selector_all('[data-testid^="allergy-row-"]')
            
            for row in allergy_rows:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 3:
                        allergy = {
                            "allergen": await cells[0].text_content() or "",
                            "reaction": await cells[1].text_content() or "",
                            "severity": await cells[2].text_content() or ""
                        }
                        allergies.append(allergy)
                except Exception as e:
                    logger.error(f"Error extracting allergy row: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting allergies: {str(e)}")
            
        return allergies

    async def _extract_medical_history(self, page: Page) -> List[Dict[str, str]]:
        """Extract patient medical history/problems"""
        medical_history = []
        
        try:
            # Check if problems section exists
            problems_section = await page.query_selector('[data-testid="problems-list-component"]')
            if not problems_section:
                return medical_history
            
            # Get all problem rows
            problem_rows = await page.query_selector_all('[data-testid^="problem-row-"]')
            
            for row in problem_rows:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 5:
                        problem = {
                            "condition": await cells[0].text_content() or "",
                            "status": await cells[2].text_content() or "",
                            "date": await cells[4].text_content() or ""
                        }
                        medical_history.append(problem)
                except Exception as e:
                    logger.error(f"Error extracting problem row: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting medical history: {str(e)}")
            
        return medical_history

    async def _extract_appointments(self, page: Page) -> List[Dict[str, str]]:
        """Extract patient appointments"""
        appointments = []
        
        try:
            # Check if appointments section exists
            appointments_section = await page.query_selector('[data-testid="appointments-list-component"]')
            if not appointments_section:
                return appointments
            
            # Get all appointment rows
            appointment_rows = await page.query_selector_all('[data-testid^="appointment-row-"]')
            
            for row in appointment_rows:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 6:
                        appointment = {
                            "date_time": await cells[0].text_content() or "",
                            "type": await cells[3].text_content() or "",
                            "provider": await cells[5].text_content() or ""
                        }
                        appointments.append(appointment)
                except Exception as e:
                    logger.error(f"Error extracting appointment row: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting appointments: {str(e)}")
            
        return appointments

    def get_adapter_info(self) -> Dict[str, str]:
        """Return adapter information"""
        return {
            "name": self.name,
            "description": "Comprehensive adapter for MediMind portal. Extracts demographics, medications, lab results, allergies, medical history, and appointments.",
            "supported_modes": ["ALL_PATIENTS", "SINGLE_PATIENT"],
            "portal_url": self.base_url,
            "features": [
                "Patient demographics extraction",
                "Medications with dosage and frequency",
                "Lab results with reference ranges",
                "Allergies with severity levels",
                "Medical history/problems",
                "Appointments with providers",
                "Search functionality",
                "Comprehensive error handling"
            ]
        }

# Main execution function for testing
async def main():
    """Test function for the MediMind adapter"""
    adapter = MediMindAdapter()
    
    # Test credentials (replace with actual credentials)
    test_credentials = {
        "username": "testuser",
        "password": "testpass"
    }
    
    # Test extraction
    result = await adapter.extract_patient_data(
        target_url="http://localhost:3004/login",
        credentials=test_credentials,
        extraction_mode="ALL_PATIENTS"
    )
    
    print(f"Extraction completed. Status: {result['status']}")
    print(f"Total patients extracted: {result.get('total_patients', 0)}")
    
    return result

# Wrapper functions for orchestrator compatibility
async def extract_single_patient_data(page, patient_identifier: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Wrapper function for single patient extraction - compatible with orchestrator
    
    Args:
        page: Playwright page object (already authenticated by user)
        patient_identifier: Patient ID/MRN for extraction
        config: Optional configuration dictionary
        
    Returns:
        Dictionary containing patient data
    """
    try:
        logger.info(f"MediMind: Starting single patient extraction for: {patient_identifier}")
        
        # Wait for page to be ready after manual login
        await page.wait_for_load_state('networkidle')
        
        # Check if we're on dashboard, if not navigate there
        current_url = page.url
        if '/dashboard' not in current_url:
            logger.info("MediMind: Navigating to dashboard...")
            await page.goto('http://localhost:3004/dashboard')
            await page.wait_for_load_state('networkidle')
        
        # Wait for patient data to be available using verified selectors
        try:
            await page.wait_for_selector('[data-testid^="patient-row-"]', timeout=10000)
            logger.info("MediMind: Found patient rows")
        except Exception as e:
            logger.error(f"MediMind: Could not find patient rows: {str(e)}")
            await page.screenshot(path='medimind_debug_single_patient_failed.png')
            raise Exception("Could not locate patient data on dashboard")
        
        # Search for specific patient if search is available
        search_input = await page.query_selector('input[data-testid="search-input"]')
        if search_input:
            logger.info(f"MediMind: Searching for patient: {patient_identifier}")
            await search_input.fill(patient_identifier)
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(2000)  # Wait for search results
        
        # Find the specific patient row using verified table structure
        patient_rows = await page.query_selector_all('[data-testid^="patient-row-"]')
        target_patient_row = None
        
        for row in patient_rows:
            cells = await row.query_selector_all('td')
            if len(cells) >= 1:
                patient_id_cell = cells[0]  # First column is ID
                patient_id_text = await patient_id_cell.text_content()
                if patient_id_text and patient_identifier in patient_id_text.strip():
                    target_patient_row = row
                    break
        
        if not target_patient_row:
            raise Exception(f"Patient with identifier {patient_identifier} not found")
        
        # Extract basic info and click profile link
        cells = await target_patient_row.query_selector_all('td')
        patient_id = await cells[0].text_content() if cells[0] else patient_identifier
        first_name = await cells[1].text_content() if len(cells) > 1 else ""
        last_name = await cells[2].text_content() if len(cells) > 2 else ""
        date_of_birth = await cells[3].text_content() if len(cells) > 3 else ""
        gender = await cells[4].text_content() if len(cells) > 4 else ""
        
        # Click the "View Profile" link
        view_profile_link = await target_patient_row.query_selector('a[href*="/patients/"][href*="/summary"]')
        if not view_profile_link:
            raise Exception("Could not find patient detail link")
        
        await view_profile_link.click()
        await page.wait_for_load_state('networkidle')
        
        # Extract detailed patient data
        patient_data = await extract_patient_details_medimind_fixed(page, patient_identifier, {
            'patient_id': patient_id.strip(),
            'first_name': first_name.strip(),
            'last_name': last_name.strip(),
            'date_of_birth': date_of_birth.strip(),
            'gender': gender.strip()
        })
        
        logger.info(f"MediMind: Successfully extracted data for patient: {patient_identifier}")
        return patient_data
            
    except Exception as e:
        logger.error(f"MediMind: Failed to extract data for patient {patient_identifier}: {str(e)}")
        raise Exception(f"MediMind single patient extraction failed: {str(e)}")

async def extract_all_patients_data(page, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Wrapper function for all patients extraction - compatible with orchestrator
    
    Args:
        page: Playwright page object (already authenticated by user)
        config: Optional configuration dictionary
        
    Returns:
        List of dictionaries containing patient data
    """
    try:
        logger.info("MediMind: Starting all patients extraction")
        
        # Wait for page to be ready after manual login
        await page.wait_for_load_state('networkidle')
        
        # Check if we're on dashboard, if not navigate there
        current_url = page.url
        if '/dashboard' not in current_url:
            logger.info("MediMind: Navigating to dashboard...")
            await page.goto('http://localhost:3004/dashboard')
            await page.wait_for_load_state('networkidle')
        
        # Wait for patient data to be available - verified selectors from debugging
        try:
            await page.wait_for_selector('[data-testid^="patient-row-"]', timeout=10000)
            logger.info("MediMind: Found patient rows")
        except Exception as e:
            logger.error(f"MediMind: Could not find patient rows: {str(e)}")
            # Take screenshot for debugging
            await page.screenshot(path='medimind_debug_all_patients_failed.png')
            raise Exception("Could not locate patient data on dashboard")
        
        # Get all patient rows - verified working selector
        patient_rows = await page.query_selector_all('[data-testid^="patient-row-"]')
        total_patients = len(patient_rows)
        logger.info(f"MediMind: Found {total_patients} patients to process")
        
        all_patients_data = []
        
        # Process each patient using a simple index-based approach
        for patient_index in range(total_patients):
            try:
                logger.info(f"🔄 MediMind: Processing patient {patient_index + 1}/{total_patients}")
                
                # Navigate back to dashboard and re-query rows to ensure fresh state
                await page.goto('http://localhost:3004/dashboard')
                await page.wait_for_load_state('networkidle')
                await page.wait_for_selector('[data-testid^="patient-row-"]', timeout=5000)
                
                # Re-query patient rows
                current_patient_rows = await page.query_selector_all('[data-testid^="patient-row-"]')
                
                if patient_index >= len(current_patient_rows):
                    logger.warning(f"MediMind: Patient index {patient_index} out of range, skipping")
                    continue
                
                current_row = current_patient_rows[patient_index]
                
                # Extract basic patient info from this specific row
                cells = await current_row.query_selector_all('td')
                
                if len(cells) < 6:
                    logger.warning(f"MediMind: Row {patient_index + 1} has {len(cells)} cells, expected 6")
                    continue
                
                # Extract data from each cell
                patient_id = await cells[0].text_content() if cells[0] else "Unknown"
                first_name = await cells[1].text_content() if cells[1] else ""
                last_name = await cells[2].text_content() if cells[2] else ""
                date_of_birth = await cells[3].text_content() if cells[3] else ""
                gender = await cells[4].text_content() if cells[4] else ""
                
                logger.info(f"MediMind: Processing patient {patient_index + 1}: {first_name} {last_name} (ID: {patient_id})")
                
                # Check if we've already processed this patient (avoid duplicates)
                already_processed = any(p['patient_identifier'] == patient_id.strip() for p in all_patients_data)
                if already_processed:
                    logger.info(f"⏭️ MediMind: Patient {patient_id} already processed, skipping")
                    continue
                
                # Find and click the "View Profile" link
                view_profile_link = await current_row.query_selector('a[href*="/patients/"][href*="/summary"]')
                if view_profile_link:
                    # Navigate to patient detail page
                    await view_profile_link.click()
                    await page.wait_for_load_state('networkidle')
                    
                    # Extract detailed patient data from all tabs
                    patient_data = await extract_patient_details_medimind_fixed(page, patient_id.strip(), {
                        'patient_id': patient_id.strip(),
                        'first_name': first_name.strip(),
                        'last_name': last_name.strip(),
                        'date_of_birth': date_of_birth.strip(),
                        'gender': gender.strip()
                    })
                    all_patients_data.append(patient_data)
                    
                    logger.info(f"✅ MediMind: Completed patient {patient_index + 1}: {first_name} {last_name}")
                    
                else:
                    logger.warning(f"MediMind: No profile link found for patient {patient_index + 1}")
                    # Still add basic data even without detail page
                    patient_data = {
                        'patient_identifier': patient_id.strip(),
                        'demographics': {
                            'patient_id': patient_id.strip(),
                            'first_name': first_name.strip(),
                            'last_name': last_name.strip(),
                            'date_of_birth': date_of_birth.strip(),
                            'gender': gender.strip()
                        },
                        'medications': [],
                        'lab_results': [],
                        'allergies': [],
                        'problems': [],
                        'immunizations': [],
                        'procedures': [],
                        'imaging_reports': [],
                        'visit_notes': [],
                        'appointments': [],
                        'extraction_timestamp': datetime.now().isoformat(),
                        'extraction_note': 'Basic data only - no detail page access'
                    }
                    all_patients_data.append(patient_data)
                
            except Exception as e:
                logger.error(f"MediMind: Error extracting patient {patient_index + 1}: {str(e)}")
                continue
        
        logger.info(f"MediMind: Successfully extracted data for {len(all_patients_data)} patients")
        return all_patients_data
        
    except Exception as e:
        logger.error(f"MediMind: Failed to extract all patients data: {str(e)}")
        raise Exception(f"MediMind all patients extraction failed: {str(e)}")

async def extract_patient_details_medimind_fixed(page, patient_id: str, basic_info: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract detailed patient information using corrected selectors and navigation tabs
    """
    try:
        # Wait for patient summary component - verified to exist
        await page.wait_for_selector('[data-testid="patient-summary-component"]', timeout=10000)
        
        # Take screenshot for debugging
        await page.screenshot(path=f'patient_detail_{patient_id}.png')
        
        logger.info(f"🔍 MediMind: Starting comprehensive extraction for patient {patient_id}")
        
        # Extract demographics from summary page (already on this tab)
        demographics = basic_info.copy()  # Start with dashboard data
        
        try:
            # Get all summary elements and extract their data
            summary_elements = await page.query_selector_all('[data-testid^="summary-"]')
            logger.info(f"MediMind: Found {len(summary_elements)} summary elements")
            
            for element in summary_elements:
                try:
                    testid = await element.get_attribute('data-testid')
                    text_content = await element.text_content()
                    if testid and text_content:
                        # Clean the text content to get just the value
                        if ':' in text_content:
                            field_value = text_content.split(':', 1)[1].strip()
                        else:
                            field_value = text_content.strip()
                        
                        # Map testid to field names
                        field_map = {
                            'summary-name': 'full_name',
                            'summary-dob': 'date_of_birth',
                            'summary-gender': 'gender',
                            'summary-address': 'address',
                            'summary-phone': 'phone',
                            'summary-email': 'email',
                            'summary-emergency-contact': 'emergency_contact'
                        }
                        
                        field_name = field_map.get(testid)
                        if field_name:
                            demographics[field_name] = field_value
                            logger.info(f"MediMind: Extracted {field_name}: {field_value}")
                
                except Exception as e:
                    logger.warning(f"MediMind: Error extracting summary element: {e}")
                    
        except Exception as e:
            logger.warning(f"MediMind: Error extracting demographics: {str(e)}")
        
        # Now navigate through ALL medical data tabs
        medical_sections = {
            'medications': '/medications',
            'lab_results': '/labs', 
            'problems': '/problems',
            'allergies': '/allergies',
            'immunizations': '/immunizations',
            'procedures': '/procedures',
            'imaging_reports': '/imaging_reports',
            'visit_notes': '/visit_notes',
            'appointments': '/appointments'
        }
        
        extracted_data = {
            'medications': [],
            'lab_results': [],
            'problems': [],
            'allergies': [],
            'immunizations': [],
            'procedures': [],
            'imaging_reports': [],
            'visit_notes': [],
            'appointments': []
        }
        
        base_patient_url = f"http://localhost:3004/patients/{patient_id}"
        
        for section_name, url_suffix in medical_sections.items():
            try:
                logger.info(f"🔍 MediMind: Extracting {section_name} for patient {patient_id}")
                
                # Navigate to the specific section
                section_url = base_patient_url + url_suffix
                await page.goto(section_url)
                await page.wait_for_load_state('networkidle')
                
                # Wait for content to load
                await asyncio.sleep(1)
                
                # Take screenshot for debugging
                await page.screenshot(path=f'patient_{patient_id}_{section_name}.png')
                
                # Extract data from this section
                section_data = await extract_section_data(page, section_name)
                extracted_data[section_name] = section_data
                
                logger.info(f"✅ MediMind: Extracted {len(section_data)} {section_name} records")
                
            except Exception as e:
                logger.error(f"❌ MediMind: Error extracting {section_name}: {str(e)}")
                extracted_data[section_name] = []
        
        return {
            "patient_identifier": patient_id,
            "demographics": demographics,
            "medications": extracted_data['medications'],
            "lab_results": extracted_data['lab_results'],
            "problems": extracted_data['problems'],
            "allergies": extracted_data['allergies'],
            "immunizations": extracted_data['immunizations'],
            "procedures": extracted_data['procedures'],
            "imaging_reports": extracted_data['imaging_reports'],
            "visit_notes": extracted_data['visit_notes'],
            "appointments": extracted_data['appointments'],
            "extraction_timestamp": datetime.now().isoformat(),
            "portal_version": "comprehensive_all_sections"
        }
        
    except Exception as e:
        logger.error(f"MediMind: Error extracting patient details: {str(e)}")
        raise

async def extract_section_data(page, section_name: str) -> List[Dict[str, Any]]:
    """
    Extract data from a specific medical section (medications, labs, etc.)
    """
    section_data = []
    
    try:
        # Wait for content to load
        await page.wait_for_timeout(1000)
        
        # Get page content for analysis
        page_text = await page.text_content('body')
        
        # Look for tables first
        tables = await page.query_selector_all('table')
        
        if tables:
            logger.info(f"🔍 Found {len(tables)} tables in {section_name} section")
            
            for table_index, table in enumerate(tables):
                try:
                    # Get table headers
                    headers = await table.query_selector_all('th')
                    header_texts = []
                    for header in headers:
                        header_text = await header.text_content()
                        header_texts.append(header_text.strip() if header_text else "")
                    
                    # Get table rows (skip header)
                    rows = await table.query_selector_all('tbody tr')
                    if not rows:  # Fallback to all rows
                        all_rows = await table.query_selector_all('tr')
                        rows = all_rows[1:] if len(all_rows) > 1 else []
                    
                    logger.info(f"📊 Table {table_index + 1} in {section_name}: {len(header_texts)} headers, {len(rows)} data rows")
                    logger.info(f"📋 Headers: {header_texts}")
                    
                    for row_index, row in enumerate(rows):
                        try:
                            cells = await row.query_selector_all('td')
                            cell_data = []
                            
                            for cell in cells:
                                cell_text = await cell.text_content()
                                cell_data.append(cell_text.strip() if cell_text else "")
                            
                            if cell_data and any(cell_data):  # Only add if row has data
                                row_dict = {"row_index": row_index + 1}
                                
                                # Map cell data to headers
                                for i, cell_value in enumerate(cell_data):
                                    if i < len(header_texts):
                                        header_key = header_texts[i].lower().replace(' ', '_').replace('/', '_')
                                        row_dict[header_key] = cell_value
                                    else:
                                        row_dict[f"column_{i+1}"] = cell_value
                                
                                section_data.append(row_dict)
                                logger.info(f"   Row {row_index + 1}: {row_dict}")
                                
                        except Exception as e:
                            logger.warning(f"Error processing row {row_index + 1}: {e}")
                            
                except Exception as e:
                    logger.warning(f"Error processing table {table_index + 1}: {e}")
        
        # If no tables found, look for list items or other content patterns
        elif 'no data' not in page_text.lower() and 'empty' not in page_text.lower():
            # Look for alternative data structures
            list_items = await page.query_selector_all('li')
            cards = await page.query_selector_all('.card, .item, [data-testid*="item"]')
            rows = await page.query_selector_all('[data-testid*="row"]')
            
            if list_items and len(list_items) > 3:  # More than just navigation
                logger.info(f"🔍 Found {len(list_items)} list items in {section_name}")
                for i, item in enumerate(list_items[:10]):  # Limit to first 10
                    try:
                        item_text = await item.text_content()
                        if item_text and len(item_text.strip()) > 10:
                            section_data.append({
                                "type": "list_item",
                                "content": item_text.strip(),
                                "index": i + 1
                            })
                    except:
                        pass
            
            if cards:
                logger.info(f"🔍 Found {len(cards)} cards in {section_name}")
                for i, card in enumerate(cards[:10]):
                    try:
                        card_text = await card.text_content()
                        if card_text and len(card_text.strip()) > 10:
                            section_data.append({
                                "type": "card",
                                "content": card_text.strip(),
                                "index": i + 1
                            })
                    except:
                        pass
        
        # If still no data, record the page content for analysis
        if not section_data:
            logger.info(f"📝 No structured data found in {section_name}, recording page content")
            if len(page_text.strip()) > 50:  # Has meaningful content
                section_data.append({
                    "type": "raw_content",
                    "content": page_text.strip()[:500],  # First 500 chars
                    "note": "No structured data found, raw page content recorded"
                })
        
    except Exception as e:
        logger.error(f"Error extracting {section_name} data: {e}")
    
    return section_data

if __name__ == "__main__":
    # Run the test
    asyncio.run(main()) 
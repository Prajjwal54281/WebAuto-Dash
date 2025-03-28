"""
Universal Portal Inspector for WebAutoDash
This advanced tool can inspect any medical portal and automatically generate adapter code.
"""

import asyncio
import logging
from playwright.async_api import async_playwright
import json
import re
from datetime import datetime
import os
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Tuple
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portal_inspection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UniversalPortalInspector:
    def __init__(self):
        self.screenshots_dir = "portal_screenshots"
        self.html_dir = "portal_html"
        self.analysis_results = {}
        
        # Create directories
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.html_dir, exist_ok=True)
        
        # Medical data keywords for pattern detection
        self.medical_keywords = {
            'medications': ['medication', 'medications', 'drug', 'drugs', 'prescription', 'prescriptions', 'meds', 'rx'],
            'allergies': ['allergy', 'allergies', 'allergic', 'reaction', 'reactions', 'sensitivity'],
            'lab_results': ['lab', 'laboratory', 'test', 'tests', 'result', 'results', 'blood', 'urine', 'culture'],
            'problems': ['problem', 'problems', 'diagnosis', 'diagnoses', 'condition', 'conditions', 'issue', 'issues'],
            'appointments': ['appointment', 'appointments', 'visit', 'visits', 'schedule', 'scheduled'],
            'procedures': ['procedure', 'procedures', 'surgery', 'surgeries', 'operation', 'operations'],
            'immunizations': ['immunization', 'immunizations', 'vaccine', 'vaccines', 'vaccination', 'vaccinations', 'shot', 'shots'],
            'imaging': ['imaging', 'xray', 'x-ray', 'ct', 'mri', 'ultrasound', 'scan', 'scans'],
            'vitals': ['vital', 'vitals', 'blood pressure', 'heart rate', 'temperature', 'weight', 'height'],
            'notes': ['note', 'notes', 'progress', 'clinical', 'visit notes', 'physician notes']
        }
        
        # Common portal patterns
        self.common_selectors = {
            'patient_rows': [
                '[data-testid^="patient-row"]',
                '[data-testid*="patient"]',
                'tr[data-patient-id]',
                'tr[data-patient]',
                '.patient-row',
                '.patient-card',
                '.patient-item',
                'tbody tr',
                'table tr:not(:first-child)',
                '[class*="patient"]',
                'a[href*="patient"]',
                'a[href*="summary"]',
                '[role="row"]'
            ],
            'medical_sections': [
                '[data-testid*="medication"]',
                '[data-testid*="allerg"]',
                '[data-testid*="lab"]',
                '[data-testid*="problem"]',
                '[data-testid*="appointment"]',
                '[data-testid*="procedure"]',
                '[data-testid*="immuniz"]',
                '[data-testid*="imaging"]',
                '[data-testid*="vital"]',
                '[data-testid*="note"]',
                '.medication', '.medications',
                '.allergy', '.allergies',
                '.lab-result', '.lab-results',
                '.problem', '.problems',
                '.appointment', '.appointments',
                '.procedure', '.procedures',
                '.immunization', '.immunizations',
                '.imaging', '.vitals', '.notes',
                'section', 'div[class*="section"]',
                '.tab-content', '.tab-pane',
                '[id*="medication"]', '[id*="allerg"]', '[id*="lab"]',
                '[id*="problem"]', '[id*="appointment"]'
            ],
            'navigation': [
                'nav', '.nav', '.navbar', '.navigation',
                '.menu', '.sidebar', '.tabs',
                'button[role="tab"]', '[role="tab"]',
                '.tab', '.tab-item', '.nav-item',
                'a[href*="dashboard"]', 'a[href*="patient"]',
                'button', 'a'
            ]
        }

    async def inspect_portal(self, portal_config: Dict) -> Dict:
        """
        Comprehensive portal inspection
        
        Args:
            portal_config: {
                'name': 'Portal Name',
                'url': 'https://portal.example.com',
                'login_url': 'https://portal.example.com/login',
                'username': 'username',
                'password': 'password',
                'login_selectors': {  # Optional custom selectors
                    'username_field': '#username',
                    'password_field': '#password',
                    'submit_button': 'button[type="submit"]'
                }
            }
        """
        logger.info(f"🔍 Starting inspection of {portal_config['name']}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=1000,
                args=['--start-maximized', '--disable-web-security']
            )
            
            page = await browser.new_page()
            
            try:
                # Step 1: Analyze login page
                login_analysis = await self._analyze_login_page(page, portal_config)
                
                # Step 2: Perform login
                login_success = await self._perform_login(page, portal_config)
                if not login_success:
                    logger.error("❌ Login failed - cannot proceed with portal analysis")
                    return {'error': 'Login failed'}
                
                # Step 3: Analyze dashboard/main page
                dashboard_analysis = await self._analyze_dashboard(page, portal_config['name'])
                
                # Step 4: Discover and analyze patient data structure
                patient_analysis = await self._analyze_patient_structure(page, portal_config['name'])
                
                # Step 5: Navigate to patient details and analyze medical data
                medical_data_analysis = await self._analyze_medical_data_structure(page, portal_config['name'])
                
                # Step 6: Analyze navigation patterns
                navigation_analysis = await self._analyze_navigation_patterns(page)
                
                # Step 7: Generate comprehensive analysis report
                analysis_report = {
                    'portal_name': portal_config['name'],
                    'portal_url': portal_config['url'],
                    'timestamp': datetime.now().isoformat(),
                    'login_analysis': login_analysis,
                    'dashboard_analysis': dashboard_analysis,
                    'patient_analysis': patient_analysis,
                    'medical_data_analysis': medical_data_analysis,
                    'navigation_analysis': navigation_analysis,
                    'adapter_recommendations': self._generate_adapter_recommendations(
                        dashboard_analysis, patient_analysis, medical_data_analysis, navigation_analysis
                    )
                }
                
                # Step 8: Generate adapter code
                adapter_code = await self._generate_adapter_code(portal_config['name'], analysis_report)
                
                # Save all results
                await self._save_analysis_results(portal_config['name'], analysis_report, adapter_code)
                
                # Keep browser open for manual inspection
                logger.info("🔍 Keeping browser open for 120 seconds for manual inspection...")
                await asyncio.sleep(120)
                
                return analysis_report
                
            except Exception as e:
                logger.error(f"❌ Portal inspection failed: {e}")
                await page.screenshot(path=f'{self.screenshots_dir}/error_{portal_config["name"]}.png')
                return {'error': str(e)}
                
            finally:
                await browser.close()

    async def _analyze_login_page(self, page, portal_config: Dict) -> Dict:
        """Analyze the login page structure"""
        logger.info("🔐 Analyzing login page...")
        
        await page.goto(portal_config.get('login_url', portal_config['url']))
        await page.wait_for_load_state('networkidle')
        
        # Take screenshot and save HTML
        await page.screenshot(path=f'{self.screenshots_dir}/01_login_{portal_config["name"]}.png')
        html_content = await page.content()
        with open(f'{self.html_dir}/01_login_{portal_config["name"]}.html', 'w') as f:
            f.write(html_content)
        
        # Analyze login form elements
        login_selectors = await self._discover_login_selectors(page)
        
        return {
            'url': page.url,
            'title': await page.title(),
            'login_selectors': login_selectors,
            'form_analysis': await self._analyze_forms(page)
        }

    async def _discover_login_selectors(self, page) -> Dict:
        """Discover login form selectors automatically"""
        selectors = {}
        
        # Common username field patterns
        username_patterns = [
            '#username', '#user', '#email', '#login',
            '[name="username"]', '[name="user"]', '[name="email"]', '[name="login"]',
            '[type="email"]', '[placeholder*="username"]', '[placeholder*="email"]',
            'input[class*="username"]', 'input[class*="email"]'
        ]
        
        # Common password field patterns
        password_patterns = [
            '#password', '#pass', '#pwd',
            '[name="password"]', '[name="pass"]', '[name="pwd"]',
            '[type="password"]', '[placeholder*="password"]',
            'input[class*="password"]'
        ]
        
        # Common submit button patterns
        submit_patterns = [
            'button[type="submit"]', 'input[type="submit"]',
            'button:has-text("login")', 'button:has-text("sign in")',
            '.login-button', '.submit-button', '#login-button',
            'button[class*="login"]', 'button[class*="submit"]'
        ]
        
        # Find username field
        for pattern in username_patterns:
            try:
                element = await page.query_selector(pattern)
                if element:
                    selectors['username_field'] = pattern
                    break
            except:
                continue
        
        # Find password field
        for pattern in password_patterns:
            try:
                element = await page.query_selector(pattern)
                if element:
                    selectors['password_field'] = pattern
                    break
            except:
                continue
        
        # Find submit button
        for pattern in submit_patterns:
            try:
                element = await page.query_selector(pattern)
                if element:
                    selectors['submit_button'] = pattern
                    break
            except:
                continue
        
        return selectors

    async def _perform_login(self, page, portal_config: Dict) -> bool:
        """Perform login using discovered or provided selectors"""
        logger.info("🔑 Performing login...")
        
        try:
            # Use custom selectors if provided, otherwise use discovered ones
            login_selectors = portal_config.get('login_selectors', {})
            if not login_selectors:
                login_selectors = await self._discover_login_selectors(page)
            
            # Fill login form
            username_field = login_selectors.get('username_field')
            password_field = login_selectors.get('password_field')
            submit_button = login_selectors.get('submit_button')
            
            if username_field:
                await page.fill(username_field, portal_config['username'])
            if password_field:
                await page.fill(password_field, portal_config['password'])
            if submit_button:
                await page.click(submit_button)
            
            # Wait for navigation or dashboard
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
                current_url = page.url
                
                # Check if we're still on login page
                if 'login' in current_url.lower():
                    logger.warning("Still on login page - login might have failed")
                    return False
                
                logger.info("✅ Login successful")
                return True
                
            except Exception as e:
                logger.error(f"Login navigation failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Login process failed: {e}")
            return False

    async def _analyze_dashboard(self, page, portal_name: str) -> Dict:
        """Analyze the main dashboard page"""
        logger.info("📊 Analyzing dashboard...")
        
        await page.wait_for_load_state('networkidle')
        
        # Take screenshot and save HTML
        await page.screenshot(path=f'{self.screenshots_dir}/02_dashboard_{portal_name}.png')
        html_content = await page.content()
        with open(f'{self.html_dir}/02_dashboard_{portal_name}.html', 'w') as f:
            f.write(html_content)
        
        # Analyze page structure
        page_analysis = {
            'url': page.url,
            'title': await page.title(),
            'navigation_elements': await self._find_navigation_elements(page),
            'tables_analysis': await self._analyze_tables(page),
            'links_analysis': await self._analyze_links(page),
            'content_sections': await self._analyze_content_sections(page)
        }
        
        return page_analysis

    async def _analyze_patient_structure(self, page, portal_name: str) -> Dict:
        """Analyze patient data structure and discover patient rows"""
        logger.info("👥 Analyzing patient data structure...")
        
        patient_findings = {}
        
        # Test all common patient row selectors
        for selector in self.common_selectors['patient_rows']:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    patient_findings[selector] = {
                        'count': len(elements),
                        'sample_data': await self._extract_sample_patient_data(elements[:3])
                    }
                    logger.info(f"🔍 {selector}: {len(elements)} patient elements")
            except Exception as e:
                patient_findings[selector] = {'error': str(e)}
        
        # Analyze specific table structures for patient data
        table_analysis = await self._analyze_patient_tables(page)
        
        return {
            'selector_findings': patient_findings,
            'table_analysis': table_analysis,
            'recommended_selectors': self._recommend_patient_selectors(patient_findings, table_analysis)
        }

    async def _analyze_medical_data_structure(self, page, portal_name: str) -> Dict:
        """Navigate to patient details and analyze medical data structure"""
        logger.info("🏥 Analyzing medical data structure...")
        
        # Try to find and click on first patient
        patient_clicked = False
        medical_analysis = {}
        
        # Try different ways to access patient details
        patient_access_methods = [
            'a[href*="patient"]',
            'a[href*="summary"]',
            '[data-testid^="patient-row"] a',
            'tbody tr a',
            'table tr a'
        ]
        
        for method in patient_access_methods:
            try:
                links = await page.query_selector_all(method)
                if links:
                    logger.info(f"Trying to access patient via: {method}")
                    await links[0].click()
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    patient_clicked = True
                    break
            except Exception as e:
                logger.warning(f"Failed to access patient via {method}: {e}")
                continue
        
        if patient_clicked:
            # Take screenshot of patient detail page
            await page.screenshot(path=f'{self.screenshots_dir}/03_patient_detail_{portal_name}.png')
            html_content = await page.content()
            with open(f'{self.html_dir}/03_patient_detail_{portal_name}.html', 'w') as f:
                f.write(html_content)
            
            # Analyze medical data sections
            medical_analysis = await self._analyze_medical_sections(page)
            
            # Look for tabs or navigation within patient details
            tabs_analysis = await self._analyze_patient_tabs(page)
            medical_analysis['tabs_analysis'] = tabs_analysis
        
        return medical_analysis

    async def _analyze_medical_sections(self, page) -> Dict:
        """Analyze medical data sections on patient detail page"""
        medical_sections = {}
        
        # Get full page content for keyword analysis
        page_text = await page.text_content('body')
        
        # Analyze each medical data type
        for section_type, keywords in self.medical_keywords.items():
            section_analysis = {
                'keywords_found': [kw for kw in keywords if kw.lower() in page_text.lower()],
                'selectors': {},
                'content_preview': []
            }
            
            # Test selectors for this section type
            for selector in self.common_selectors['medical_sections']:
                if any(keyword in selector.lower() for keyword in keywords):
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            section_analysis['selectors'][selector] = len(elements)
                            
                            # Get sample content
                            for i, element in enumerate(elements[:3]):
                                try:
                                    text = await element.text_content()
                                    if text and len(text.strip()) > 5:
                                        section_analysis['content_preview'].append(text.strip()[:100])
                                except:
                                    continue
                    except:
                        continue
            
            medical_sections[section_type] = section_analysis
        
        return medical_sections

    async def _analyze_navigation_patterns(self, page) -> Dict:
        """Analyze navigation patterns and portal flow"""
        logger.info("🧭 Analyzing navigation patterns...")
        
        navigation_analysis = {}
        
        # Find all navigation elements
        nav_elements = []
        for selector in self.common_selectors['navigation']:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        text = await element.text_content()
                        href = await element.get_attribute('href')
                        tag = await element.evaluate('el => el.tagName')
                        classes = await element.get_attribute('class')
                        
                        nav_elements.append({
                            'text': text.strip() if text else '',
                            'href': href,
                            'tag': tag.lower(),
                            'classes': classes,
                            'selector': selector
                        })
                    except:
                        continue
            except:
                continue
        
        navigation_analysis['elements'] = nav_elements
        navigation_analysis['patterns'] = self._identify_navigation_patterns(nav_elements)
        
        return navigation_analysis

    def _generate_adapter_recommendations(self, dashboard_analysis, patient_analysis, medical_data_analysis, navigation_analysis) -> List[str]:
        """Generate recommendations for adapter development"""
        recommendations = []
        
        # Patient row recommendations
        patient_selectors = patient_analysis.get('recommended_selectors', [])
        if patient_selectors:
            recommendations.append(f"✅ Use patient selector: {patient_selectors[0]}")
        else:
            recommendations.append("❌ No reliable patient selector found - manual investigation needed")
        
        # Medical data recommendations
        for section, analysis in medical_data_analysis.items():
            if section == 'tabs_analysis':
                continue
            
            working_selectors = [sel for sel, count in analysis.get('selectors', {}).items() if count > 0]
            if working_selectors:
                recommendations.append(f"✅ {section}: Use {working_selectors[0]}")
            else:
                recommendations.append(f"❌ {section}: No selectors found - check tabs or alternative navigation")
        
        # Navigation recommendations
        nav_patterns = navigation_analysis.get('patterns', {})
        if nav_patterns.get('has_tabs'):
            recommendations.append("💡 Portal uses tabs - implement tab navigation in adapter")
        
        return recommendations

    async def _generate_adapter_code(self, portal_name: str, analysis_report: Dict) -> str:
        """Generate complete adapter code based on analysis"""
        logger.info("🔧 Generating adapter code...")
        
        # Extract key information
        patient_selectors = analysis_report['patient_analysis'].get('recommended_selectors', [])
        medical_analysis = analysis_report['medical_data_analysis']
        
        # Create adapter template
        adapter_code = f'''"""
{portal_name} Portal Adapter for WebAutoDash
Auto-generated based on portal analysis
"""

import logging
from typing import List, Dict, Optional
from .base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

class {portal_name.replace(' ', '').replace('-', '')}Adapter(BaseAdapter):
    def __init__(self):
        super().__init__()
        self.portal_name = "{portal_name}"
        
        # Selectors discovered during analysis
        self.selectors = {{
            'patient_rows': {patient_selectors[:3] if patient_selectors else ["'tbody tr'"]},
            'medical_sections': {{'''
        
        # Add medical section selectors
        for section, analysis in medical_analysis.items():
            if section == 'tabs_analysis':
                continue
            working_selectors = [sel for sel, count in analysis.get('selectors', {}).items() if count > 0]
            if working_selectors:
                adapter_code += f'''
                '{section}': {working_selectors[:2]},'''
        
        adapter_code += f'''
            }}
        }}
    
    async def login(self, page, username: str, password: str) -> bool:
        """Perform login to {portal_name}"""
        try:
            await page.goto(self.base_url + "/login")
            
            # Auto-discovered login selectors
            await page.fill('{analysis_report.get("login_analysis", {}).get("login_selectors", {}).get("username_field", "#username")}', username)
            await page.fill('{analysis_report.get("login_analysis", {}).get("login_selectors", {}).get("password_field", "#password")}', password)
            await page.click('{analysis_report.get("login_analysis", {}).get("login_selectors", {}).get("submit_button", "button[type=submit]")}')
            
            await page.wait_for_load_state('networkidle')
            return not 'login' in page.url.lower()
            
        except Exception as e:
            logger.error(f"Login failed: {{e}}")
            return False
    
    async def get_patient_list(self, page) -> List[Dict]:
        """Extract patient list from dashboard"""
        patients = []
        
        # Try discovered patient selectors
        for selector in self.selectors['patient_rows']:
            try:
                patient_elements = await page.query_selector_all(selector)
                if patient_elements:
                    for i, element in enumerate(patient_elements):
                        # Extract patient info based on analysis
                        patient_data = await self._extract_patient_info(element, i)
                        if patient_data:
                            patients.append(patient_data)
                    break
            except Exception as e:
                logger.warning(f"Selector {{selector}} failed: {{e}}")
                continue
        
        return patients
    
    async def extract_patient_data(self, page, patient_info: Dict) -> Dict:
        """Extract comprehensive patient data"""
        try:
            # Navigate to patient detail page
            await page.click(f'a[href*="{{patient_info.get("id", "")}}"]')
            await page.wait_for_load_state('networkidle')
            
            patient_data = {{
                'patient_info': patient_info,
                'medical_data': {{}}
            }}
            
            # Extract each medical section'''
        
        # Add medical data extraction for each section
        for section, analysis in medical_analysis.items():
            if section == 'tabs_analysis':
                continue
            working_selectors = [sel for sel, count in analysis.get('selectors', {}).items() if count > 0]
            if working_selectors:
                adapter_code += f'''
            
            # Extract {section}
            {section}_data = await self._extract_medical_section(page, self.selectors['medical_sections']['{section}'])
            patient_data['medical_data']['{section}'] = {section}_data'''
        
        adapter_code += '''
            
            return patient_data
            
        except Exception as e:
            logger.error(f"Failed to extract patient data: {e}")
            return {}
    
    async def _extract_patient_info(self, element, index: int) -> Dict:
        """Extract basic patient information from patient row element"""
        try:
            # This will need customization based on actual portal structure
            cells = await element.query_selector_all('td, .cell, .patient-field')
            patient_info = {
                'index': index,
                'id': f'patient_{index}',
                'element_text': await element.text_content()
            }
            
            # Try to extract specific fields
            if len(cells) >= 2:
                patient_info['name'] = await cells[0].text_content()
                patient_info['mrn'] = await cells[1].text_content()
            
            return patient_info
            
        except Exception as e:
            logger.error(f"Failed to extract patient info: {e}")
            return {}
    
    async def _extract_medical_section(self, page, selectors: List[str]) -> List[Dict]:
        """Extract data from medical section using provided selectors"""
        data = []
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text and len(text.strip()) > 5:
                        data.append({
                            'text': text.strip(),
                            'selector_used': selector
                        })
                
                if data:  # If we found data with this selector, use it
                    break
                    
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        return data
'''
        
        return adapter_code

    async def _save_analysis_results(self, portal_name: str, analysis_report: Dict, adapter_code: str):
        """Save all analysis results and generated code"""
        
        # Save analysis report
        safe_name = portal_name.replace(' ', '_').replace('-', '_').lower()
        
        with open(f'{safe_name}_analysis_report.json', 'w') as f:
            json.dump(analysis_report, f, indent=2)
        
        # Save adapter code
        with open(f'{safe_name}_adapter.py', 'w') as f:
            f.write(adapter_code)
        
        # Save configuration template
        config_template = {
            'portal_name': portal_name,
            'base_url': analysis_report.get('portal_url'),
            'login_url': analysis_report.get('login_analysis', {}).get('url'),
            'selectors': {
                'login': analysis_report.get('login_analysis', {}).get('login_selectors', {}),
                'patients': analysis_report['patient_analysis'].get('recommended_selectors', []),
                'medical_sections': {}
            },
            'navigation': analysis_report.get('navigation_analysis', {}),
            'notes': analysis_report.get('adapter_recommendations', [])
        }
        
        with open(f'{safe_name}_config.yaml', 'w') as f:
            yaml.dump(config_template, f, default_flow_style=False)
        
        logger.info(f"📁 Analysis results saved:")
        logger.info(f"   - {safe_name}_analysis_report.json")
        logger.info(f"   - {safe_name}_adapter.py")
        logger.info(f"   - {safe_name}_config.yaml")

    # Helper methods for analysis
    async def _analyze_forms(self, page) -> Dict:
        """Analyze all forms on the page"""
        forms = await page.query_selector_all('form')
        form_analysis = []
        
        for i, form in enumerate(forms):
            inputs = await form.query_selector_all('input, select, textarea')
            input_info = []
            
            for inp in inputs:
                input_data = {
                    'type': await inp.get_attribute('type'),
                    'name': await inp.get_attribute('name'),
                    'id': await inp.get_attribute('id'),
                    'placeholder': await inp.get_attribute('placeholder')
                }
                input_info.append(input_data)
            
            form_analysis.append({
                'form_index': i,
                'inputs': input_info,
                'action': await form.get_attribute('action'),
                'method': await form.get_attribute('method')
            })
        
        return form_analysis

    async def _analyze_tables(self, page) -> List[Dict]:
        """Analyze all tables on the page"""
        tables = await page.query_selector_all('table')
        table_analysis = []
        
        for i, table in enumerate(tables):
            try:
                headers = await table.query_selector_all('th')
                rows = await table.query_selector_all('tr')
                
                header_texts = []
                for header in headers:
                    text = await header.text_content()
                    header_texts.append(text.strip() if text else "")
                
                # Get sample data rows
                sample_rows = []
                data_rows = rows[1:4] if len(rows) > 1 else []
                
                for row in data_rows:
                    cells = await row.query_selector_all('td')
                    row_data = []
                    for cell in cells:
                        text = await cell.text_content()
                        row_data.append(text.strip() if text else "")
                    sample_rows.append(row_data)
                
                table_analysis.append({
                    'table_index': i,
                    'headers': header_texts,
                    'total_rows': len(rows),
                    'sample_data': sample_rows
                })
                
            except Exception as e:
                logger.error(f"Error analyzing table {i}: {e}")
        
        return table_analysis

    async def _analyze_links(self, page) -> List[Dict]:
        """Analyze important links on the page"""
        links = await page.query_selector_all('a[href]')
        link_analysis = []
        
        for link in links[:20]:  # Analyze first 20 links
            try:
                text = await link.text_content()
                href = await link.get_attribute('href')
                
                if text and href and len(text.strip()) > 2:
                    link_analysis.append({
                        'text': text.strip(),
                        'href': href,
                        'is_patient_link': 'patient' in href.lower() or 'summary' in href.lower()
                    })
            except:
                continue
        
        return link_analysis

    async def _find_navigation_elements(self, page) -> List[Dict]:
        """Find navigation elements"""
        nav_elements = []
        
        for selector in self.common_selectors['navigation']:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements[:5]:  # Limit to avoid too much data
                    try:
                        text = await element.text_content()
                        if text and len(text.strip()) > 1:
                            nav_elements.append({
                                'selector': selector,
                                'text': text.strip(),
                                'tag': await element.evaluate('el => el.tagName')
                            })
                    except:
                        continue
            except:
                continue
        
        return nav_elements

    async def _analyze_content_sections(self, page) -> List[Dict]:
        """Analyze main content sections"""
        sections = await page.query_selector_all('section, .section, .content, main, .main')
        section_analysis = []
        
        for i, section in enumerate(sections):
            try:
                text = await section.text_content()
                classes = await section.get_attribute('class')
                section_analysis.append({
                    'index': i,
                    'classes': classes,
                    'text_length': len(text) if text else 0,
                    'preview': text[:100] if text else ""
                })
            except:
                continue
        
        return section_analysis

    async def _extract_sample_patient_data(self, elements) -> List[Dict]:
        """Extract sample data from patient elements"""
        sample_data = []
        
        for i, element in enumerate(elements):
            try:
                text = await element.text_content()
                href = await element.get_attribute('href') if await element.evaluate('el => el.tagName === "A"') else None
                
                sample_data.append({
                    'index': i,
                    'text': text.strip() if text else "",
                    'href': href,
                    'has_link': href is not None
                })
            except:
                continue
        
        return sample_data

    async def _analyze_patient_tables(self, page) -> Dict:
        """Analyze tables specifically for patient data"""
        tables = await page.query_selector_all('table')
        patient_tables = []
        
        for i, table in enumerate(tables):
            try:
                headers = await table.query_selector_all('th')
                header_texts = []
                
                for header in headers:
                    text = await header.text_content()
                    header_texts.append(text.lower().strip() if text else "")
                
                # Check if this looks like a patient table
                patient_keywords = ['patient', 'name', 'mrn', 'id', 'dob', 'date of birth']
                is_patient_table = any(keyword in ' '.join(header_texts) for keyword in patient_keywords)
                
                if is_patient_table:
                    rows = await table.query_selector_all('tr')
                    patient_tables.append({
                        'table_index': i,
                        'headers': header_texts,
                        'row_count': len(rows) - 1,  # Subtract header row
                        'selector': f'table:nth-of-type({i+1}) tbody tr'
                    })
                    
            except Exception as e:
                logger.error(f"Error analyzing patient table {i}: {e}")
        
        return {'patient_tables': patient_tables}

    def _recommend_patient_selectors(self, selector_findings: Dict, table_analysis: Dict) -> List[str]:
        """Recommend best patient selectors based on findings"""
        recommendations = []
        
        # Sort selectors by element count (more elements = more likely to be correct)
        valid_selectors = []
        for selector, data in selector_findings.items():
            if isinstance(data, dict) and 'count' in data and data['count'] > 0:
                valid_selectors.append((selector, data['count']))
        
        # Sort by count descending
        valid_selectors.sort(key=lambda x: x[1], reverse=True)
        
        # Add table-based selectors if patient tables were found
        patient_tables = table_analysis.get('patient_tables', [])
        for table in patient_tables:
            recommendations.append(table['selector'])
        
        # Add top performing general selectors
        for selector, count in valid_selectors[:5]:
            recommendations.append(selector)
        
        return recommendations

    async def _analyze_patient_tabs(self, page) -> Dict:
        """Analyze tabs or sections within patient details"""
        tab_analysis = {}
        
        # Look for tab elements
        tab_selectors = [
            '[role="tab"]', '.tab', '.nav-tab', 'button[role="tab"]',
            '.tab-item', '.nav-item', '.tabs button'
        ]
        
        for selector in tab_selectors:
            try:
                tabs = await page.query_selector_all(selector)
                if tabs:
                    tab_info = []
                    for tab in tabs:
                        text = await tab.text_content()
                        if text:
                            tab_info.append(text.strip())
                    
                    tab_analysis[selector] = {
                        'count': len(tabs),
                        'tab_names': tab_info
                    }
            except:
                continue
        
        return tab_analysis

    def _identify_navigation_patterns(self, nav_elements: List[Dict]) -> Dict:
        """Identify common navigation patterns"""
        patterns = {
            'has_tabs': False,
            'has_sidebar': False,
            'has_breadcrumbs': False,
            'main_nav_items': []
        }
        
        # Check for tabs
        tab_indicators = ['tab', 'tabs']
        for element in nav_elements:
            if any(indicator in element.get('classes', '').lower() for indicator in tab_indicators):
                patterns['has_tabs'] = True
            
            if element.get('tag') == 'nav' or 'nav' in element.get('classes', '').lower():
                patterns['main_nav_items'].append(element.get('text', ''))
        
        return patterns

# Usage function
async def inspect_portal_from_config(config_file: str):
    """Load portal config and run inspection"""
    
    if config_file.endswith('.yaml') or config_file.endswith('.yml'):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    else:
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    inspector = UniversalPortalInspector()
    return await inspector.inspect_portal(config)

# Interactive usage
async def interactive_inspection():
    """Interactive portal inspection"""
    print("🔍 Universal Portal Inspector for WebAutoDash")
    print("=" * 60)
    
    portal_config = {
        'name': input("Portal name: "),
        'url': input("Portal URL (e.g., https://portal.example.com): "),
        'username': input("Username: "),
        'password': input("Password: ")
    }
    
    # Optional custom login URL
    custom_login = input("Custom login URL (press Enter to use portal URL + /login): ")
    if custom_login:
        portal_config['login_url'] = custom_login
    
    inspector = UniversalPortalInspector()
    result = await inspector.inspect_portal(portal_config)
    
    print(f"\n✅ Inspection complete! Check the generated files:")
    safe_name = portal_config['name'].replace(' ', '_').replace('-', '_').lower()
    print(f"   - {safe_name}_analysis_report.json")
    print(f"   - {safe_name}_adapter.py")
    print(f"   - {safe_name}_config.yaml")
    
    return result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run with config file
        asyncio.run(inspect_portal_from_config(sys.argv[1]))
    else:
        # Interactive mode
        asyncio.run(interactive_inspection()) 
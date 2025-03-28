"""
Comprehensive Portal Analyzer
Performs deep inspection of any web portal to discover complete structure, navigation, and data patterns
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensivePortalAnalyzer:
    def __init__(self):
        self.discovered_urls = set()
        self.analyzed_pages = {}
        self.navigation_map = {}
        self.data_patterns = {}
        self.form_patterns = {}
        self.element_inventory = {}
        self.css_selectors = set()
        self.portal_structure = {}
        
    async def analyze_portal(self, base_url: str, credentials: Dict[str, str], 
                           max_depth: int = 3, analysis_name: str = "portal_analysis") -> Dict[str, Any]:
        """
        Comprehensive portal analysis
        
        Args:
            base_url: Portal's base URL
            credentials: Login credentials
            max_depth: Maximum crawl depth  
            analysis_name: Name for saving results
        """
        analysis_start = datetime.now()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=300)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                logger.info("🔍 Starting comprehensive portal analysis...")
                
                # Phase 1: Authentication Analysis
                auth_analysis = await self._analyze_authentication(page, base_url, credentials)
                
                # Phase 2: Portal Structure Discovery
                structure_analysis = await self._discover_portal_structure(page, base_url, max_depth)
                
                # Phase 3: Data Pattern Analysis
                data_analysis = await self._analyze_data_patterns(page, context)
                
                # Phase 4: Navigation Flow Mapping
                navigation_analysis = await self._map_navigation_flows(page, context)
                
                # Phase 5: Element Inventory
                element_analysis = await self._create_element_inventory(page, context)
                
                # Phase 6: Security & Performance Analysis
                security_analysis = await self._analyze_security_features(page, context)
                
                # Compile comprehensive report
                comprehensive_report = {
                    "analysis_metadata": {
                        "portal_url": base_url,
                        "analysis_timestamp": analysis_start.isoformat(),
                        "analysis_duration": str(datetime.now() - analysis_start),
                        "total_pages_analyzed": len(self.analyzed_pages),
                        "total_urls_discovered": len(self.discovered_urls),
                        "analysis_depth": max_depth
                    },
                    "authentication_analysis": auth_analysis,
                    "portal_structure": structure_analysis,
                    "data_patterns": data_analysis,
                    "navigation_flows": navigation_analysis,
                    "element_inventory": element_analysis,
                    "security_analysis": security_analysis,
                    "generated_adapters": await self._generate_comprehensive_adapters()
                }
                
                # Save comprehensive report
                await self._save_analysis_report(comprehensive_report, analysis_name)
                
                return comprehensive_report
                
            except Exception as e:
                logger.error(f"❌ Analysis failed: {str(e)}")
                return {"error": str(e), "status": "failed"}
                
            finally:
                await browser.close()
    
    async def _analyze_authentication(self, page: Page, base_url: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Analyze authentication mechanisms and login flow"""
        logger.info("🔐 Analyzing authentication...")
        
        # Navigate to login page
        login_url = f"{base_url}/login" if not base_url.endswith('/login') else base_url
        await page.goto(login_url, wait_until='networkidle')
        
        # Discover login form structure
        login_forms = await page.query_selector_all('form')
        login_analysis = {
            "login_url": login_url,
            "forms_found": len(login_forms),
            "login_fields": [],
            "login_buttons": [],
            "authentication_method": "form_based",
            "security_features": []
        }
        
        for form in login_forms:
            # Analyze form fields
            inputs = await form.query_selector_all('input')
            for input_elem in inputs:
                input_type = await input_elem.get_attribute('type') or 'text'
                input_name = await input_elem.get_attribute('name') or ''
                input_id = await input_elem.get_attribute('id') or ''
                input_class = await input_elem.get_attribute('class') or ''
                
                field_info = {
                    "type": input_type,
                    "name": input_name,
                    "id": input_id,
                    "class": input_class,
                    "selector": f"input[name='{input_name}']" if input_name else f"#{input_id}" if input_id else "input",
                    "xpath": await self._get_xpath(input_elem)
                }
                login_analysis["login_fields"].append(field_info)
            
            # Analyze submit buttons
            buttons = await form.query_selector_all('button, input[type="submit"]')
            for button in buttons:
                button_text = await button.text_content() or await button.get_attribute('value') or ''
                button_class = await button.get_attribute('class') or ''
                button_id = await button.get_attribute('id') or ''
                
                login_analysis["login_buttons"].append({
                    "text": button_text,
                    "class": button_class,
                    "id": button_id,
                    "selector": f"#{button_id}" if button_id else f"button:has-text('{button_text}')"
                })
        
        # Perform login and analyze post-auth state
        try:
            username_field = next((field for field in login_analysis["login_fields"] 
                                 if field["type"] in ["text", "email"] and 
                                 any(keyword in field["name"].lower() for keyword in ["user", "email", "login"])), None)
            
            password_field = next((field for field in login_analysis["login_fields"] 
                                 if field["type"] == "password"), None)
            
            if username_field and password_field:
                await page.fill(f"#{username_field['id']}" if username_field['id'] else f"input[name='{username_field['name']}']", 
                               credentials.get('username', ''))
                await page.fill(f"#{password_field['id']}" if password_field['id'] else f"input[name='{password_field['name']}']", 
                               credentials.get('password', ''))
                
                submit_button = login_analysis["login_buttons"][0] if login_analysis["login_buttons"] else None
                if submit_button:
                    await page.click(submit_button["selector"])
                    await page.wait_for_load_state('networkidle')
                    
                    login_analysis["login_success"] = True
                    login_analysis["post_login_url"] = page.url
                    
        except Exception as e:
            logger.warning(f"Login attempt failed: {e}")
            login_analysis["login_success"] = False
        
        return login_analysis
    
    async def _discover_portal_structure(self, page: Page, base_url: str, max_depth: int) -> Dict[str, Any]:
        """Discover complete portal structure and sitemap"""
        logger.info("🗺️ Discovering portal structure...")
        
        structure = {
            "sitemap": {},
            "page_hierarchy": {},
            "url_patterns": [],
            "common_layouts": {},
            "navigation_menus": []
        }
        
        # Start with current page (dashboard/home)
        await self._crawl_page_recursive(page, page.url, base_url, 0, max_depth, structure)
        
        # Analyze URL patterns
        structure["url_patterns"] = self._analyze_url_patterns(list(self.discovered_urls))
        
        return structure
    
    async def _crawl_page_recursive(self, page: Page, current_url: str, base_url: str, 
                                  depth: int, max_depth: int, structure: Dict) -> None:
        """Recursively crawl pages to build sitemap"""
        if depth > max_depth or current_url in self.discovered_urls:
            return
            
        self.discovered_urls.add(current_url)
        logger.info(f"📄 Analyzing page: {current_url} (depth: {depth})")
        
        try:
            await page.goto(current_url, wait_until='networkidle')
            await page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
            
            # Analyze current page
            page_analysis = await self._analyze_single_page(page, current_url)
            self.analyzed_pages[current_url] = page_analysis
            
            # Discover navigation links
            links = await page.query_selector_all('a[href]')
            discovered_links = []
            
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    full_url = urljoin(current_url, href)
                    if self._is_internal_url(full_url, base_url):
                        discovered_links.append(full_url)
            
            # Recursively crawl discovered links
            for link_url in discovered_links[:5]:  # Limit to prevent infinite crawling
                if link_url not in self.discovered_urls:
                    await self._crawl_page_recursive(page, link_url, base_url, depth + 1, max_depth, structure)
                    
        except Exception as e:
            logger.warning(f"Failed to crawl {current_url}: {e}")
    
    async def _analyze_single_page(self, page: Page, url: str) -> Dict[str, Any]:
        """Comprehensive analysis of a single page"""
        page_analysis = {
            "url": url,
            "title": await page.title(),
            "forms": [],
            "tables": [],
            "lists": [],
            "navigation_elements": [],
            "data_containers": [],
            "interactive_elements": [],
            "all_selectors": set()
        }
        
        # Analyze forms
        forms = await page.query_selector_all('form')
        for form in forms:
            form_data = await self._analyze_form(form)
            page_analysis["forms"].append(form_data)
        
        # Analyze tables (potential data sources)
        tables = await page.query_selector_all('table')
        for table in tables:
            table_data = await self._analyze_table(table)
            page_analysis["tables"].append(table_data)
        
        # Analyze lists
        lists = await page.query_selector_all('ul, ol, dl')
        for list_elem in lists:
            list_data = await self._analyze_list(list_elem)
            page_analysis["lists"].append(list_data)
        
        # Find navigation elements
        nav_elements = await page.query_selector_all('nav, .nav, .menu, .navigation, [role="navigation"]')
        for nav in nav_elements:
            nav_data = await self._analyze_navigation(nav)
            page_analysis["navigation_elements"].append(nav_data)
        
        # Find data containers
        containers = await page.query_selector_all('div[class*="data"], div[class*="content"], section, article, .card, .panel')
        for container in containers:
            container_data = await self._analyze_container(container)
            page_analysis["data_containers"].append(container_data)
        
        # Discover all unique selectors
        all_elements = await page.query_selector_all('*')
        for element in all_elements[:100]:  # Limit to prevent overwhelm
            selectors = await self._generate_selectors_for_element(element)
            page_analysis["all_selectors"].update(selectors)
        
        return page_analysis
    
    async def _analyze_form(self, form) -> Dict[str, Any]:
        """Analyze form structure and fields"""
        form_data = {
            "action": await form.get_attribute('action') or '',
            "method": await form.get_attribute('method') or 'get',
            "fields": [],
            "buttons": []
        }
        
        # Analyze form inputs
        inputs = await form.query_selector_all('input, select, textarea')
        for input_elem in inputs:
            field_data = {
                "tag": await input_elem.evaluate('el => el.tagName.toLowerCase()'),
                "type": await input_elem.get_attribute('type') or 'text',
                "name": await input_elem.get_attribute('name') or '',
                "id": await input_elem.get_attribute('id') or '',
                "class": await input_elem.get_attribute('class') or '',
                "placeholder": await input_elem.get_attribute('placeholder') or '',
                "required": await input_elem.get_attribute('required') is not None,
                "selector": await self._generate_best_selector(input_elem)
            }
            form_data["fields"].append(field_data)
        
        # Analyze form buttons
        buttons = await form.query_selector_all('button, input[type="submit"], input[type="button"]')
        for button in buttons:
            button_data = {
                "tag": await button.evaluate('el => el.tagName.toLowerCase()'),
                "type": await button.get_attribute('type') or 'button',
                "text": await button.text_content() or await button.get_attribute('value') or '',
                "class": await button.get_attribute('class') or '',
                "selector": await self._generate_best_selector(button)
            }
            form_data["buttons"].append(button_data)
        
        return form_data
    
    async def _analyze_table(self, table) -> Dict[str, Any]:
        """Analyze table structure for data extraction"""
        table_data = {
            "class": await table.get_attribute('class') or '',
            "id": await table.get_attribute('id') or '',
            "headers": [],
            "sample_rows": [],
            "total_rows": 0,
            "selector": await self._generate_best_selector(table)
        }
        
        # Analyze table headers
        headers = await table.query_selector_all('th, thead td')
        for header in headers:
            header_text = await header.text_content()
            if header_text:
                table_data["headers"].append(header_text.strip())
        
        # Sample table rows
        rows = await table.query_selector_all('tbody tr, tr')
        table_data["total_rows"] = len(rows)
        
        for i, row in enumerate(rows[:3]):  # Sample first 3 rows
            cells = await row.query_selector_all('td, th')
            row_data = []
            for cell in cells:
                cell_text = await cell.text_content()
                row_data.append(cell_text.strip() if cell_text else '')
            table_data["sample_rows"].append(row_data)
        
        return table_data
    
    async def _analyze_list(self, list_elem) -> Dict[str, Any]:
        """Analyze list structure"""
        list_data = {
            "tag": await list_elem.evaluate('el => el.tagName.toLowerCase()'),
            "class": await list_elem.get_attribute('class') or '',
            "id": await list_elem.get_attribute('id') or '',
            "items": [],
            "total_items": 0,
            "selector": await self._generate_best_selector(list_elem)
        }
        
        items = await list_elem.query_selector_all('li, dt, dd')
        list_data["total_items"] = len(items)
        
        for item in items[:5]:  # Sample first 5 items
            item_text = await item.text_content()
            if item_text:
                list_data["items"].append(item_text.strip()[:100])  # Limit length
        
        return list_data
    
    async def _analyze_navigation(self, nav) -> Dict[str, Any]:
        """Analyze navigation structure"""
        nav_data = {
            "class": await nav.get_attribute('class') or '',
            "id": await nav.get_attribute('id') or '',
            "links": [],
            "selector": await self._generate_best_selector(nav)
        }
        
        links = await nav.query_selector_all('a[href]')
        for link in links:
            link_text = await link.text_content()
            link_href = await link.get_attribute('href')
            if link_text and link_href:
                nav_data["links"].append({
                    "text": link_text.strip(),
                    "href": link_href,
                    "selector": await self._generate_best_selector(link)
                })
        
        return nav_data
    
    async def _analyze_container(self, container) -> Dict[str, Any]:
        """Analyze data container"""
        container_data = {
            "tag": await container.evaluate('el => el.tagName.toLowerCase()'),
            "class": await container.get_attribute('class') or '',
            "id": await container.get_attribute('id') or '',
            "text_content": '',
            "child_elements": [],
            "selector": await self._generate_best_selector(container)
        }
        
        # Get text content sample
        text_content = await container.text_content()
        if text_content:
            container_data["text_content"] = text_content.strip()[:200]  # Limit length
        
        # Analyze child elements
        children = await container.query_selector_all('> *')
        for child in children[:10]:  # Limit children
            child_tag = await child.evaluate('el => el.tagName.toLowerCase()')
            child_class = await child.get_attribute('class') or ''
            container_data["child_elements"].append({
                "tag": child_tag,
                "class": child_class
            })
        
        return container_data
    
    async def _analyze_data_patterns(self, page: Page, context: BrowserContext) -> Dict[str, Any]:
        """Analyze data patterns across pages"""
        logger.info("📊 Analyzing data patterns...")
        
        data_patterns = {
            "common_data_types": {},
            "table_patterns": {},
            "form_patterns": {},
            "api_endpoints": set(),
            "data_relationships": {}
        }
        
        # Analyze patterns from all discovered pages
        for url, page_data in self.analyzed_pages.items():
            # Analyze table patterns
            for table in page_data.get("tables", []):
                if table["headers"]:
                    pattern_key = "|".join(table["headers"])
                    if pattern_key not in data_patterns["table_patterns"]:
                        data_patterns["table_patterns"][pattern_key] = []
                    data_patterns["table_patterns"][pattern_key].append(url)
            
            # Analyze form patterns
            for form in page_data.get("forms", []):
                field_types = [field["type"] for field in form["fields"]]
                pattern_key = "|".join(field_types)
                if pattern_key not in data_patterns["form_patterns"]:
                    data_patterns["form_patterns"][pattern_key] = []
                data_patterns["form_patterns"][pattern_key].append(url)
        
        return data_patterns
    
    async def _map_navigation_flows(self, page: Page, context: BrowserContext) -> Dict[str, Any]:
        """Map navigation flows and user journeys"""
        logger.info("🗺️ Mapping navigation flows...")
        
        navigation_flows = {
            "user_journeys": {},
            "page_connections": {},
            "common_pathways": [],
            "breadcrumb_patterns": []
        }
        
        # Build navigation graph from discovered pages
        for url, page_data in self.analyzed_pages.items():
            connections = []
            for nav in page_data.get("navigation_elements", []):
                for link in nav.get("links", []):
                    full_link = urljoin(url, link["href"])
                    connections.append({
                        "destination": full_link,
                        "link_text": link["text"],
                        "selector": link["selector"]
                    })
            navigation_flows["page_connections"][url] = connections
        
        return navigation_flows
    
    async def _create_element_inventory(self, page: Page, context: BrowserContext) -> Dict[str, Any]:
        """Create comprehensive element inventory"""
        logger.info("📋 Creating element inventory...")
        
        inventory = {
            "css_selectors": list(self.css_selectors),
            "element_types": {},
            "common_classes": {},
            "common_ids": {},
            "xpath_patterns": []
        }
        
        # Compile element statistics
        all_classes = []
        all_ids = []
        element_counts = {}
        
        for url, page_data in self.analyzed_pages.items():
            for selector in page_data.get("all_selectors", set()):
                self.css_selectors.add(selector)
        
        inventory["css_selectors"] = list(self.css_selectors)
        
        return inventory
    
    async def _analyze_security_features(self, page: Page, context: BrowserContext) -> Dict[str, Any]:
        """Analyze security features and requirements"""
        logger.info("🔒 Analyzing security features...")
        
        security_analysis = {
            "csrf_tokens": [],
            "session_management": {},
            "ssl_certificate": {},
            "content_security_policy": {},
            "authentication_requirements": {}
        }
        
        # Check for CSRF tokens
        csrf_inputs = await page.query_selector_all('input[name*="csrf"], input[name*="token"]')
        for csrf_input in csrf_inputs:
            token_name = await csrf_input.get_attribute('name')
            token_value = await csrf_input.get_attribute('value')
            security_analysis["csrf_tokens"].append({
                "name": token_name,
                "selector": f"input[name='{token_name}']"
            })
        
        return security_analysis
    
    async def _generate_comprehensive_adapters(self) -> Dict[str, str]:
        """Generate comprehensive adapters based on analysis"""
        logger.info("⚙️ Generating comprehensive adapters...")
        
        adapters = {}
        
        # Generate main portal adapter
        main_adapter = self._create_main_adapter_code()
        adapters["main_portal_adapter.py"] = main_adapter
        
        # Generate specialized adapters for each data type
        for pattern_key, urls in self.data_patterns.get("table_patterns", {}).items():
            adapter_name = f"table_adapter_{hash(pattern_key) % 10000}.py"
            table_adapter = self._create_table_adapter_code(pattern_key, urls)
            adapters[adapter_name] = table_adapter
        
        return adapters
    
    def _create_main_adapter_code(self) -> str:
        """Create main adapter code based on analysis"""
        # Extract common patterns
        login_fields = []
        for page_data in self.analyzed_pages.values():
            for form in page_data.get("forms", []):
                if any(field["type"] == "password" for field in form["fields"]):
                    login_fields = form["fields"]
                    break
        
        adapter_code = f'''"""
Generated Comprehensive Portal Adapter
Auto-generated from comprehensive portal analysis
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensivePortalAdapter:
    def __init__(self):
        self.name = "Comprehensive Portal Adapter"
        self.discovered_urls = {list(self.discovered_urls)}
        self.navigation_map = {json.dumps(self.navigation_map, indent=8)}
        
    async def extract_patient_data(self, target_url: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Main extraction method using discovered patterns"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=300)
            context = await browser.new_context(viewport={{'width': 1920, 'height': 1080}})
            page = await context.new_page()
            
            try:
                # Login using discovered patterns
                await self._perform_login(page, target_url, credentials)
                
                # Extract data from all discovered pages
                all_data = []
                for url in self.discovered_urls:
                    if "patient" in url.lower() or "data" in url.lower():
                        page_data = await self._extract_from_page(page, url)
                        all_data.extend(page_data)
                
                return {{
                    "extraction_timestamp": datetime.now().isoformat(),
                    "portal_name": self.name,
                    "total_records": len(all_data),
                    "data": all_data,
                    "status": "success"
                }}
                
            except Exception as e:
                logger.error(f"Extraction failed: {{str(e)}}")
                return {{"status": "error", "error": str(e)}}
                
            finally:
                await browser.close()
    
    async def _perform_login(self, page: Page, target_url: str, credentials: Dict[str, str]) -> None:
        """Login using discovered form patterns"""
        login_url = f"{{target_url}}/login"
        await page.goto(login_url, wait_until='networkidle')
        
        # Use discovered login selectors
        {self._generate_login_code(login_fields)}
        
        await page.wait_for_load_state('networkidle')
    
    async def _extract_from_page(self, page: Page, url: str) -> List[Dict[str, Any]]:
        """Extract data from page using discovered patterns"""
        await page.goto(url, wait_until='networkidle')
        extracted_data = []
        
        # Extract from discovered tables
        {self._generate_table_extraction_code()}
        
        return extracted_data

if __name__ == "__main__":
    # Test the comprehensive adapter
    adapter = ComprehensivePortalAdapter()
    print("🚀 Comprehensive Portal Adapter Generated Successfully!")
    print(f"📊 Discovered {{len(adapter.discovered_urls)}} URLs")
    print("🔧 Ready for data extraction")
'''
        
        return adapter_code
    
    def _generate_login_code(self, login_fields: List[Dict]) -> str:
        """Generate login code from discovered fields"""
        if not login_fields:
            return "# No login fields discovered"
        
        username_field = next((f for f in login_fields if f["type"] in ["text", "email"]), None)
        password_field = next((f for f in login_fields if f["type"] == "password"), None)
        
        if username_field and password_field:
            return f'''
        await page.fill("{username_field.get('selector', '#username')}", credentials['username'])
        await page.fill("{password_field.get('selector', '#password')}", credentials['password'])
        await page.click("button[type='submit']")
'''
        return "# Login pattern not fully recognized"
    
    def _generate_table_extraction_code(self) -> str:
        """Generate table extraction code"""
        return '''
        tables = await page.query_selector_all('table')
        for table in tables:
            rows = await table.query_selector_all('tbody tr')
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 2:
                    row_data = {}
                    for i, cell in enumerate(cells):
                        cell_text = await cell.text_content()
                        row_data[f'column_{i}'] = cell_text.strip() if cell_text else ''
                    extracted_data.append(row_data)
'''
    
    def _create_table_adapter_code(self, pattern_key: str, urls: List[str]) -> str:
        """Create specialized table adapter"""
        headers = pattern_key.split("|")
        return f'''
# Specialized adapter for table pattern: {pattern_key}
# Found in URLs: {urls}

async def extract_table_data_{hash(pattern_key) % 10000}(page: Page) -> List[Dict[str, Any]]:
    """Extract data from tables with headers: {headers}"""
    data = []
    tables = await page.query_selector_all('table')
    
    for table in tables:
        headers_found = await table.query_selector_all('th')
        if len(headers_found) == {len(headers)}:
            rows = await table.query_selector_all('tbody tr')
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= {len(headers)}:
                    record = {{}}
                    {chr(10).join([f'                    record["{header}"] = await cells[{i}].text_content() or ""' 
                                  for i, header in enumerate(headers)])}
                    data.append(record)
    
    return data
'''
    
    async def _save_analysis_report(self, report: Dict[str, Any], analysis_name: str) -> None:
        """Save comprehensive analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save main report
        report_path = Path(f"Projects/WebAutoDash/portal_analyses/{analysis_name}_comprehensive_{timestamp}.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        # Save generated adapters
        for adapter_name, adapter_code in report.get("generated_adapters", {}).items():
            adapter_path = Path(f"Projects/WebAutoDash/portal_adapters/{analysis_name}_{adapter_name}")
            with open(adapter_path, 'w', encoding='utf-8') as f:
                f.write(adapter_code)
        
        logger.info(f"📁 Analysis saved to: {report_path}")
    
    # Utility methods
    async def _generate_best_selector(self, element) -> str:
        """Generate the best CSS selector for element"""
        element_id = await element.get_attribute('id')
        if element_id:
            return f"#{element_id}"
        
        element_class = await element.get_attribute('class')
        if element_class:
            classes = element_class.split()
            if classes:
                return f".{classes[0]}"
        
        tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
        return tag_name
    
    async def _generate_selectors_for_element(self, element) -> Set[str]:
        """Generate all possible selectors for element"""
        selectors = set()
        
        element_id = await element.get_attribute('id')
        if element_id:
            selectors.add(f"#{element_id}")
        
        element_class = await element.get_attribute('class')
        if element_class:
            classes = element_class.split()
            for cls in classes:
                selectors.add(f".{cls}")
        
        tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
        selectors.add(tag_name)
        
        return selectors
    
    async def _get_xpath(self, element) -> str:
        """Get XPath for element"""
        try:
            xpath = await element.evaluate('''
                el => {
                    const getXPath = (element) => {
                        if (element.id) return `//*[@id="${element.id}"]`;
                        if (element === document.body) return '/html/body';
                        let ix = 0;
                        const siblings = element.parentNode.childNodes;
                        for (let i = 0; i < siblings.length; i++) {
                            const sibling = siblings[i];
                            if (sibling === element) return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                        }
                    };
                    return getXPath(el);
                }
            ''')
            return xpath or ''
        except:
            return ''
    
    def _is_internal_url(self, url: str, base_url: str) -> bool:
        """Check if URL is internal to the portal"""
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
        return parsed_url.netloc == parsed_base.netloc
    
    def _analyze_url_patterns(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Analyze URL patterns to identify sections"""
        patterns = {}
        for url in urls:
            path = urlparse(url).path
            path_parts = [part for part in path.split('/') if part]
            
            if len(path_parts) >= 2:
                pattern = f"/{path_parts[0]}/..."
                if pattern not in patterns:
                    patterns[pattern] = []
                patterns[pattern].append(url)
        
        return [{"pattern": k, "urls": v, "count": len(v)} for k, v in patterns.items()]


# Main execution function
async def run_comprehensive_analysis(base_url: str, credentials: Dict[str, str], 
                                   analysis_name: str = "portal_analysis") -> Dict[str, Any]:
    """Run comprehensive portal analysis"""
    analyzer = ComprehensivePortalAnalyzer()
    return await analyzer.analyze_portal(base_url, credentials, max_depth=3, analysis_name=analysis_name)

if __name__ == "__main__":
    print("🔍 Comprehensive Portal Analyzer")
    print("📋 This tool performs deep analysis of any web portal")
    print("🚀 Usage: python comprehensive_portal_analyzer.py") 
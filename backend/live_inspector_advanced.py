#!/usr/bin/env python3
"""
Live Portal Inspector - Comprehensive Asynchronous Web Portal Analysis Tool

This module implements a sophisticated web portal inspection system using Playwright
for automated recording of user interactions, network traffic, and dynamic content
analysis. It provides real-time streaming of events and generates replay adapters.

Usage:
    # CLI Mode
    python live_inspector.py --portal-url https://portal.example.com --portal-name "MyPortal"
    
    # Flask Integration
    from live_inspector_advanced import create_inspector_blueprint
    app.register_blueprint(create_inspector_blueprint())

Configuration:
    Use InspectorConfig to customize recording behavior, output directories,
    redaction patterns, and selector strategies.

Features:
    - Asynchronous event recording (DOM, navigation, network, popups)
    - Real-time SocketIO streaming
    - Shadow DOM and iframe traversal
    - Automatic selector generation
    - Screenshot capture with visual metadata
    - Comprehensive portal analysis
    - Replay adapter generation
    - PHI redaction and security compliance
"""

import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Pattern, Set, Union
from urllib.parse import urljoin, urlparse
import argparse
import base64
import hashlib
from dataclasses import dataclass, field

try:
    import jinja2
    from flask import Blueprint, Flask, jsonify, request
    from flask_socketio import SocketIO, emit
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    from pydantic import BaseModel, Field, validator
    from cryptography.fernet import Fernet
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    import_error = str(e)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_inspector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InspectorConfig(BaseModel):
    """Configuration model for the Live Portal Inspector."""
    
    portal_url: str = Field(..., description="Target portal URL to inspect")
    portal_name: str = Field(..., description="Human-readable portal name")
    recording_mode: Literal['full', 'login_only', 'navigation_only'] = Field(
        default='full', 
        description="Scope of recording: full, login_only, or navigation_only"
    )
    output_dir: Path = Field(default=Path("./inspector_output"), description="Output directory for logs and screenshots")
    timeout_minutes: int = Field(default=30, description="Maximum inspection duration in minutes")
    headless: bool = Field(default=False, description="Run browser in headless mode")
    redaction_patterns: List[str] = Field(
        default_factory=lambda: [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{2}/\d{2}/\d{4}\b',  # DOB
            r'\b[A-Z]{2}\d{6,}\b',     # MRN
            r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b'  # Credit Card
        ],
        description="Regex patterns for PHI redaction"
    )
    selector_strategy: Literal['id', 'data-attr', 'class-chain', 'nth-child'] = Field(
        default='id',
        description="Primary selector generation strategy"
    )
    encryption_key: Optional[str] = Field(default=None, description="Optional encryption key for logs")
    
    @validator('output_dir')
    def create_output_dir(cls, v):
        """Ensure output directory exists."""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


class EventModel(BaseModel):
    """Base event model with common fields."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    page_url: str
    frame_url: Optional[str] = None
    event_type: str


class ClickEvent(EventModel):
    """Click event with element details."""
    
    event_type: str = "click"
    selector: str
    tag_name: str
    element_id: Optional[str] = None
    classes: List[str] = Field(default_factory=list)
    attributes: Dict[str, str] = Field(default_factory=dict)
    text_content: Optional[str] = None
    coordinates: Dict[str, float] = Field(default_factory=dict)


class InputEvent(EventModel):
    """Input event with form field details."""
    
    event_type: str = "input"
    selector: str
    input_type: str
    name: Optional[str] = None
    value: str
    placeholder: Optional[str] = None
    label: Optional[str] = None


class NavigationEvent(EventModel):
    """Navigation event for page loads and SPA transitions."""
    
    event_type: str = "navigation"
    navigation_type: Literal['load', 'spa', 'iframe']
    from_url: Optional[str] = None
    dom_ready: bool = False
    network_idle: bool = False
    viewport_size: Dict[str, int] = Field(default_factory=dict)
    scroll_position: Dict[str, float] = Field(default_factory=dict)


class NetworkEvent(EventModel):
    """Network request/response event."""
    
    event_type: str = "network"
    request_url: str
    method: str
    status_code: Optional[int] = None
    request_headers: Dict[str, str] = Field(default_factory=dict)
    response_headers: Dict[str, str] = Field(default_factory=dict)
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    duration_ms: Optional[float] = None


class PopupEvent(EventModel):
    """Popup/modal dialog event."""
    
    event_type: str = "popup"
    popup_selector: str
    trigger_selector: Optional[str] = None
    inner_text: str
    form_fields: List[Dict[str, Any]] = Field(default_factory=list)
    buttons: List[Dict[str, str]] = Field(default_factory=list)
    links: List[Dict[str, str]] = Field(default_factory=list)
    screenshot_path: Optional[str] = None


class SelectorGenerator:
    """Advanced selector generation with multiple strategies."""
    
    def __init__(self, strategy: str = 'id'):
        self.strategy = strategy
        self.js_helper = """
        window.generateSelector = function(element) {
            if (!element || element.nodeType !== 1) return '';
            
            // Strategy 1: ID
            if (element.id) {
                return '#' + element.id;
            }
            
            // Strategy 2: Data attributes
            const dataAttrs = ['data-test', 'data-testid', 'data-cy', 'data-qa'];
            for (const attr of dataAttrs) {
                if (element.hasAttribute(attr)) {
                    return `[${attr}="${element.getAttribute(attr)}"]`;
                }
            }
            
            // Strategy 3: Class chain
            const classes = Array.from(element.classList);
            if (classes.length > 0) {
                const classSelector = '.' + classes.join('.');
                const siblings = Array.from(element.parentElement?.children || []);
                const matchingSiblings = siblings.filter(s => s.matches(classSelector));
                if (matchingSiblings.length === 1) {
                    return classSelector;
                }
            }
            
            // Strategy 4: nth-child fallback
            let path = [];
            let current = element;
            
            while (current && current.nodeType === 1 && current !== document.body) {
                let selector = current.tagName.toLowerCase();
                
                if (current.id) {
                    selector = '#' + current.id;
                    path.unshift(selector);
                    break;
                }
                
                const siblings = Array.from(current.parentElement?.children || []);
                const sameTagSiblings = siblings.filter(s => s.tagName === current.tagName);
                
                if (sameTagSiblings.length > 1) {
                    const index = sameTagSiblings.indexOf(current) + 1;
                    selector += `:nth-child(${index})`;
                }
                
                path.unshift(selector);
                current = current.parentElement;
            }
            
            return path.join(' > ');
        };
        """
    
    async def inject_helper(self, page: Page) -> None:
        """Inject selector generation helper into page."""
        await page.add_init_script(self.js_helper)
    
    async def generate_selector(self, page: Page, element_handle) -> str:
        """Generate optimal selector for element."""
        try:
            selector = await page.evaluate(
                'element => window.generateSelector(element)',
                element_handle
            )
            return selector or 'unknown'
        except Exception as e:
            logger.warning(f"Selector generation failed: {e}")
            return 'unknown'


class PHIRedactor:
    """PHI redaction utility with pattern matching."""
    
    def __init__(self, patterns: List[str]):
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def redact_text(self, text: str) -> str:
        """Redact PHI from text using configured patterns."""
        if not text:
            return text
            
        redacted = text
        for pattern in self.patterns:
            redacted = pattern.sub('[REDACTED]', redacted)
        return redacted
    
    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact PHI from dictionary."""
        if isinstance(data, dict):
            return {k: self.redact_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact_dict(item) for item in data]
        elif isinstance(data, str):
            return self.redact_text(data)
        return data


class ScreenshotManager:
    """Screenshot capture and management."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.screenshot_dir = output_dir / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    async def capture_screenshot(
        self, 
        page: Page, 
        inspection_id: str, 
        screenshot_type: str = "page"
    ) -> str:
        """Capture and save screenshot."""
        timestamp = int(time.time() * 1000)
        filename = f"{inspection_id}_{screenshot_type}_{timestamp}.png"
        filepath = self.screenshot_dir / filename
        
        try:
            await page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return ""
    
    async def get_visual_metadata(self, page: Page) -> Dict[str, Any]:
        """Get viewport and scroll position metadata."""
        try:
            viewport = await page.evaluate("""
                () => ({
                    width: window.innerWidth,
                    height: window.innerHeight,
                    devicePixelRatio: window.devicePixelRatio,
                    scrollX: window.scrollX,
                    scrollY: window.scrollY,
                    documentWidth: document.documentElement.scrollWidth,
                    documentHeight: document.documentElement.scrollHeight
                })
            """)
            return viewport
        except Exception as e:
            logger.error(f"Visual metadata extraction failed: {e}")
            return {}


class LivePortalInspector:
    """Main inspector class implementing comprehensive portal analysis."""
    
    def __init__(self, config: InspectorConfig, socketio=None):
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError(f"Required dependencies not available: {import_error}")
            
        self.config = config
        self.socketio = socketio
        self.selector_generator = SelectorGenerator(config.selector_strategy)
        self.phi_redactor = PHIRedactor(config.redaction_patterns)
        self.screenshot_manager = ScreenshotManager(config.output_dir)
        
        # State management
        self.inspection_id: Optional[str] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_recording = False
        self.events: List[EventModel] = []
        
        # Analysis data
        self.forms_discovered: List[Dict[str, Any]] = []
        self.tables_discovered: List[Dict[str, Any]] = []
        self.navigation_flow: List[str] = []
        self.api_endpoints: Set[str] = set()
        self.popup_dialogs: List[Dict[str, Any]] = []
        
        # Setup encryption if key provided
        self.cipher = None
        if config.encryption_key:
            key = config.encryption_key.encode()
            if len(key) != 44:  # Fernet requires 32-byte key, base64 encoded = 44 chars
                key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
            self.cipher = Fernet(key)
    
    async def start_inspection(self) -> str:
        """Start new inspection session."""
        if self.is_recording:
            raise RuntimeError("Inspection already in progress")
        
        self.inspection_id = str(uuid.uuid4())
        self.is_recording = True
        self.events.clear()
        
        logger.info(f"Starting inspection {self.inspection_id} for {self.config.portal_url}")
        
        try:
            # Launch browser
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=self.config.headless)
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_video_dir=str(self.config.output_dir / "videos" / self.inspection_id)
            )
            
            # Setup request/response interception
            await self._setup_network_interception()
            
            # Create main page
            self.page = await self.context.new_page()
            await self.selector_generator.inject_helper(self.page)
            
            # Setup event listeners
            await self._setup_event_listeners()
            
            # Navigate to portal
            await self._navigate_and_record(self.config.portal_url)
            
            # Start background tasks
            asyncio.create_task(self._monitor_dynamic_content())
            asyncio.create_task(self._handle_timeout())
            
            # Emit start event
            if self.socketio:
                self.socketio.emit('inspection_started', {
                    'inspection_id': self.inspection_id,
                    'portal_url': self.config.portal_url,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            
            return self.inspection_id
            
        except Exception as e:
            logger.exception(f"Failed to start inspection: {e}")
            await self.stop_inspection()
            raise
    
    async def stop_inspection(self) -> Dict[str, Any]:
        """Stop inspection and generate analysis."""
        if not self.is_recording:
            return {"error": "No inspection in progress"}
        
        self.is_recording = False
        
        try:
            # Perform final analysis
            analysis = await self._perform_comprehensive_analysis()
            
            # Save logs
            await self._save_inspection_logs()
            
            # Generate adapter
            adapter_path = await self._generate_replay_adapter()
            
            # Cleanup
            if self.browser:
                await self.browser.close()
            
            result = {
                'inspection_id': self.inspection_id,
                'success': True,
                'events_count': len(self.events),
                'analysis': analysis,
                'adapter_path': adapter_path,
                'logs_path': str(self.config.output_dir / "logs" / f"{self.inspection_id}.ndjson")
            }
            
            # Emit stop event
            if self.socketio:
                self.socketio.emit('inspection_stopped', result)
            
            logger.info(f"Inspection {self.inspection_id} completed")
            return result
            
        except Exception as e:
            logger.exception(f"Error stopping inspection: {e}")
            return {"error": str(e)}
    
    async def _setup_network_interception(self) -> None:
        """Setup network request/response interception."""
        
        async def handle_request(request):
            if not self.is_recording:
                return
                
            # Record request
            event = NetworkEvent(
                page_url=request.url,
                request_url=request.url,
                method=request.method,
                request_headers=dict(request.headers),
                request_body=request.post_data
            )
            
            # Redact PHI from request
            event.request_body = self.phi_redactor.redact_text(event.request_body or "")
            event.request_headers = self.phi_redactor.redact_dict(event.request_headers)
            
            await self._record_event(event)
        
        async def handle_response(response):
            if not self.is_recording:
                return
                
            try:
                # Get response body
                body = ""
                if response.status < 400:
                    try:
                        body = await response.text()
                    except:
                        body = "[Binary Content]"
                
                # Find corresponding request event
                for event in reversed(self.events):
                    if (isinstance(event, NetworkEvent) and 
                        event.request_url == response.url and 
                        event.status_code is None):
                        
                        # Update with response data
                        event.status_code = response.status
                        event.response_headers = dict(response.headers)
                        event.response_body = self.phi_redactor.redact_text(body)
                        event.duration_ms = (datetime.now(timezone.utc) - event.timestamp).total_seconds() * 1000
                        
                        # Track API endpoints
                        if response.url.endswith(('.json', '/api/', '/graphql')):
                            self.api_endpoints.add(response.url)
                        
                        break
                        
            except Exception as e:
                logger.warning(f"Response handling error: {e}")
        
        self.context.on('request', handle_request)
        self.context.on('response', handle_response)
    
    async def _setup_event_listeners(self) -> None:
        """Setup DOM event listeners."""
        
        # Inject click tracking
        await self.page.add_init_script("""
            document.addEventListener('click', (event) => {
                const clickId = 'click_' + Date.now() + '_' + Math.random();
                event.target.setAttribute('data-click-id', clickId);
                
                console.log('CLICK_EVENT:' + JSON.stringify({
                    clickId: clickId,
                    tagName: event.target.tagName,
                    id: event.target.id,
                    classes: Array.from(event.target.classList),
                    attributes: Object.fromEntries(
                        Array.from(event.target.attributes).map(attr => [attr.name, attr.value])
                    ),
                    textContent: event.target.textContent,
                    coordinates: { x: event.clientX, y: event.clientY }
                }));
            }, true);
        """)
        
        # Listen for console messages
        self.page.on('console', lambda msg: asyncio.create_task(self._handle_console_message(msg)))
    
    async def _handle_console_message(self, msg) -> None:
        """Handle console messages from injected scripts."""
        try:
            if msg.type == 'log':
                text = msg.text
                if text.startswith('CLICK_EVENT:'):
                    event_data = json.loads(text[12:])
                    await self._handle_click_event(event_data)
        except Exception as e:
            logger.warning(f"Console message handling error: {e}")
    
    async def _handle_click_event(self, event_data):
        """Handle click event data from console."""
        try:
            element = await self.page.query_selector(f'[data-click-id="{event_data["clickId"]}"]')
            if element:
                selector = await self.selector_generator.generate_selector(self.page, element)
                
                # Check for popup triggers immediately after click
                await asyncio.sleep(0.1)  # Brief wait for potential popup
                await self._check_for_popups(selector)
                
                click_event = ClickEvent(
                    page_url=self.page.url,
                    selector=selector,
                    tag_name=event_data.get('tagName', ''),
                    element_id=event_data.get('id'),
                    classes=event_data.get('classes', []),
                    attributes=event_data.get('attributes', {}),
                    text_content=self.phi_redactor.redact_text(event_data.get('textContent', '')),
                    coordinates=event_data.get('coordinates', {})
                )
                
                await self._record_event(click_event)
                
        except Exception as e:
            logger.error(f"Click event handling error: {e}")
    
    async def _navigate_and_record(self, url: str) -> None:
        """Navigate to URL and record navigation event."""
        try:
            await self.page.goto(url, wait_until='domcontentloaded')
            
            # Wait for network idle
            await self.page.wait_for_load_state('networkidle')
            
            # Get visual metadata
            visual_meta = await self.screenshot_manager.get_visual_metadata(self.page)
            
            # Take screenshot
            screenshot_path = await self.screenshot_manager.capture_screenshot(
                self.page, self.inspection_id, "navigation"
            )
            
            # Record navigation event
            nav_event = NavigationEvent(
                page_url=url,
                navigation_type='load',
                dom_ready=True,
                network_idle=True,
                viewport_size={
                    'width': visual_meta.get('width', 0),
                    'height': visual_meta.get('height', 0)
                },
                scroll_position={
                    'x': visual_meta.get('scrollX', 0),
                    'y': visual_meta.get('scrollY', 0)
                }
            )
            
            await self._record_event(nav_event)
            self.navigation_flow.append(url)
            
            # Analyze initial page structure
            await self._analyze_page_structure()
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            raise
    
    async def _check_for_popups(self, trigger_selector: str) -> None:
        """Check for popup dialogs after element interaction."""
        try:
            # Common popup selectors
            popup_selectors = [
                '[role="dialog"]',
                '.modal',
                '.popup',
                '.overlay',
                '[data-modal]',
                '.dialog'
            ]
            
            for selector in popup_selectors:
                elements = await self.page.query_selector_all(selector)
                for element in elements:
                    is_visible = await element.is_visible()
                    if is_visible:
                        await self._record_popup_event(element, trigger_selector)
                        break
                        
        except Exception as e:
            logger.warning(f"Popup detection error: {e}")
    
    async def _record_popup_event(self, popup_element, trigger_selector: str) -> None:
        """Record detailed popup event."""
        try:
            popup_selector = await self.selector_generator.generate_selector(self.page, popup_element)
            inner_text = await popup_element.inner_text()
            
            # Extract form fields
            form_fields = []
            form_elements = await popup_element.query_selector_all('input, select, textarea')
            for field in form_elements:
                field_data = await self.page.evaluate('''
                    element => ({
                        name: element.name,
                        type: element.type,
                        placeholder: element.placeholder,
                        value: element.value,
                        label: element.labels?.[0]?.textContent || ''
                    })
                ''', field)
                form_fields.append(field_data)
            
            # Extract buttons
            buttons = []
            button_elements = await popup_element.query_selector_all('button, input[type="submit"], input[type="button"]')
            for button in button_elements:
                button_text = await button.inner_text()
                buttons.append({'text': button_text, 'type': await button.get_attribute('type') or 'button'})
            
            # Extract links
            links = []
            link_elements = await popup_element.query_selector_all('a')
            for link in link_elements:
                link_text = await link.inner_text()
                link_href = await link.get_attribute('href')
                links.append({'text': link_text, 'href': link_href})
            
            # Take screenshot
            screenshot_path = await self.screenshot_manager.capture_screenshot(
                self.page, self.inspection_id, "popup"
            )
            
            popup_event = PopupEvent(
                page_url=self.page.url,
                popup_selector=popup_selector,
                trigger_selector=trigger_selector,
                inner_text=self.phi_redactor.redact_text(inner_text),
                form_fields=self.phi_redactor.redact_dict(form_fields),
                buttons=buttons,
                links=links,
                screenshot_path=screenshot_path
            )
            
            await self._record_event(popup_event)
            self.popup_dialogs.append({
                'selector': popup_selector,
                'trigger': trigger_selector,
                'fields': form_fields,
                'buttons': buttons,
                'links': links
            })
            
        except Exception as e:
            logger.error(f"Popup recording error: {e}")
    
    async def _monitor_dynamic_content(self) -> None:
        """Monitor for dynamic content changes."""
        while self.is_recording:
            try:
                # Check for SPA navigation
                current_url = self.page.url
                if current_url not in self.navigation_flow:
                    nav_event = NavigationEvent(
                        page_url=current_url,
                        navigation_type='spa',
                        from_url=self.navigation_flow[-1] if self.navigation_flow else None
                    )
                    await self._record_event(nav_event)
                    self.navigation_flow.append(current_url)
                
                # Check for new frames
                for frame in self.page.frames:
                    if frame.url and frame.url not in self.navigation_flow:
                        nav_event = NavigationEvent(
                            page_url=self.page.url,
                            frame_url=frame.url,
                            navigation_type='iframe'
                        )
                        await self._record_event(nav_event)
                        self.navigation_flow.append(frame.url)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.warning(f"Dynamic content monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _handle_timeout(self) -> None:
        """Handle inspection timeout."""
        await asyncio.sleep(self.config.timeout_minutes * 60)
        if self.is_recording:
            logger.info(f"Inspection timeout reached ({self.config.timeout_minutes} minutes)")
            await self.stop_inspection()
    
    async def _analyze_page_structure(self) -> None:
        """Analyze current page structure for forms and tables."""
        try:
            # Analyze forms
            forms = await self.page.query_selector_all('form')
            for form in forms:
                form_data = await self.page.evaluate('''
                    form => {
                        const fields = Array.from(form.querySelectorAll('input, select, textarea')).map(field => ({
                            name: field.name,
                            type: field.type,
                            placeholder: field.placeholder,
                            label: field.labels?.[0]?.textContent || '',
                            required: field.required
                        }));
                        
                        return {
                            action: form.action,
                            method: form.method,
                            fields: fields
                        };
                    }
                ''', form)
                
                form_selector = await self.selector_generator.generate_selector(self.page, form)
                form_data['selector'] = form_selector
                self.forms_discovered.append(form_data)
            
            # Analyze tables
            tables = await self.page.query_selector_all('table')
            for table in tables:
                table_data = await self.page.evaluate('''
                    table => {
                        const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
                        const rows = table.querySelectorAll('tbody tr, tr');
                        const sampleData = Array.from(rows).slice(0, 3).map(row => 
                            Array.from(row.querySelectorAll('td')).map(td => td.textContent.trim())
                        );
                        
                        return {
                            headers: headers,
                            rowCount: rows.length,
                            sampleData: sampleData
                        };
                    }
                ''', table)
                
                table_selector = await self.selector_generator.generate_selector(self.page, table)
                table_data['selector'] = table_selector
                self.tables_discovered.append(table_data)
                
        except Exception as e:
            logger.error(f"Page structure analysis error: {e}")
    
    async def _record_event(self, event: EventModel) -> None:
        """Record event with validation and streaming."""
        try:
            # Validate event
            event_dict = event.dict()
            
            # Add to events list
            self.events.append(event)
            
            # Stream to SocketIO
            if self.socketio:
                self.socketio.emit('live_inspection_update', {
                    'inspection_id': self.inspection_id,
                    'event': event_dict,
                    'timestamp': event.timestamp.isoformat()
                })
            
            logger.debug(f"Recorded {event.event_type} event: {event.event_id}")
            
        except Exception as e:
            logger.error(f"Event recording error: {e}")
    
    async def _perform_comprehensive_analysis(self) -> Dict[str, Any]:
        """Perform comprehensive analysis of recorded events."""
        analysis = {
            'summary': {
                'total_events': len(self.events),
                'navigation_count': len([e for e in self.events if isinstance(e, NavigationEvent)]),
                'click_count': len([e for e in self.events if isinstance(e, ClickEvent)]),
                'input_count': len([e for e in self.events if isinstance(e, InputEvent)]),
                'network_count': len([e for e in self.events if isinstance(e, NetworkEvent)]),
                'popup_count': len([e for e in self.events if isinstance(e, PopupEvent)])
            },
            'forms': self.forms_discovered,
            'tables': self.tables_discovered,
            'navigation_flow': self.navigation_flow,
            'api_endpoints': list(self.api_endpoints),
            'popup_dialogs': self.popup_dialogs,
            'demographic_fields': self._identify_demographic_fields(),
            'medical_sections': self._classify_medical_sections()
        }
        
        return analysis
    
    def _identify_demographic_fields(self) -> List[Dict[str, Any]]:
        """Identify demographic fields from forms."""
        demographic_keywords = {
            'name': ['name', 'first_name', 'last_name', 'full_name'],
            'dob': ['dob', 'date_of_birth', 'birthdate', 'birth_date'],
            'ssn': ['ssn', 'social_security', 'social_security_number'],
            'address': ['address', 'street', 'city', 'state', 'zip', 'postal'],
            'phone': ['phone', 'telephone', 'mobile', 'cell'],
            'email': ['email', 'e_mail', 'mail'],
            'gender': ['gender', 'sex'],
            'race': ['race', 'ethnicity', 'ethnic'],
            'insurance': ['insurance', 'provider', 'policy', 'subscriber']
        }
        
        demographic_fields = []
        
        for form in self.forms_discovered:
            for field in form.get('fields', []):
                field_name = (field.get('name', '') + ' ' + field.get('label', '')).lower()
                
                for category, keywords in demographic_keywords.items():
                    if any(keyword in field_name for keyword in keywords):
                        demographic_fields.append({
                            'category': category,
                            'field_name': field.get('name'),
                            'label': field.get('label'),
                            'form_selector': form.get('selector'),
                            'type': field.get('type')
                        })
                        break
        
        return demographic_fields
    
    def _classify_medical_sections(self) -> Dict[str, List[str]]:
        """Classify pages/sections by medical content."""
        medical_keywords = {
            'demographics': ['patient', 'personal', 'contact', 'emergency'],
            'medications': ['medication', 'drugs', 'prescriptions', 'pharmacy'],
            'labs': ['lab', 'laboratory', 'test', 'results', 'blood', 'urine'],
            'vitals': ['vital', 'blood_pressure', 'temperature', 'weight', 'height'],
            'allergies': ['allergy', 'allergies', 'adverse', 'reaction'],
            'appointments': ['appointment', 'schedule', 'visit', 'calendar'],
            'procedures': ['procedure', 'surgery', 'operation', 'treatment'],
            'history': ['history', 'medical_history', 'past', 'previous'],
            'insurance': ['insurance', 'billing', 'payment', 'coverage']
        }
        
        classified_sections = defaultdict(list)
        
        for url in self.navigation_flow:
            url_lower = url.lower()
            for category, keywords in medical_keywords.items():
                if any(keyword in url_lower for keyword in keywords):
                    classified_sections[category].append(url)
                    break
        
        return dict(classified_sections)
    
    async def _save_inspection_logs(self) -> None:
        """Save inspection logs to NDJSON format."""
        logs_dir = self.config.output_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = logs_dir / f"{self.inspection_id}.ndjson"
        
        try:
            with open(log_file, 'w') as f:
                for event in self.events:
                    event_json = json.dumps(event.dict(), default=str)
                    
                    # Encrypt if cipher available
                    if self.cipher:
                        event_json = self.cipher.encrypt(event_json.encode()).decode()
                    
                    f.write(event_json + '\n')
            
            logger.info(f"Logs saved to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to save logs: {e}")
    
    async def _generate_replay_adapter(self) -> str:
        """Generate replay adapter script using Jinja2."""
        template_str = '''#!/usr/bin/env python3
"""
Auto-generated Portal Replay Adapter
Generated from inspection: {{ inspection_id }}
Portal: {{ portal_name }}
Date: {{ generation_date }}
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

CREDENTIALS = {
    'username': 'YOUR_USERNAME_HERE',
    'password': 'YOUR_PASSWORD_HERE'
}

class PortalAdapter:
    """{{ portal_name }} Portal Adapter"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    async def start_browser(self):
        """Initialize browser and context."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
    
    async def login(self):
        """Perform login sequence."""
        await self.page.goto('{{ portal_url }}')
        await self.page.wait_for_load_state('networkidle')
        
        {% for form in forms %}
        {% if 'login' in form.action.lower() or 'signin' in form.action.lower() %}
        # Login form found: {{ form.selector }}
        {% for field in form.fields %}
        {% if 'username' in field.name.lower() or 'email' in field.name.lower() %}
        await self.page.fill('{{ form.selector }} input[name="{{ field.name }}"]', CREDENTIALS['username'])
        {% elif 'password' in field.name.lower() %}
        await self.page.fill('{{ form.selector }} input[name="{{ field.name }}"]', CREDENTIALS['password'])
        {% endif %}
        {% endfor %}
        
        await self.page.click('{{ form.selector }} input[type="submit"], {{ form.selector }} button[type="submit"]')
        await self.page.wait_for_load_state('networkidle')
        {% endif %}
        {% endfor %}
    
    async def extract_table_data(self):
        """Extract data from discovered tables."""
        {% for table in tables %}
        try:
            table_element = await self.page.query_selector('{{ table.selector }}')
            if table_element:
                headers = {{ table.headers | tojson }}
                rows = await self.page.query_selector_all('{{ table.selector }} tbody tr, {{ table.selector }} tr')
                table_data = []
                
                for row in rows:
                    cells = await row.query_selector_all('td')
                    row_data = []
                    for cell in cells:
                        cell_text = await cell.inner_text()
                        row_data.append(cell_text.strip())
                    if row_data:
                        table_data.append(row_data)
                
                print(f"Extracted table data: {len(table_data)} rows")
                
        except Exception as e:
            print(f"Table extraction error: {e}")
        {% endfor %}
    
    async def run_full_sequence(self):
        """Run complete portal interaction sequence."""
        try:
            await self.start_browser()
            print("Browser started")
            await self.login()
            print("Login completed")
            await self.extract_table_data()
            print("Data extraction completed")
            
        except Exception as e:
            print(f"Adapter execution error: {e}")
        
        finally:
            if self.browser:
                await self.browser.close()

async def main():
    """Main execution function."""
    adapter = PortalAdapter()
    await adapter.run_full_sequence()

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        # Render template
        if DEPENDENCIES_AVAILABLE:
            template = jinja2.Template(template_str)
            adapter_content = template.render(
                inspection_id=self.inspection_id,
                portal_name=self.config.portal_name,
                portal_url=self.config.portal_url,
                generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                forms=self.forms_discovered,
                tables=self.tables_discovered,
                navigation_flow=self.navigation_flow,
                api_endpoints=list(self.api_endpoints),
                popup_dialogs=self.popup_dialogs
            )
        else:
            adapter_content = f"# Adapter generation skipped due to missing jinja2 dependency\n# Inspection ID: {self.inspection_id}"
        
        # Save adapter file
        adapter_dir = self.config.output_dir / "adapters"
        adapter_dir.mkdir(parents=True, exist_ok=True)
        adapter_path = adapter_dir / f"adapter_{self.inspection_id}.py"
        
        with open(adapter_path, 'w') as f:
            f.write(adapter_content)
        
        logger.info(f"Replay adapter generated: {adapter_path}")
        return str(adapter_path)


# Flask Blueprint for Web API
def create_inspector_blueprint() -> Blueprint:
    """Create Flask blueprint for inspector API."""
    
    if not DEPENDENCIES_AVAILABLE:
        raise ImportError(f"Required dependencies not available: {import_error}")
    
    blueprint = Blueprint('inspector', __name__, url_prefix='/inspector')
    inspector_instance = None
    
    @blueprint.route('/start', methods=['POST'])
    async def start_inspection():
        """Start new inspection."""
        nonlocal inspector_instance
        
        try:
            config_data = request.get_json()
            config = InspectorConfig(**config_data)
            
            # Get SocketIO instance from app
            socketio = getattr(blueprint, 'socketio', None)
            
            inspector_instance = LivePortalInspector(config, socketio)
            inspection_id = await inspector_instance.start_inspection()
            
            return jsonify({
                'success': True,
                'inspection_id': inspection_id,
                'message': 'Inspection started successfully'
            })
            
        except Exception as e:
            logger.exception(f"Start inspection error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/stop', methods=['POST'])
    async def stop_inspection():
        """Stop current inspection."""
        nonlocal inspector_instance
        
        try:
            if not inspector_instance:
                return jsonify({
                    'success': False,
                    'error': 'No inspection in progress'
                }), 400
            
            result = await inspector_instance.stop_inspection()
            inspector_instance = None
            
            return jsonify({
                'success': True,
                'result': result
            })
            
        except Exception as e:
            logger.exception(f"Stop inspection error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/status', methods=['GET'])
    def get_status():
        """Get inspection status."""
        nonlocal inspector_instance
        
        if inspector_instance and inspector_instance.is_recording:
            return jsonify({
                'active': True,
                'inspection_id': inspector_instance.inspection_id,
                'events_count': len(inspector_instance.events),
                'portal_url': inspector_instance.config.portal_url
            })
        else:
            return jsonify({
                'active': False,
                'inspection_id': None
            })
    
    @blueprint.route('/export/<inspection_id>', methods=['GET'])
    def export_inspection(inspection_id: str):
        """Export inspection data."""
        try:
            # TODO: Implement export functionality
            # This would read the saved logs and return formatted data
            return jsonify({
                'success': True,
                'message': 'Export functionality not yet implemented'
            })
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return blueprint


# CLI Interface
def create_cli_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(description='Live Portal Inspector')
    
    parser.add_argument('--portal-url', required=True, help='Portal URL to inspect')
    parser.add_argument('--portal-name', required=True, help='Portal name')
    parser.add_argument('--recording-mode', choices=['full', 'login_only', 'navigation_only'], 
                       default='full', help='Recording mode')
    parser.add_argument('--output-dir', type=Path, default=Path('./inspector_output'), 
                       help='Output directory')
    parser.add_argument('--timeout-minutes', type=int, default=30, help='Timeout in minutes')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--encryption-key', help='Encryption key for logs')
    
    return parser


async def main_cli():
    """Main CLI function."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Create config
    config = InspectorConfig(
        portal_url=args.portal_url,
        portal_name=args.portal_name,
        recording_mode=args.recording_mode,
        output_dir=args.output_dir,
        timeout_minutes=args.timeout_minutes,
        headless=args.headless,
        encryption_key=args.encryption_key
    )
    
    # Create inspector
    inspector = LivePortalInspector(config)
    
    try:
        print(f"Starting inspection of {config.portal_url}")
        inspection_id = await inspector.start_inspection()
        print(f"Inspection started: {inspection_id}")
        
        # Wait for user input to stop
        input("Press Enter to stop inspection...")
        
        result = await inspector.stop_inspection()
        print(f"Inspection completed: {result}")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        await inspector.stop_inspection()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main_cli()) 
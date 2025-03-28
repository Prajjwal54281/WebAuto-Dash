# Universal Portal Inspector for WebAutoDash

## 🎯 Overview

The **Universal Portal Inspector** is an advanced tool that can automatically analyze any medical portal and generate custom adapter code for WebAutoDash. It goes far beyond the original MediMind debug script by providing:

- **🔍 Comprehensive Portal Analysis**: Automatically discovers login methods, patient data structures, and medical data sections
- **🤖 Auto-Generated Adapters**: Creates complete, working adapter code based on analysis
- **📊 Detailed Reports**: Provides JSON reports with all findings and recommendations
- **⚙️ Configurable Inspection**: Supports custom portal configurations and login methods
- **🔧 Multiple Output Formats**: Generates Python adapters, YAML configs, and analysis reports

## 🚀 Quick Start

### Method 1: Interactive Mode (Easiest)
```bash
python universal_portal_inspector.py
```
The tool will prompt you for:
- Portal name
- Portal URL
- Username/Password
- Optional custom login URL

### Method 2: Configuration File Mode (Recommended)
1. Copy the template configuration:
```bash
cp portal_config_template.yaml my_portal_config.yaml
```

2. Edit `my_portal_config.yaml` with your portal details:
```yaml
portal_name: "My Hospital Portal"
url: "https://portal.myhospital.com"
username: "your_username"
password: "your_password"
```

3. Run the inspector:
```bash
python universal_portal_inspector.py my_portal_config.yaml
```

## 📋 Configuration Options

### Basic Configuration
```yaml
portal_name: "Portal Name"           # Required: Display name for the portal
url: "https://portal.example.com"    # Required: Portal base URL
username: "your_username"            # Required: Login username
password: "your_password"            # Required: Login password
login_url: "https://portal.example.com/login"  # Optional: Custom login URL
```

### Advanced Login Selectors
If auto-discovery fails, you can specify custom selectors:
```yaml
login_selectors:
  username_field: "#email"          # Custom username field selector
  password_field: "[name='pwd']"    # Custom password field selector
  submit_button: ".login-btn"       # Custom submit button selector
```

### Portal Settings
```yaml
settings:
  headless: false                   # Run browser visually (true for headless)
  slow_mo: 1000                    # Slow down actions (milliseconds)
  timeout: 15000                   # Login timeout (milliseconds)
```

## 🔍 What Gets Analyzed

### 1. Login Page Analysis
- **Auto-discovers login form elements**
- **Tests common username/password field patterns**
- **Identifies submit buttons**
- **Saves login page screenshot and HTML**

### 2. Dashboard Analysis
- **Maps navigation structure**
- **Analyzes all tables for patient data**
- **Discovers patient access links**
- **Identifies content sections**

### 3. Patient Data Structure
- **Tests 13+ different patient row selectors**
- **Analyzes table headers and data**
- **Extracts sample patient information**
- **Recommends best selectors for patient rows**

### 4. Medical Data Analysis
- **Navigates to patient detail pages**
- **Scans for 10 medical data categories**:
  - Medications
  - Allergies
  - Lab Results
  - Problems/Diagnoses
  - Appointments
  - Procedures
  - Immunizations
  - Imaging
  - Vitals
  - Clinical Notes
- **Tests 20+ selectors per category**
- **Extracts sample content**

### 5. Navigation Pattern Analysis
- **Identifies tabs, menus, sidebars**
- **Maps portal flow and structure**
- **Detects navigation requirements**

## 📁 Generated Output Files

After inspection, you'll get these files:

### 1. `{portal_name}_analysis_report.json`
Complete analysis report with:
- Login page structure
- Dashboard analysis
- Patient data findings
- Medical section discoveries
- Navigation patterns
- Adapter recommendations

### 2. `{portal_name}_adapter.py`
Ready-to-use adapter code with:
- Auto-discovered selectors
- Login method
- Patient list extraction
- Medical data extraction
- Error handling

### 3. `{portal_name}_config.yaml`
Configuration summary with:
- Working selectors
- Portal characteristics
- Implementation notes

### 4. Debug Files
- `portal_screenshots/` - Visual captures of each step
- `portal_html/` - HTML snapshots for analysis
- `portal_inspection.log` - Detailed operation log

## 🛠️ Using Generated Adapters

### 1. Add to WebAutoDash
```bash
# Copy the generated adapter to your portal_adapters directory
cp my_portal_adapter.py portal_adapters/

# Update the adapter to inherit from BaseAdapter if needed
```

### 2. Test the Adapter
```python
from portal_adapters.my_portal_adapter import MyPortalAdapter

adapter = MyPortalAdapter()
# Test with your portal credentials
```

### 3. Integrate with WebAutoDash
Add your portal to the main configuration and test extraction jobs.

## 🔧 Advanced Usage

### Custom Analysis for Complex Portals

For portals with complex authentication or unusual structures:

1. **Two-Factor Authentication**: 
   - Run initial analysis to login page
   - Manually handle 2FA
   - Resume analysis from dashboard

2. **Multi-Step Login**:
   - Configure intermediate URLs
   - Use custom selectors for each step

3. **Dynamic Content**:
   - Increase timeout values
   - Add wait conditions for specific elements

### Batch Portal Analysis

Analyze multiple portals:
```bash
# Create configs for each portal
python universal_portal_inspector.py portal1_config.yaml
python universal_portal_inspector.py portal2_config.yaml
python universal_portal_inspector.py portal3_config.yaml
```

### Continuous Monitoring

Use the inspector to monitor portal changes:
```bash
# Schedule regular analysis to detect UI changes
crontab -e
# Add: 0 2 * * 0 python /path/to/universal_portal_inspector.py config.yaml
```

## 🚨 Troubleshooting

### Common Issues

#### Login Fails
- ✅ Check credentials are correct
- ✅ Verify portal URL is accessible
- ✅ Check if portal requires VPN
- ✅ Try custom login selectors
- ✅ Check for CAPTCHA or 2FA requirements

#### No Patient Data Found
- ✅ Verify user has patient access permissions
- ✅ Check if patients exist in test environment
- ✅ Look for "load more" buttons or pagination
- ✅ Check manual browser navigation

#### Selector Discovery Fails
- ✅ Increase timeout values
- ✅ Check generated HTML files for actual structure
- ✅ Use browser developer tools to find correct selectors
- ✅ Manual review of screenshots

#### Browser Issues
- ✅ Install required dependencies: `pip install playwright pyyaml`
- ✅ Install browser: `playwright install chromium`
- ✅ Check X11 forwarding for remote systems

### Debug Mode

Enable verbose logging:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Manual Review

Always review generated files:
1. Check `portal_screenshots/` for visual confirmation
2. Review `portal_html/` files for structure
3. Validate selectors in `_analysis_report.json`
4. Test generated adapter code manually

## 🎯 Portal-Specific Examples

### Epic MyChart Portals
```yaml
portal_name: "Epic MyChart"
url: "https://mychart.hospital.org"
login_selectors:
  username_field: "#Login"
  password_field: "#Password"
  submit_button: "#loginbutton"
```

### Cerner PowerChart Portals
```yaml
portal_name: "Cerner PowerChart"
url: "https://powerchart.hospital.org"
portal_characteristics:
  uses_tabs: true
  patient_access_method: "navigate"
```

### Custom Hospital Portals
```yaml
portal_name: "Custom Portal"
url: "https://portal.hospital.com"
settings:
  slow_mo: 2000  # Slower for complex JS
  timeout: 30000 # Longer timeout
```

## 🔐 Security Considerations

- **Credentials**: Never commit config files with real credentials
- **Screenshots**: Review screenshots before sharing (may contain PHI)
- **HTML Files**: Sanitize HTML dumps if they contain patient data
- **Network**: Use VPN if required by portal
- **Compliance**: Ensure portal analysis complies with your organization's policies

## 🆘 Getting Help

1. **Check the logs**: `portal_inspection.log` contains detailed information
2. **Review screenshots**: Visual confirmation of each step
3. **Analyze HTML files**: Raw portal structure for manual selector discovery
4. **Test selectors manually**: Use browser developer tools
5. **Contact support**: Include analysis report and logs

## 🚀 Next Steps

After successful portal analysis:

1. **Validate the generated adapter** with test credentials
2. **Customize medical data extraction** based on your needs
3. **Add error handling** for portal-specific edge cases
4. **Integrate with WebAutoDash** main application
5. **Schedule regular testing** to catch portal changes

The Universal Portal Inspector transforms the complex task of portal analysis from days of manual work to an automated process that completes in minutes, giving you production-ready adapter code and comprehensive documentation. 
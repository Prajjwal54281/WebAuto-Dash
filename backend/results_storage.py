"""
Results Storage Utility for WebAutoDash
Handles saving extraction results with proper naming convention and directory structure
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ResultsStorage:
    def __init__(self, base_results_dir: str = "Projects/WebAutoDash/Results"):
        """
        Initialize ResultsStorage with base directory
        
        Args:
            base_results_dir: Base directory for storing results
        """
        self.base_results_dir = base_results_dir
        self.ensure_results_directory()
    
    def ensure_results_directory(self):
        """Ensure the results directory exists"""
        try:
            os.makedirs(self.base_results_dir, exist_ok=True)
            logger.info(f"Results directory ensured: {self.base_results_dir}")
        except Exception as e:
            logger.error(f"Failed to create results directory: {e}")
            raise
    
    def ensure_provider_directory(self, provider_name: str) -> str:
        """
        Ensure the provider-specific directory exists
        
        Args:
            provider_name: Name of the provider (doctor)
            
        Returns:
            Path to the provider directory
        """
        try:
            sanitized_provider = self.sanitize_filename_component(provider_name)
            provider_dir = os.path.join(self.base_results_dir, sanitized_provider)
            os.makedirs(provider_dir, exist_ok=True)
            logger.info(f"Provider directory ensured: {provider_dir}")
            return provider_dir
        except Exception as e:
            logger.error(f"Failed to create provider directory for {provider_name}: {e}")
            raise
    
    def sanitize_filename_component(self, component: str) -> str:
        """
        Sanitize a component for use in filename
        
        Args:
            component: String to sanitize
            
        Returns:
            Sanitized string safe for filename use
        """
        if not component:
            return "unknown"
        
        # Remove/replace invalid characters
        sanitized = re.sub(r'[^\w\-_.]', '_', component.lower())
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        return sanitized if sanitized else "unknown"
    
    def generate_filename(self, job_data: Dict[str, Any], provider_dir: str) -> str:
        """
        Generate filename using the specified convention:
        {provider_name}_{portal_name}_{mode}_{date}_{count}.json
        
        Args:
            job_data: Job data containing necessary information
            provider_dir: Directory path for the provider
            
        Returns:
            Generated filename
        """
        # Extract components
        doctor_name = job_data.get('doctor_name', 'unknown_provider')
        adapter_name = job_data.get('adapter_name', 'unknown_portal')
        extraction_mode = job_data.get('extraction_mode', 'unknown_mode')
        
        # Sanitize components
        provider_name = self.sanitize_filename_component(doctor_name)
        portal_name = self.sanitize_filename_component(adapter_name)
        mode = self.sanitize_filename_component(extraction_mode.lower())
        
        # Generate date string
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Generate base filename without count
        base_filename = f"{provider_name}_{portal_name}_{mode}_{date_str}"
        
        # Find next available count
        count = 1
        while True:
            filename = f"{base_filename}_{count:03d}.json"
            filepath = os.path.join(provider_dir, filename)
            
            if not os.path.exists(filepath):
                break
            
            count += 1
            
            # Safety check to prevent infinite loop
            if count > 999:
                filename = f"{base_filename}_{datetime.now().strftime('%H%M%S')}.json"
                break
        
        return filename
    
    def save_results(self, job_data: Dict[str, Any], extraction_results: Dict[str, Any]) -> str:
        """
        Save extraction results to a JSON file with proper naming convention
        in a provider-specific subfolder
        
        Args:
            job_data: Job data for filename generation
            extraction_results: The actual extraction results to save
            
        Returns:
            Full path to the saved file
        """
        try:
            # Get provider name and ensure provider directory exists
            doctor_name = job_data.get('doctor_name', 'unknown_provider')
            provider_dir = self.ensure_provider_directory(doctor_name)
            
            # Generate filename
            filename = self.generate_filename(job_data, provider_dir)
            filepath = os.path.join(provider_dir, filename)
            
            # Prepare results data with metadata
            results_with_metadata = {
                'extraction_metadata': {
                    'job_id': job_data.get('id'),
                    'job_name': job_data.get('job_name'),
                    'extraction_mode': job_data.get('extraction_mode'),
                    'provider_name': job_data.get('doctor_name'),
                    'portal_name': job_data.get('adapter_name'),
                    'target_url': job_data.get('target_url'),
                    'patient_identifier': job_data.get('input_patient_identifier'),
                    'medication': job_data.get('medication'),
                    'start_date': job_data.get('start_date'),
                    'end_date': job_data.get('end_date'),
                    'extracted_at': datetime.now().isoformat(),
                    'results_filename': filename,
                    'provider_directory': os.path.basename(provider_dir)
                },
                'extraction_results': extraction_results
            }
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results_with_metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved successfully: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
    
    def load_results(self, filepath: str) -> Dict[str, Any]:
        """
        Load results from a JSON file
        
        Args:
            filepath: Path to the results file
            
        Returns:
            Loaded results data
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load results from {filepath}: {e}")
            raise
    
    def list_results_files(self, provider_name: Optional[str] = None) -> list:
        """
        List all results files in the results directory or a specific provider directory
        
        Args:
            provider_name: Optional provider name to filter results
            
        Returns:
            List of results filenames with their provider paths
        """
        try:
            if not os.path.exists(self.base_results_dir):
                return []
            
            files = []
            
            if provider_name:
                # List files for specific provider
                sanitized_provider = self.sanitize_filename_component(provider_name)
                provider_dir = os.path.join(self.base_results_dir, sanitized_provider)
                
                if os.path.exists(provider_dir):
                    for filename in os.listdir(provider_dir):
                        if filename.endswith('.json'):
                            files.append({
                                'filename': filename,
                                'provider': sanitized_provider,
                                'full_path': os.path.join(provider_dir, filename)
                            })
            else:
                # List files from all providers
                for item in os.listdir(self.base_results_dir):
                    item_path = os.path.join(self.base_results_dir, item)
                    
                    if os.path.isdir(item_path):
                        # This is a provider directory
                        for filename in os.listdir(item_path):
                            if filename.endswith('.json'):
                                files.append({
                                    'filename': filename,
                                    'provider': item,
                                    'full_path': os.path.join(item_path, filename)
                                })
                    elif item.endswith('.json'):
                        # Legacy file in root directory
                        files.append({
                            'filename': item,
                            'provider': 'root',
                            'full_path': os.path.join(self.base_results_dir, item)
                        })
            
            # Sort by modification time (most recent first)
            files.sort(key=lambda x: os.path.getmtime(x['full_path']), reverse=True)
            return files
            
        except Exception as e:
            logger.error(f"Failed to list results files: {e}")
            return []
    
    def list_providers(self) -> list:
        """
        List all provider directories
        
        Returns:
            List of provider names
        """
        try:
            if not os.path.exists(self.base_results_dir):
                return []
            
            providers = []
            for item in os.listdir(self.base_results_dir):
                item_path = os.path.join(self.base_results_dir, item)
                if os.path.isdir(item_path):
                    providers.append(item)
            
            return sorted(providers)
            
        except Exception as e:
            logger.error(f"Failed to list providers: {e}")
            return []
    
    def get_results_summary(self) -> Dict[str, Any]:
        """
        Get summary information about stored results
        
        Returns:
            Summary of results storage
        """
        try:
            all_files = self.list_results_files()
            providers = self.list_providers()
            
            # Group files by provider
            provider_counts = {}
            for file_info in all_files:
                provider = file_info['provider']
                provider_counts[provider] = provider_counts.get(provider, 0) + 1
            
            summary = {
                'total_results_files': len(all_files),
                'total_providers': len(providers),
                'results_directory': self.base_results_dir,
                'providers': providers,
                'provider_file_counts': provider_counts,
                'latest_results': all_files[:5] if all_files else [],  # Latest 5 files
                'storage_info': {
                    'directory_exists': os.path.exists(self.base_results_dir),
                    'is_writable': os.access(self.base_results_dir, os.W_OK) if os.path.exists(self.base_results_dir) else False
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get results summary: {e}")
            return {
                'error': str(e),
                'total_results_files': 0,
                'results_directory': self.base_results_dir
            }

# Global instance - Use absolute path to avoid working directory issues
# Get the actual project root by going up from backend/ to WebAutoDash/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results_storage = ResultsStorage(
    base_results_dir=os.path.join(project_root, "Results")
) 
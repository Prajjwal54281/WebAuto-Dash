import React, { useState, useEffect } from 'react';
import { jobsApi, clearApiCache } from '../services/api';
import Select from 'react-select';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';
import toast from 'react-hot-toast';
import {
    UserGroupIcon,
    CalendarIcon,
    DocumentTextIcon,
    ExclamationTriangleIcon,
    MagnifyingGlassIcon,
    ArrowDownTrayIcon,
    EyeIcon,
    ClockIcon,
    FunnelIcon,
    DocumentIcon,
    TableCellsIcon,
    ArrowUpIcon,
    ArrowDownIcon,
    AdjustmentsHorizontalIcon,
    ArrowPathIcon,
    ChevronDownIcon,
    ChevronUpIcon,
    HeartIcon,
    BeakerIcon,
    ExclamationCircleIcon,
    XMarkIcon
} from '@heroicons/react/24/outline';

const PatientData = () => {
    const [completedJobs, setCompletedJobs] = useState([]);
    const [selectedJob, setSelectedJob] = useState(null);
    const [patientData, setPatientData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [expandedLabResults, setExpandedLabResults] = useState({});

    // Enhanced expand/collapse state for comprehensive data display
    const [expandedSections, setExpandedSections] = useState({});
    const [expandedPatients, setExpandedPatients] = useState({});

    // Helper function to extract health concern text safely
    const getHealthConcernText = (concern) => {
        // Try multiple text fields
        if (concern.concern_text) return concern.concern_text;
        if (concern.name) return concern.name;
        if (concern.description) return concern.description;
        if (concern.note_text) return concern.note_text; // For health_concern_note type
        if (concern.text) return concern.text;
        if (concern.content) return concern.content;

        // If it's a health concern note object, extract the note_text
        if (concern.type === 'health_concern_note' && concern.note_text) {
            return concern.note_text;
        }

        // Last resort - return a generic message instead of JSON
        return 'Health Concern (details not available)';
    };

    // Patient removal state management
    const [removedPatients, setRemovedPatients] = useState(new Set());

    // Enhanced filtering and sorting states - Set PRN as default
    const [sortBy, setSortBy] = useState('mrn'); // mrn field but displays as PRN
    const [sortOrder, setSortOrder] = useState('asc'); // asc, desc
    const [filterCriteria, setFilterCriteria] = useState({
        gender: '',
        ageRange: '',
        hasLabResults: '',
        hasMedications: '',
        hasAllergies: ''
    });
    const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

    // PDF export loading state
    const [pdfExporting, setPdfExporting] = useState(false);

    // Filter options for dropdowns
    const genderOptions = [
        { value: '', label: 'All Genders' },
        { value: 'Male', label: 'Male' },
        { value: 'Female', label: 'Female' },
        { value: 'Other', label: 'Other' }
    ];

    const ageRangeOptions = [
        { value: '', label: 'All Ages' },
        { value: '0-18', label: '0-18 years' },
        { value: '19-30', label: '19-30 years' },
        { value: '31-50', label: '31-50 years' },
        { value: '51-70', label: '51-70 years' },
        { value: '70+', label: '70+ years' }
    ];

    const sortOptions = [
        { value: 'mrn', label: 'PRN (Default)' }, // PRN display but mrn value
        { value: 'name', label: 'Name (A-Z)' },
        { value: 'dob', label: 'Date of Birth' },
        { value: 'gender', label: 'Gender' },
        { value: 'created', label: 'Recently Added' }
    ];

    // Patient removal function using original index for reliable tracking
    const removePatient = (originalIndex) => {
        setRemovedPatients(prev => new Set([...prev, originalIndex]));
    };

    // Restore all removed patients function
    const restoreAllPatients = () => {
        setRemovedPatients(new Set());
    };

    useEffect(() => {
        fetchCompletedJobs();
    }, []);

    const fetchCompletedJobs = async () => {
        try {
            const response = await jobsApi.getAll(1, 100);
            const jobs = response.data.jobs || [];
            const completed = jobs.filter(job =>
                job.status === 'COMPLETED' && job.extracted_data
            );
            setCompletedJobs(completed);

            // Auto-select the most recent job if available
            if (completed.length > 0) {
                selectJob(completed[0]);
            }
        } catch (error) {
            console.error('Failed to fetch completed jobs:', error);
        } finally {
            setLoading(false);
        }
    };

    // Enhanced data processing function for comprehensive data extraction
    const processPatientData = (jobData) => {
        // Extract from either extraction_results or extracted_data (backward compatibility)
        const results = jobData.extraction_results || jobData.extracted_data || [];
        console.log('🔍 Processing comprehensive patient data:', results);

        return results.map((patient, originalIndex) => {
            const processed = { ...patient };
            processed._originalIndex = originalIndex; // Add unique identifier for reliable removal

            // Extract demographics with comprehensive handling
            if (patient.demographics_printable) {
                processed.demographics = {
                    name: patient.demographics_printable.patient_name,
                    date_of_birth: patient.demographics_printable.date_of_birth,
                    age: patient.demographics_printable.age,
                    gender: patient.demographics_printable.gender,
                    mrn: patient.demographics_printable.prn,
                    patient_name: patient.demographics_printable.patient_name,
                    ...patient.demographics_printable
                };
            }

            // Ensure patient name is available
            if (!processed.name && !processed.demographics?.name) {
                if (processed.patient_name) {
                    processed.name = processed.patient_name;
                }
            }

            // Extract comprehensive medication data
            processed.allMedications = patient.all_medications || [];
            processed.currentMedications = patient.current_medications || [];
            processed.historicalMedications = patient.historical_medications || [];

            // Extract comprehensive diagnosis data
            processed.allDiagnoses = patient.all_diagnoses || [];
            processed.currentDiagnoses = patient.current_diagnoses || [];
            processed.historicalDiagnoses = patient.historical_diagnoses || [];

            // Extract comprehensive health concerns data
            processed.allHealthConcerns = patient.all_health_concerns || [];
            processed.healthConcernNotes = patient.health_concern_notes || [];
            processed.activeHealthConcerns = patient.active_health_concerns || [];
            processed.inactiveHealthConcerns = patient.inactive_health_concerns || [];

            // Extract comprehensive allergies data
            processed.allAllergies = patient.all_allergies || [];
            processed.drugAllergies = patient.drug_allergies || [];
            processed.foodAllergies = patient.food_allergies || [];
            processed.environmentalAllergies = patient.environmental_allergies || [];

            // Extract extraction summary information
            processed.extractionSummary = patient.extraction_summary || {
                total_medications: processed.allMedications.length,
                total_diagnoses: processed.allDiagnoses.length,
                total_health_concerns: processed.allHealthConcerns.length,
                total_allergies: processed.allAllergies.length,
                parameters_used: patient.filter_criteria || {}
            };

            // Legacy compatibility for existing medications/diagnoses fields
            if (!processed.medications && processed.currentMedications) {
                processed.medications = processed.currentMedications.map(med => ({
                    name: med.medication_name,
                    medication: med.medication_name,
                    dosage: med.sig,
                    dose: med.sig,
                    dates: med.dates,
                    diagnosis: med.diagnosis,
                    type: 'current'
                }));
            }

            if (!processed.diagnoses && processed.currentDiagnoses) {
                processed.diagnoses = processed.currentDiagnoses;
            }

            console.log('📋 Processed comprehensive patient data:', processed.name || processed.patient_name, processed);
            return processed;
        });
    };

    const selectJob = (job) => {
        setSelectedJob(job);
        try {
            const extractedData = job.extracted_data; // Already parsed by API
            console.log('🔍 PatientData: Processing extracted data:', extractedData);

            // Handle multiple possible data structures
            let patients = [];

            if (Array.isArray(extractedData)) {
                // Direct array of patients (old format)
                patients = extractedData;
            } else if (extractedData && extractedData.extraction_results) {
                // New format with extraction_results array
                patients = extractedData.extraction_results;
                console.log('📋 PatientData: Found extraction_results format with', patients.length, 'patients');
            } else if (extractedData && extractedData.patients) {
                // Object with patients property
                patients = extractedData.patients;
            } else if (extractedData && typeof extractedData === 'object') {
                // Single patient object
                patients = [extractedData];
            }

            // Use enhanced data processing function
            const normalizedPatients = processPatientData({ extraction_results: patients });

            console.log('📋 PatientData: Setting', normalizedPatients.length, 'patients');
            setPatientData(normalizedPatients);
        } catch (error) {
            console.error('Error processing patient data:', error);
            setPatientData([]);
        }
    };

    // Enhanced section toggle function for patient cards
    const toggleSection = (patientId, sectionName) => {
        setExpandedSections(prev => ({
            ...prev,
            [`${patientId}-${sectionName}`]: !prev[`${patientId}-${sectionName}`]
        }));
    };

    // Check if section is expanded
    const isSectionExpanded = (patientId, sectionName) => {
        return expandedSections[`${patientId}-${sectionName}`] || false;
    };

    const handleViewLabResult = (lab, patientIndex, labIndex) => {
        const expandKey = `${patientIndex}-${labIndex}`;
        setExpandedLabResults(prev => ({
            ...prev,
            [expandKey]: !prev[expandKey]
        }));
    };

    const handleDownloadLabResult = async (lab) => {
        try {
            if (lab.document_url || lab.pdf_url || lab.file_url) {
                const url = lab.document_url || lab.pdf_url || lab.file_url;
                const link = document.createElement('a');
                link.href = url;
                link.download = `lab_result_${lab.test_name}_${lab.date}.pdf`;
                link.target = '_blank';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                // Create a simple PDF with lab results if no document URL
                const doc = new jsPDF();
                doc.setFontSize(16);
                doc.text(`Lab Result: ${lab.test_name}`, 20, 20);
                doc.setFontSize(12);
                doc.text(`Date: ${lab.date}`, 20, 35);

                let yPosition = 50;
                doc.text('Results:', 20, yPosition);
                yPosition += 15;

                Object.entries(lab.results || {}).forEach(([key, value]) => {
                    doc.text(`${key}: ${value}`, 25, yPosition);
                    yPosition += 10;
                });

                if (lab.reference_range) {
                    yPosition += 10;
                    doc.text(`Reference Range: ${lab.reference_range}`, 20, yPosition);
                }

                doc.save(`lab_result_${lab.test_name}_${lab.date}.pdf`);
            }
        } catch (error) {
            console.error('Error downloading lab result:', error);
            alert('Failed to download lab result. Please try again.');
        }
    };

    // Enhanced PDF export with proper autoTable implementation
    const exportToPDF = async () => {
        if (pdfExporting) return; // Prevent multiple simultaneous exports

        try {
            setPdfExporting(true);
            toast.loading('Generating PDF report...', { id: 'pdf-export' });

            // Small delay to allow UI to update
            await new Promise(resolve => setTimeout(resolve, 100));

            const doc = new jsPDF();

            // COMPREHENSIVE DEBUGGING - Log complete selectedJob structure
            console.log('🔍 DEBUG: Complete selectedJob object:', selectedJob);
            console.log('🔍 DEBUG: Job extraction_parameters:', selectedJob?.extraction_parameters);
            console.log('🔍 DEBUG: All job properties:', Object.keys(selectedJob || {}));
            console.log('🔍 DEBUG: Job doctor_name:', selectedJob?.doctor_name);
            console.log('🔍 DEBUG: Job medication:', selectedJob?.medication);
            console.log('🔍 DEBUG: Job start_date:', selectedJob?.start_date);
            console.log('🔍 DEBUG: Job end_date:', selectedJob?.end_date);
            console.log('🔍 DEBUG: Job provider_name:', selectedJob?.provider_name);
            console.log('🔍 DEBUG: Job filter_medication:', selectedJob?.filter_medication);

            // Test basic PDF functionality
            console.log('📄 Starting PDF generation...');
            console.log('autoTable available:', typeof autoTable === 'function');

            let yPosition = 20;

            // SIMPLIFIED EXTRACTION INFORMATION SECTION (Start directly, no header)
            // Fix data extraction - check multiple possible locations
            const extractionParams = selectedJob.extraction_parameters || selectedJob.parameters || {};

            // Provider/Doctor name - check multiple possible fields (UPPERCASE FOR PDF)
            const providerRaw = selectedJob.doctor_name ||
                extractionParams.doctor_name ||
                selectedJob.provider_name ||
                extractionParams.provider_name ||
                selectedJob.doctorName ||
                'N/A';
            const provider = providerRaw.toUpperCase();

            // Medication - check multiple possible fields  
            const medicine = selectedJob.medication ||
                extractionParams.medication ||
                selectedJob.filter_medication ||
                extractionParams.filter_medication ||
                selectedJob.med_name ||
                'N/A';

            // Date range - check multiple possible fields
            const startDate = selectedJob.start_date ||
                extractionParams.start_date ||
                selectedJob.date_from ||
                extractionParams.date_from ||
                '';

            const endDate = selectedJob.end_date ||
                extractionParams.end_date ||
                extractionParams.stop_date ||
                selectedJob.date_to ||
                extractionParams.date_to ||
                '';

            const dateRange = startDate && endDate ? `${startDate} to ${endDate}` :
                startDate ? `From ${startDate}` :
                    endDate ? `Until ${endDate}` :
                        'No date filter';

            // CLEAN EXTRACTION INFORMATION - SIMPLE BLACK & WHITE DESIGN
            doc.setTextColor(0, 0, 0);
            doc.setFontSize(16);
            doc.setFont("helvetica", "bold");
            doc.text("EXTRACTION INFORMATION", 20, yPosition);
            yPosition += 12;

            // Clean, simple layout
            doc.setFontSize(10);
            doc.setFont("helvetica", "normal");
            doc.text(`Provider: ${provider}`, 20, yPosition);
            doc.text(`Generated: ${new Date().toLocaleDateString()}`, 120, yPosition);
            yPosition += 6;
            doc.text(`Medication Filter: ${medicine}`, 20, yPosition);
            doc.text(`Total Patients: ${visiblePatients.length}`, 120, yPosition);
            yPosition += 6;
            doc.text(`Date Range: ${dateRange}`, 20, yPosition);
            yPosition += 15;

            // Patient Data Section
            visiblePatients.forEach((patient, index) => {
                // Check for page break
                if (yPosition > 250) {
                    doc.addPage();
                    yPosition = 20;
                }

                // Simple Patient Header - No background colors for performance
                doc.setTextColor(0, 0, 0);
                doc.setFontSize(14);
                doc.setFont("helvetica", "bold");
                doc.text(`PATIENT ${index + 1}: ${patient.demographics?.name || patient.name || 'Unknown'}`, 20, yPosition);
                yPosition += 12;

                // Demographics Table
                const demographicsData = [
                    ['PRN', patient.demographics?.mrn || 'N/A'],
                    ['Date of Birth', patient.demographics?.date_of_birth || 'N/A'],
                    ['Age', patient.demographics?.age || 'N/A'],
                    ['Gender', patient.demographics?.gender || 'N/A']
                ];

                autoTable(doc, {
                    startY: yPosition,
                    head: [['Field', 'Value']],
                    body: demographicsData,
                    theme: 'grid',
                    headStyles: { fillColor: [220, 220, 220], textColor: [0, 0, 0] },
                    styles: { fontSize: 9 },
                    margin: { left: 20, right: 20 }
                });

                yPosition = doc.lastAutoTable.finalY + 10;

                // Current Medications Section
                if (patient.currentMedications && patient.currentMedications.length > 0) {
                    if (yPosition > 230) {
                        doc.addPage();
                        yPosition = 20;
                    }

                    doc.setFontSize(12);
                    doc.setFont("helvetica", "bold");
                    doc.text(`Current Medications (${patient.currentMedications.length})`, 20, yPosition);
                    yPosition += 8;

                    const medicationsData = patient.currentMedications.map(med => [
                        med.medication_name || 'Unknown',
                        med.sig || 'N/A',
                        med.diagnosis || 'N/A',
                        med.dates || 'Current'
                    ]);

                    autoTable(doc, {
                        startY: yPosition,
                        head: [['Medication', 'Dosage/Sig', 'Diagnosis', 'Dates']],
                        body: medicationsData,
                        theme: 'striped',
                        headStyles: { fillColor: [220, 220, 220], textColor: [0, 0, 0] },
                        styles: { fontSize: 8 },
                        margin: { left: 20, right: 20 }
                    });

                    yPosition = doc.lastAutoTable.finalY + 10;
                }

                // Historical Medications Section
                if (patient.historicalMedications && patient.historicalMedications.length > 0) {
                    if (yPosition > 230) {
                        doc.addPage();
                        yPosition = 20;
                    }

                    doc.setFontSize(12);
                    doc.setFont("helvetica", "bold");
                    doc.text(`Historical Medications (${patient.historicalMedications.length})`, 20, yPosition);
                    yPosition += 8;

                    const historicalMedsData = patient.historicalMedications.map(med => [
                        med.medication_name || 'Unknown',
                        med.sig || 'N/A',
                        med.diagnosis || 'N/A',
                        med.dates || 'Historical'
                    ]);

                    autoTable(doc, {
                        startY: yPosition,
                        head: [['Medication', 'Dosage/Sig', 'Diagnosis', 'Dates']],
                        body: historicalMedsData,
                        theme: 'striped',
                        headStyles: { fillColor: [220, 220, 220], textColor: [0, 0, 0] },
                        styles: { fontSize: 8 },
                        margin: { left: 20, right: 20 }
                    });

                    yPosition = doc.lastAutoTable.finalY + 10;
                }

                // Current Diagnoses Section
                if (patient.currentDiagnoses && patient.currentDiagnoses.length > 0) {
                    if (yPosition > 230) {
                        doc.addPage();
                        yPosition = 20;
                    }

                    doc.setFontSize(12);
                    doc.setFont("helvetica", "bold");
                    doc.text(`Current Diagnoses (${patient.currentDiagnoses.length})`, 20, yPosition);
                    yPosition += 8;

                    const diagnosesData = patient.currentDiagnoses.map(diag => [
                        diag.diagnosis_text || 'Unknown',
                        diag.acuity || 'N/A',
                        diag.start_date || 'N/A'
                    ]);

                    autoTable(doc, {
                        startY: yPosition,
                        head: [['Diagnosis', 'Acuity', 'Start Date']],
                        body: diagnosesData,
                        theme: 'striped',
                        headStyles: { fillColor: [220, 220, 220], textColor: [0, 0, 0] },
                        styles: { fontSize: 8 },
                        margin: { left: 20, right: 20 }
                    });

                    yPosition = doc.lastAutoTable.finalY + 10;
                }

                // Health Concerns Section
                if (patient.allHealthConcerns && patient.allHealthConcerns.length > 0) {
                    if (yPosition > 230) {
                        doc.addPage();
                        yPosition = 20;
                    }

                    doc.setFontSize(12);
                    doc.setFont("helvetica", "bold");
                    doc.text(`Health Concerns (${patient.allHealthConcerns.length})`, 20, yPosition);
                    yPosition += 8;

                    const healthConcernsData = patient.allHealthConcerns.map(concern => [
                        concern.concern_text || concern.name || 'Health Concern',
                        concern.status || 'N/A',
                        concern.type || 'N/A'
                    ]);

                    autoTable(doc, {
                        startY: yPosition,
                        head: [['Concern', 'Status', 'Type']],
                        body: healthConcernsData,
                        theme: 'striped',
                        headStyles: { fillColor: [220, 220, 220], textColor: [0, 0, 0] },
                        styles: { fontSize: 8 },
                        margin: { left: 20, right: 20 }
                    });

                    yPosition = doc.lastAutoTable.finalY + 10;
                }

                // Allergies Section
                const allAllergiesArray = [
                    ...(patient.drugAllergies || []).map(a => ({ ...a, type: 'Drug' })),
                    ...(patient.foodAllergies || []).map(a => ({ ...a, type: 'Food' })),
                    ...(patient.environmentalAllergies || []).map(a => ({ ...a, type: 'Environmental' }))
                ];

                if (allAllergiesArray.length > 0) {
                    if (yPosition > 230) {
                        doc.addPage();
                        yPosition = 20;
                    }

                    doc.setFontSize(12);
                    doc.setFont("helvetica", "bold");
                    doc.text(`Allergies (${allAllergiesArray.length})`, 20, yPosition);
                    yPosition += 8;

                    const allergiesData = allAllergiesArray.map(allergy => [
                        allergy.type || 'Unknown',
                        allergy.allergen || allergy.name || 'Unknown Allergen',
                        allergy.reaction || 'N/A',
                        allergy.severity || 'N/A'
                    ]);

                    autoTable(doc, {
                        startY: yPosition,
                        head: [['Type', 'Allergen', 'Reaction', 'Severity']],
                        body: allergiesData,
                        theme: 'striped',
                        headStyles: { fillColor: [220, 220, 220], textColor: [0, 0, 0] },
                        styles: { fontSize: 8 },
                        margin: { left: 20, right: 20 }
                    });

                    yPosition = doc.lastAutoTable.finalY + 15;
                }

                // Add separator between patients
                if (index < visiblePatients.length - 1) {
                    doc.setLineWidth(0.3);
                    doc.line(20, yPosition, 190, yPosition);
                    yPosition += 10;
                }
            });

            // Save with improved filename
            const filename = `${generatePDFHeader(selectedJob).replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
            doc.save(filename);

            toast.success('PDF report generated successfully!', { id: 'pdf-export' });

        } catch (error) {
            console.error('Error exporting to PDF:', error);

            // Show fallback option to user
            toast.error(
                'PDF generation failed. Would you like to try the browser print option instead?',
                {
                    id: 'pdf-export',
                    duration: 6000,
                    action: {
                        label: 'Print Report',
                        onClick: () => {
                            toast.dismiss('pdf-export');
                            exportToPrint();
                        }
                    }
                }
            );
        } finally {
            setPdfExporting(false);
        }
    };

    // Fallback print functionality
    const exportToPrint = () => {
        try {
            // Create a new window with the patient data formatted for printing
            const printWindow = window.open('', '_blank');
            const printContent = generatePrintHTML();

            printWindow.document.write(printContent);
            printWindow.document.close();

            // Wait for content to load, then print
            printWindow.onload = () => {
                printWindow.print();
                printWindow.close();
            };

            toast.success('Print preview opened in new window');
        } catch (error) {
            console.error('Print fallback failed:', error);
            toast.error('Both PDF and print options failed. Please try refreshing the page.');
        }
    };

    // Generate HTML content for printing
    const generatePrintHTML = () => {
        // Use fixed data extraction logic
        const extractionParams = selectedJob.extraction_parameters || selectedJob.parameters || {};

        const providerRaw = selectedJob.doctor_name ||
            extractionParams.doctor_name ||
            selectedJob.provider_name ||
            extractionParams.provider_name ||
            selectedJob.doctorName ||
            'N/A';
        const provider = providerRaw.toUpperCase();

        const medicine = selectedJob.medication ||
            extractionParams.medication ||
            selectedJob.filter_medication ||
            extractionParams.filter_medication ||
            selectedJob.med_name ||
            'N/A';

        const jobTitle = generatePDFHeader(selectedJob);

        return `
            <!DOCTYPE html>
            <html>
            <head>
                <title>${jobTitle}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .header { border-bottom: 2px solid #3b82f6; padding-bottom: 10px; margin-bottom: 20px; }
                    .title { font-size: 24px; font-weight: bold; color: #1f2937; }
                    .subtitle { font-size: 14px; color: #6b7280; margin-top: 5px; }
                    .patient { margin-bottom: 30px; page-break-inside: avoid; }
                    .patient-header { background: #f3f4f6; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
                    .patient-name { font-size: 18px; font-weight: bold; color: #1f2937; }
                    .section { margin-bottom: 15px; }
                    .section-title { font-size: 14px; font-weight: bold; color: #374151; margin-bottom: 8px; }
                    table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
                    th, td { border: 1px solid #d1d5db; padding: 8px; text-align: left; }
                    th { background-color: #f9fafb; font-weight: bold; }
                    tr:nth-child(even) { background-color: #f9fafb; }
                    .no-data { color: #6b7280; font-style: italic; }
                    @media print { body { margin: 0; } .patient { page-break-inside: avoid; } }
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="title">${jobTitle}</div>
                    <div class="subtitle">
                        Provider: ${provider} | 
                        Medicine: ${medicine} | 
                        Patients: ${visiblePatients.length} | 
                        Generated: ${new Date().toLocaleString()}
                    </div>
                </div>
                
                ${visiblePatients.map((patient, index) => `
                    <div class="patient">
                        <div class="patient-header">
                            <div class="patient-name">Patient ${index + 1}: ${patient.demographics?.name || patient.name || 'Unknown'}</div>
                        </div>
                        
                        <div class="section">
                            <div class="section-title">Demographics</div>
                            <table>
                                <tr><th>PRN</th><td>${patient.demographics?.mrn || 'N/A'}</td></tr>
                                <tr><th>Date of Birth</th><td>${patient.demographics?.date_of_birth || 'N/A'}</td></tr>
                                <tr><th>Age</th><td>${patient.demographics?.age || 'N/A'}</td></tr>
                                <tr><th>Gender</th><td>${patient.demographics?.gender || 'N/A'}</td></tr>
                            </table>
                        </div>
                        
                        ${patient.currentMedications?.length > 0 ? `
                            <div class="section">
                                <div class="section-title">Current Medications (${patient.currentMedications.length})</div>
                                <table>
                                    <thead>
                                        <tr><th>Medication</th><th>Dosage/Sig</th><th>Diagnosis</th><th>Dates</th></tr>
                                    </thead>
                                    <tbody>
                                        ${patient.currentMedications.map(med => `
                                            <tr>
                                                <td>${med.medication_name || 'Unknown'}</td>
                                                <td>${med.sig || 'N/A'}</td>
                                                <td>${med.diagnosis || 'N/A'}</td>
                                                <td>${med.dates || 'Current'}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        ` : '<div class="section"><div class="section-title">Current Medications</div><div class="no-data">No current medications</div></div>'}
                        
                        ${patient.currentDiagnoses?.length > 0 ? `
                            <div class="section">
                                <div class="section-title">Current Diagnoses (${patient.currentDiagnoses.length})</div>
                                <table>
                                    <thead>
                                        <tr><th>Diagnosis</th><th>Acuity</th><th>Start Date</th></tr>
                                    </thead>
                                    <tbody>
                                        ${patient.currentDiagnoses.map(diag => `
                                            <tr>
                                                <td>${diag.diagnosis_text || 'Unknown'}</td>
                                                <td>${diag.acuity || 'N/A'}</td>
                                                <td>${diag.start_date || 'N/A'}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        ` : '<div class="section"><div class="section-title">Current Diagnoses</div><div class="no-data">No current diagnoses</div></div>'}
                    </div>
                `).join('')}
            </body>
            </html>
        `;
    };

    // Enhanced Excel export with comprehensive data using visible patients
    const exportToExcel = () => {
        try {
            const workbook = XLSX.utils.book_new();

            // Demographics Sheet
            const demographicsData = visiblePatients.map((patient, index) => ({
                'Patient #': index + 1,
                'Name': patient.demographics?.name || patient.name || 'Unknown',
                'PRN': patient.demographics?.mrn || 'N/A',
                'Date of Birth': patient.demographics?.date_of_birth || 'N/A',
                'Age': patient.demographics?.age || 'N/A',
                'Gender': patient.demographics?.gender || 'N/A',
                'Phone': patient.demographics?.phone || 'N/A',
                'Address': patient.demographics?.address || 'N/A',
                'Email': patient.demographics?.email || 'N/A'
            }));

            const demographicsSheet = XLSX.utils.json_to_sheet(demographicsData);
            XLSX.utils.book_append_sheet(workbook, demographicsSheet, 'Demographics');

            // Current Medications Sheet
            const currentMedsData = [];
            visiblePatients.forEach((patient, patientIndex) => {
                patient.currentMedications?.forEach((med, medIndex) => {
                    currentMedsData.push({
                        'Patient #': patientIndex + 1,
                        'Patient Name': patient.demographics?.name || patient.name || 'Unknown',
                        'Medication': med.medication_name,
                        'Sig/Dosage': med.sig,
                        'Dates': med.dates,
                        'Diagnosis': med.diagnosis,
                        'Extracted At': med.extracted_at
                    });
                });
            });

            if (currentMedsData.length > 0) {
                const currentMedsSheet = XLSX.utils.json_to_sheet(currentMedsData);
                XLSX.utils.book_append_sheet(workbook, currentMedsSheet, 'Current Medications');
            }

            // Historical Medications Sheet
            const historicalMedsData = [];
            visiblePatients.forEach((patient, patientIndex) => {
                patient.historicalMedications?.forEach((med, medIndex) => {
                    historicalMedsData.push({
                        'Patient #': patientIndex + 1,
                        'Patient Name': patient.demographics?.name || patient.name || 'Unknown',
                        'Medication': med.medication_name,
                        'Sig/Dosage': med.sig,
                        'Dates': med.dates,
                        'Diagnosis': med.diagnosis,
                        'Extracted At': med.extracted_at
                    });
                });
            });

            if (historicalMedsData.length > 0) {
                const historicalMedsSheet = XLSX.utils.json_to_sheet(historicalMedsData);
                XLSX.utils.book_append_sheet(workbook, historicalMedsSheet, 'Historical Medications');
            }

            // Current Diagnoses Sheet
            const currentDiagnosesData = [];
            visiblePatients.forEach((patient, patientIndex) => {
                patient.currentDiagnoses?.forEach((diag, diagIndex) => {
                    currentDiagnosesData.push({
                        'Patient #': patientIndex + 1,
                        'Patient Name': patient.demographics?.name || patient.name || 'Unknown',
                        'Diagnosis': diag.diagnosis_text,
                        'Acuity': diag.acuity,
                        'Start Date': diag.start_date,
                        'Stop Date': diag.stop_date,
                        'Extracted At': diag.extracted_at
                    });
                });
            });

            if (currentDiagnosesData.length > 0) {
                const currentDiagnosesSheet = XLSX.utils.json_to_sheet(currentDiagnosesData);
                XLSX.utils.book_append_sheet(workbook, currentDiagnosesSheet, 'Current Diagnoses');
            }

            // Historical Diagnoses Sheet
            const historicalDiagnosesData = [];
            visiblePatients.forEach((patient, patientIndex) => {
                patient.historicalDiagnoses?.forEach((diag, diagIndex) => {
                    historicalDiagnosesData.push({
                        'Patient #': patientIndex + 1,
                        'Patient Name': patient.demographics?.name || patient.name || 'Unknown',
                        'Diagnosis': diag.diagnosis_text,
                        'Acuity': diag.acuity,
                        'Start Date': diag.start_date,
                        'Stop Date': diag.stop_date,
                        'Extracted At': diag.extracted_at
                    });
                });
            });

            if (historicalDiagnosesData.length > 0) {
                const historicalDiagnosesSheet = XLSX.utils.json_to_sheet(historicalDiagnosesData);
                XLSX.utils.book_append_sheet(workbook, historicalDiagnosesSheet, 'Historical Diagnoses');
            }

            // Health Concerns Sheet
            const healthConcernsData = [];
            visiblePatients.forEach((patient, patientIndex) => {
                patient.allHealthConcerns?.forEach((concern, concernIndex) => {
                    healthConcernsData.push({
                        'Patient #': patientIndex + 1,
                        'Patient Name': patient.demographics?.name || patient.name || 'Unknown',
                        'Health Concern': concern.concern_text || concern.name || 'Health Concern',
                        'Status': concern.status,
                        'Type': concern.type,
                        'Notes': concern.notes,
                        'Extracted At': concern.extracted_at
                    });
                });
            });

            if (healthConcernsData.length > 0) {
                const healthConcernsSheet = XLSX.utils.json_to_sheet(healthConcernsData);
                XLSX.utils.book_append_sheet(workbook, healthConcernsSheet, 'Health Concerns');
            }

            // Allergies Sheet
            const allergiesData = [];
            visiblePatients.forEach((patient, patientIndex) => {
                const allAllergiesArray = [
                    ...(patient.drugAllergies || []).map(a => ({ ...a, type: 'Drug' })),
                    ...(patient.foodAllergies || []).map(a => ({ ...a, type: 'Food' })),
                    ...(patient.environmentalAllergies || []).map(a => ({ ...a, type: 'Environmental' }))
                ];

                allAllergiesArray.forEach((allergy, allergyIndex) => {
                    allergiesData.push({
                        'Patient #': patientIndex + 1,
                        'Patient Name': patient.demographics?.name || patient.name || 'Unknown',
                        'Allergy Type': allergy.type,
                        'Allergen': allergy.allergen || allergy.name || 'Unknown Allergen',
                        'Reaction': allergy.reaction || 'N/A',
                        'Severity': allergy.severity || 'N/A',
                        'Extracted At': allergy.extracted_at
                    });
                });
            });

            if (allergiesData.length > 0) {
                const allergiesSheet = XLSX.utils.json_to_sheet(allergiesData);
                XLSX.utils.book_append_sheet(workbook, allergiesSheet, 'Allergies');
            }

            // Summary Sheet
            const summaryData = visiblePatients.map((patient, index) => ({
                'Patient #': index + 1,
                'Name': patient.demographics?.name || patient.name || 'Unknown',
                'Total Medications': (patient.currentMedications?.length || 0) + (patient.historicalMedications?.length || 0),
                'Current Medications': patient.currentMedications?.length || 0,
                'Historical Medications': patient.historicalMedications?.length || 0,
                'Total Diagnoses': (patient.currentDiagnoses?.length || 0) + (patient.historicalDiagnoses?.length || 0),
                'Current Diagnoses': patient.currentDiagnoses?.length || 0,
                'Historical Diagnoses': patient.historicalDiagnoses?.length || 0,
                'Health Concerns': patient.allHealthConcerns?.length || 0,
                'Total Allergies': (patient.drugAllergies?.length || 0) + (patient.foodAllergies?.length || 0) + (patient.environmentalAllergies?.length || 0),
                'Drug Allergies': patient.drugAllergies?.length || 0,
                'Food Allergies': patient.foodAllergies?.length || 0,
                'Environmental Allergies': patient.environmentalAllergies?.length || 0
            }));

            const summarySheet = XLSX.utils.json_to_sheet(summaryData);
            XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary');

            // Save the workbook
            XLSX.writeFile(workbook, `patient_data_comprehensive_${selectedJob?.job_name || 'export'}_${new Date().toISOString().split('T')[0]}.xlsx`);
        } catch (error) {
            console.error('Error exporting to Excel:', error);
            alert('Failed to export Excel file. Please try again.');
        }
    };

    const filteredPatients = patientData.filter(patient => {
        const name = patient.demographics?.name || patient.name || '';
        const patientId = patient.patient_identifier || patient.patient_id || '';
        const dob = patient.demographics?.date_of_birth || patient.date_of_birth || '';

        return name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            patientId.toLowerCase().includes(searchTerm.toLowerCase()) ||
            dob.includes(searchTerm);
    });

    // Calculate patient age from date of birth
    const calculateAge = (dob) => {
        if (!dob) return null;
        const birthDate = new Date(dob);
        const today = new Date();
        let age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
            age--;
        }
        return age;
    };

    // Check if patient age falls within range
    const isInAgeRange = (patient, range) => {
        if (!range) return true;
        const age = calculateAge(patient.demographics?.date_of_birth || patient.date_of_birth);
        if (age === null) return true;

        switch (range) {
            case '0-18': return age >= 0 && age <= 18;
            case '19-30': return age >= 19 && age <= 30;
            case '31-50': return age >= 31 && age <= 50;
            case '51-70': return age >= 51 && age <= 70;
            case '70+': return age > 70;
            default: return true;
        }
    };

    // Enhanced filtering and sorting
    const filteredAndSortedPatients = React.useMemo(() => {
        let filtered = patientData.filter(patient => {
            // Text search
            const name = patient.demographics?.name || patient.name || '';
            const patientId = patient.patient_identifier || patient.patient_id || '';
            const prn = patient.demographics?.mrn || '';
            const dob = patient.demographics?.date_of_birth || patient.date_of_birth || '';

            const matchesSearch = searchTerm === '' ||
                name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                patientId.toLowerCase().includes(searchTerm.toLowerCase()) ||
                prn.toLowerCase().includes(searchTerm.toLowerCase()) ||
                dob.includes(searchTerm);

            if (!matchesSearch) return false;

            // Gender filter
            if (filterCriteria.gender && patient.demographics?.gender !== filterCriteria.gender) {
                return false;
            }

            // Age range filter
            if (!isInAgeRange(patient, filterCriteria.ageRange)) {
                return false;
            }

            // Has lab results filter
            if (filterCriteria.hasLabResults === 'yes' && (!patient.lab_results || patient.lab_results.length === 0)) {
                return false;
            }
            if (filterCriteria.hasLabResults === 'no' && patient.lab_results && patient.lab_results.length > 0) {
                return false;
            }

            // Has medications filter
            if (filterCriteria.hasMedications === 'yes' && (!patient.medications || patient.medications.length === 0)) {
                return false;
            }
            if (filterCriteria.hasMedications === 'no' && patient.medications && patient.medications.length > 0) {
                return false;
            }

            // Has allergies filter
            if (filterCriteria.hasAllergies === 'yes' && (!patient.allergies || patient.allergies.length === 0)) {
                return false;
            }
            if (filterCriteria.hasAllergies === 'no' && patient.allergies && patient.allergies.length > 0) {
                return false;
            }

            return true;
        });

        // Sorting
        filtered.sort((a, b) => {
            let aValue, bValue;

            switch (sortBy) {
                case 'name':
                    aValue = (a.demographics?.name || a.name || '').toLowerCase();
                    bValue = (b.demographics?.name || b.name || '').toLowerCase();
                    break;
                case 'mrn':
                    aValue = a.demographics?.mrn || a.patient_identifier || a.patient_id || '';
                    bValue = b.demographics?.mrn || b.patient_identifier || b.patient_id || '';
                    break;
                case 'dob':
                    aValue = new Date(a.demographics?.date_of_birth || a.date_of_birth || '1900-01-01');
                    bValue = new Date(b.demographics?.date_of_birth || b.date_of_birth || '1900-01-01');
                    break;
                case 'gender':
                    aValue = (a.demographics?.gender || '').toLowerCase();
                    bValue = (b.demographics?.gender || '').toLowerCase();
                    break;
                default:
                    aValue = (a.demographics?.name || a.name || '').toLowerCase();
                    bValue = (b.demographics?.name || b.name || '').toLowerCase();
            }

            if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
            if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
            return 0;
        });

        return filtered;
    }, [patientData, searchTerm, filterCriteria, sortBy, sortOrder]);

    // Get visible patients (filtered and not removed)
    const visiblePatients = React.useMemo(() => {
        return filteredAndSortedPatients.filter((patient) => !removedPatients.has(patient._originalIndex));
    }, [filteredAndSortedPatients, removedPatients]);

    // Reset filters - now resets to PRN default
    const resetFilters = () => {
        setSearchTerm('');
        setFilterCriteria({
            gender: '',
            ageRange: '',
            hasLabResults: '',
            hasMedications: '',
            hasAllergies: ''
        });
        setSortBy('mrn'); // Reset to PRN default (mrn field but displays as PRN)
        setSortOrder('asc');
    };

    // Generate PDF header with extraction information - FIXED DATA EXTRACTION
    const generatePDFHeader = (selectedJob) => {
        // Check multiple possible locations for job data
        const extractionParams = selectedJob.extraction_parameters || selectedJob.parameters || {};

        // Provider/Doctor name - check multiple possible fields
        const providerRaw = selectedJob.doctor_name ||
            extractionParams.doctor_name ||
            selectedJob.provider_name ||
            extractionParams.provider_name ||
            selectedJob.doctorName ||
            'N/A';

        // Capitalize each word in provider name
        const provider = providerRaw
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join('_');

        // Medication - check multiple possible fields
        const medicine = selectedJob.medication ||
            extractionParams.medication ||
            selectedJob.filter_medication ||
            extractionParams.filter_medication ||
            selectedJob.med_name ||
            'N/A';

        // Adapter name - capitalize
        const adapterNameRaw = selectedJob.adapter_name ||
            selectedJob.adapterName ||
            extractionParams.adapter_name ||
            'Unknown_Adapter';

        const adapterName = adapterNameRaw
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join('_');

        // Date range - check multiple possible fields
        const startDate = selectedJob.start_date ||
            extractionParams.start_date ||
            selectedJob.date_from ||
            extractionParams.date_from ||
            '';

        const endDate = selectedJob.end_date ||
            extractionParams.end_date ||
            extractionParams.stop_date ||
            selectedJob.date_to ||
            extractionParams.date_to ||
            '';

        const dateRange = startDate && endDate ? `${startDate}_to_${endDate}` :
            startDate ? `From_${startDate}` :
                endDate ? `Until_${endDate}` :
                    'No_Date_Filter';

        return `Dr_${provider}_${medicine}_${adapterName}_${dateRange}`;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="relative">
                    <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
                    <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                        <UserGroupIcon className="h-6 w-6 text-blue-500" />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6 sm:space-y-8">
            {/* Header */}
            <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Patient Data</h1>
                    <p className="mt-2 text-sm sm:text-base text-gray-600">Extracted patient records from medical portals</p>
                </div>
                {patientData.length > 0 && (
                    <div className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-3">
                        <button
                            onClick={exportToPDF}
                            disabled={pdfExporting}
                            className="inline-flex items-center justify-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {pdfExporting ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                                    Generating...
                                </>
                            ) : (
                                <>
                                    <DocumentIcon className="h-4 w-4 mr-2" />
                                    Export PDF
                                </>
                            )}
                        </button>
                        <button
                            onClick={exportToExcel}
                            className="inline-flex items-center justify-center px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors shadow-sm"
                        >
                            <TableCellsIcon className="h-4 w-4 mr-2" />
                            Export Excel
                        </button>
                        {removedPatients.size > 0 && (
                            <button
                                onClick={restoreAllPatients}
                                className="inline-flex items-center justify-center px-4 py-2 bg-orange-600 text-white text-sm font-medium rounded-lg hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 transition-colors shadow-sm"
                            >
                                <ArrowPathIcon className="h-4 w-4 mr-2" />
                                Restore {removedPatients.size} Removed
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Enhanced Filtering and Sorting Controls */}
            {patientData.length > 0 && (
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
                        {/* Sort Controls */}
                        <div className="flex flex-col sm:flex-row sm:items-center space-y-3 sm:space-y-0 sm:space-x-4">
                            <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium text-gray-700">Sort by:</span>
                                <Select
                                    value={sortOptions.find(option => option.value === sortBy)}
                                    onChange={(selected) => setSortBy(selected.value)}
                                    options={sortOptions}
                                    className="min-w-[150px]"
                                    isSearchable={false}
                                />
                                <button
                                    onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                                    className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                                    title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
                                >
                                    {sortOrder === 'asc' ? <ArrowUpIcon className="h-4 w-4" /> : <ArrowDownIcon className="h-4 w-4" />}
                                </button>
                            </div>

                            <div className="flex items-center space-x-2">
                                <span className="text-sm text-gray-500">
                                    Showing {visiblePatients.length} of {patientData.length} patients
                                    {removedPatients.size > 0 && (
                                        <span className="text-red-500 ml-1">
                                            ({removedPatients.size} removed)
                                        </span>
                                    )}
                                </span>
                            </div>
                        </div>

                        {/* Filter Toggle and Reset */}
                        <div className="flex items-center space-x-3">
                            <button
                                onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                                className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${showAdvancedFilters
                                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                                    : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                                    }`}
                            >
                                <AdjustmentsHorizontalIcon className="h-4 w-4 mr-2" />
                                Advanced Filters
                            </button>
                            <button
                                onClick={resetFilters}
                                className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                <ArrowPathIcon className="h-4 w-4 mr-2" />
                                Reset
                            </button>
                        </div>
                    </div>

                    {/* Advanced Filters */}
                    {showAdvancedFilters && (
                        <div className="mt-6 pt-6 border-t border-gray-200">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {/* Gender Filter */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Gender</label>
                                    <Select
                                        value={genderOptions.find(option => option.value === filterCriteria.gender)}
                                        onChange={(selected) => setFilterCriteria(prev => ({ ...prev, gender: selected.value }))}
                                        options={genderOptions}
                                        className="text-sm"
                                        isSearchable={false}
                                        placeholder="Select gender..."
                                    />
                                </div>

                                {/* Age Range Filter */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Age Range</label>
                                    <Select
                                        value={ageRangeOptions.find(option => option.value === filterCriteria.ageRange)}
                                        onChange={(selected) => setFilterCriteria(prev => ({ ...prev, ageRange: selected.value }))}
                                        options={ageRangeOptions}
                                        className="text-sm"
                                        isSearchable={false}
                                        placeholder="Select age range..."
                                    />
                                </div>

                                {/* Has Lab Results Filter */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Lab Results</label>
                                    <Select
                                        value={[
                                            { value: '', label: 'All Patients' },
                                            { value: 'yes', label: 'With Lab Results' },
                                            { value: 'no', label: 'Without Lab Results' }
                                        ].find(option => option.value === filterCriteria.hasLabResults)}
                                        onChange={(selected) => setFilterCriteria(prev => ({ ...prev, hasLabResults: selected.value }))}
                                        options={[
                                            { value: '', label: 'All Patients' },
                                            { value: 'yes', label: 'With Lab Results' },
                                            { value: 'no', label: 'Without Lab Results' }
                                        ]}
                                        className="text-sm"
                                        isSearchable={false}
                                        placeholder="Filter by lab results..."
                                    />
                                </div>

                                {/* Has Medications Filter */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Medications</label>
                                    <Select
                                        value={[
                                            { value: '', label: 'All Patients' },
                                            { value: 'yes', label: 'With Medications' },
                                            { value: 'no', label: 'Without Medications' }
                                        ].find(option => option.value === filterCriteria.hasMedications)}
                                        onChange={(selected) => setFilterCriteria(prev => ({ ...prev, hasMedications: selected.value }))}
                                        options={[
                                            { value: '', label: 'All Patients' },
                                            { value: 'yes', label: 'With Medications' },
                                            { value: 'no', label: 'Without Medications' }
                                        ]}
                                        className="text-sm"
                                        isSearchable={false}
                                        placeholder="Filter by medications..."
                                    />
                                </div>

                                {/* Has Allergies Filter */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Allergies</label>
                                    <Select
                                        value={[
                                            { value: '', label: 'All Patients' },
                                            { value: 'yes', label: 'With Allergies' },
                                            { value: 'no', label: 'Without Allergies' }
                                        ].find(option => option.value === filterCriteria.hasAllergies)}
                                        onChange={(selected) => setFilterCriteria(prev => ({ ...prev, hasAllergies: selected.value }))}
                                        options={[
                                            { value: '', label: 'All Patients' },
                                            { value: 'yes', label: 'With Allergies' },
                                            { value: 'no', label: 'Without Allergies' }
                                        ]}
                                        className="text-sm"
                                        isSearchable={false}
                                        placeholder="Filter by allergies..."
                                    />
                                </div>
                            </div>

                            {/* Active Filters Summary */}
                            {(filterCriteria.gender || filterCriteria.ageRange || filterCriteria.hasLabResults ||
                                filterCriteria.hasMedications || filterCriteria.hasAllergies) && (
                                    <div className="mt-4 pt-4 border-t border-gray-100">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="text-sm font-medium text-gray-700">Active filters:</span>
                                            {filterCriteria.gender && (
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                    Gender: {filterCriteria.gender}
                                                </span>
                                            )}
                                            {filterCriteria.ageRange && (
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                    Age: {filterCriteria.ageRange}
                                                </span>
                                            )}
                                            {filterCriteria.hasLabResults && (
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                                    {filterCriteria.hasLabResults === 'yes' ? 'With Lab Results' : 'Without Lab Results'}
                                                </span>
                                            )}
                                            {filterCriteria.hasMedications && (
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                                                    {filterCriteria.hasMedications === 'yes' ? 'With Medications' : 'Without Medications'}
                                                </span>
                                            )}
                                            {filterCriteria.hasAllergies && (
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                                    {filterCriteria.hasAllergies === 'yes' ? 'With Allergies' : 'Without Allergies'}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                )}
                        </div>
                    )}
                </div>
            )}

            {completedJobs.length === 0 ? (
                <div className="text-center py-12">
                    <UserGroupIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No patient data available</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        Complete an extraction job to see patient data here.
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {/* Job Selection Sidebar */}
                    <div className="lg:col-span-1">
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                            <div className="p-4 border-b border-gray-200">
                                <h3 className="text-lg font-medium text-gray-900">Extraction Jobs</h3>
                                <p className="text-sm text-gray-500">Select a completed extraction</p>
                            </div>
                            <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
                                {completedJobs.map((job) => (
                                    <button
                                        key={job.id}
                                        onClick={() => selectJob(job)}
                                        className={`w-full text-left p-3 rounded-lg border transition-colors ${selectedJob?.id === job.id
                                            ? 'border-blue-500 bg-blue-50 text-blue-700'
                                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                            }`}
                                    >
                                        <div className="font-medium text-sm">
                                            {job.job_name || `Extraction #${job.id}`}
                                        </div>
                                        <div className="text-xs text-gray-500 mt-1">
                                            {job.adapter_name || 'Unknown Portal'}
                                        </div>
                                        <div className="text-xs text-gray-500 mt-1 flex items-center">
                                            <ClockIcon className="h-3 w-3 mr-1" />
                                            {new Date(job.created_at).toLocaleDateString()}
                                        </div>
                                        <div className="text-xs text-green-600 mt-1">
                                            ✓ Completed
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Patient Data Display */}
                    <div className="lg:col-span-3">
                        {selectedJob && (
                            <>
                                {/* Search and Summary */}
                                <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
                                    <div className="p-6">
                                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4">
                                            <div>
                                                <h3 className="text-lg font-semibold text-gray-900">
                                                    {selectedJob.job_name || `Extraction #${selectedJob.id}`}
                                                </h3>
                                                <p className="text-sm text-gray-600">
                                                    {selectedJob.adapter_name} • Extracted on {new Date(selectedJob.created_at).toLocaleString()}
                                                </p>
                                            </div>
                                            <div className="mt-4 sm:mt-0 flex flex-col items-end space-y-3">
                                                <div className="text-right">
                                                    <div className="text-2xl font-bold text-blue-600">
                                                        {visiblePatients.length}
                                                    </div>
                                                    <div className="text-sm text-gray-500">
                                                        Patient{visiblePatients.length !== 1 ? 's' : ''} Shown
                                                    </div>
                                                    {visiblePatients.length !== patientData.length && (
                                                        <div className="text-xs text-gray-400 mt-1">
                                                            of {patientData.length} total {removedPatients.size > 0 && `(${removedPatients.size} removed)`}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Search */}
                                        <div className="relative">
                                            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                                            <input
                                                type="text"
                                                placeholder="Search patients by name, PRN, or date of birth..."
                                                value={searchTerm}
                                                onChange={(e) => setSearchTerm(e.target.value)}
                                                className="pl-10 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Patient Cards */}
                                {visiblePatients.length === 0 ? (
                                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
                                        <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-yellow-400" />
                                        <h3 className="mt-2 text-sm font-medium text-gray-900">
                                            {removedPatients.size > 0 ? 'All patients have been removed' :
                                                searchTerm ? 'No matching patients found' : 'No patient data in this extraction'}
                                        </h3>
                                        <p className="mt-1 text-sm text-gray-500">
                                            {removedPatients.size > 0 ? 'Use the "Restore" button to bring them back.' :
                                                searchTerm ? 'Try adjusting your search terms.' : 'The extraction may have encountered an issue.'}
                                        </p>
                                    </div>
                                ) : (
                                    <div className="grid gap-6">
                                        {visiblePatients.map((patient, index) => (
                                            <div key={index} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden relative">
                                                {/* Patient Removal Button */}
                                                <button
                                                    onClick={() => removePatient(patient._originalIndex)}
                                                    className="absolute top-4 right-4 p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-colors z-10"
                                                    title="Remove this patient from display and exports"
                                                >
                                                    <XMarkIcon className="h-5 w-5" />
                                                </button>

                                                <div className="p-6">
                                                    <div className="flex items-start">
                                                        <div className="flex items-center space-x-4">
                                                            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                                                                <UserGroupIcon className="h-6 w-6 text-blue-600" />
                                                            </div>
                                                            <div>
                                                                <h4 className="text-lg font-semibold text-gray-900">
                                                                    {patient.demographics?.name || patient.name || 'Unknown Patient'}
                                                                </h4>
                                                                <div className="flex items-center space-x-4 text-sm text-gray-500">
                                                                    <span>PRN: {patient.demographics?.mrn || patient.patient_identifier || patient.patient_id || 'N/A'}</span>
                                                                    {(patient.demographics?.date_of_birth || patient.date_of_birth) && (
                                                                        <span className="flex items-center">
                                                                            <CalendarIcon className="h-4 w-4 mr-1" />
                                                                            DOB: {patient.demographics?.date_of_birth || patient.date_of_birth}
                                                                        </span>
                                                                    )}
                                                                    {patient.demographics?.age && (
                                                                        <span>Age: {patient.demographics.age}</span>
                                                                    )}
                                                                    {patient.demographics?.gender && (
                                                                        <span>Gender: {patient.demographics.gender}</span>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Medical Information Sections */}
                                                    <div className="mt-6 space-y-6">


                                                        {/* Vitals */}
                                                        {patient.vitals && patient.vitals.length > 0 && (
                                                            <div>
                                                                <h5 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                                                                    <span className="h-4 w-4 mr-2 text-red-600">💓</span>
                                                                    Recent Vitals
                                                                </h5>
                                                                <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                                                                    {patient.vitals.slice(0, 1).map((vital, vIndex) => (
                                                                        <div key={vIndex} className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                                            <div className="text-center">
                                                                                <div className="text-xs text-gray-500">Blood Pressure</div>
                                                                                <div className="text-sm font-semibold text-gray-900">{vital.blood_pressure || 'N/A'}</div>
                                                                            </div>
                                                                            <div className="text-center">
                                                                                <div className="text-xs text-gray-500">Heart Rate</div>
                                                                                <div className="text-sm font-semibold text-gray-900">{vital.heart_rate || 'N/A'}</div>
                                                                            </div>
                                                                            <div className="text-center">
                                                                                <div className="text-xs text-gray-500">Temperature</div>
                                                                                <div className="text-sm font-semibold text-gray-900">{vital.temperature || 'N/A'}</div>
                                                                            </div>
                                                                            <div className="text-center">
                                                                                <div className="text-xs text-gray-500">Weight</div>
                                                                                <div className="text-sm font-semibold text-gray-900">{vital.weight || 'N/A'}</div>
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Current Medications */}
                                                        {patient.currentMedications && patient.currentMedications.length > 0 && (
                                                            <div className="bg-green-50 rounded-lg border border-green-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'currentMedications')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-green-600">💊</span>
                                                                            Current Medications ({patient.currentMedications.length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'currentMedications') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    <div className="mt-3 space-y-2">
                                                                        {patient.currentMedications.slice(0, isSectionExpanded(index, 'currentMedications') ? patient.currentMedications.length : 3).map((med, mIndex) => (
                                                                            <div key={mIndex} className="bg-white rounded-lg p-3 border border-green-200">
                                                                                <div className="flex justify-between items-start">
                                                                                    <div className="flex-1">
                                                                                        <div className="font-medium text-gray-900">{med.medication_name}</div>
                                                                                        <div className="text-sm text-gray-600 mt-1">{med.sig}</div>
                                                                                        {med.diagnosis && med.diagnosis !== '-' && (
                                                                                            <div className="text-xs text-green-700 mt-1 bg-green-100 px-2 py-1 rounded inline-block">
                                                                                                For: {med.diagnosis}
                                                                                            </div>
                                                                                        )}
                                                                                    </div>
                                                                                    <div className="text-xs text-gray-500 ml-4">
                                                                                        {med.dates && med.dates !== '-' ? med.dates : 'Current'}
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        ))}

                                                                        {patient.currentMedications.length > 3 && (
                                                                            <button
                                                                                onClick={() => toggleSection(index, 'currentMedications')}
                                                                                className="w-full text-sm text-green-600 hover:text-green-800 font-medium py-2 text-center border border-green-300 rounded-lg hover:bg-green-100 transition-colors"
                                                                            >
                                                                                {isSectionExpanded(index, 'currentMedications') ?
                                                                                    `Show Less (Hide ${patient.currentMedications.length - 3} medications)` :
                                                                                    `Show ${patient.currentMedications.length - 3} more medications`
                                                                                }
                                                                            </button>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Historical Medications */}
                                                        {patient.historicalMedications && patient.historicalMedications.length > 0 && (
                                                            <div className="bg-green-50 rounded-lg border border-green-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'historicalMedications')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-green-600">💊</span>
                                                                            Historical Medications ({patient.historicalMedications.length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'historicalMedications') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    {isSectionExpanded(index, 'historicalMedications') && (
                                                                        <div className="mt-3 space-y-2">
                                                                            {patient.historicalMedications.map((med, mIndex) => (
                                                                                <div key={mIndex} className="bg-white rounded-lg p-3 border border-green-200 opacity-75">
                                                                                    <div className="flex justify-between items-start">
                                                                                        <div className="flex-1">
                                                                                            <div className="font-medium text-gray-700">{med.medication_name}</div>
                                                                                            <div className="text-sm text-gray-500 mt-1">{med.sig}</div>
                                                                                            {med.diagnosis && med.diagnosis !== '-' && (
                                                                                                <div className="text-xs text-gray-600 mt-1 bg-gray-100 px-2 py-1 rounded inline-block">
                                                                                                    For: {med.diagnosis}
                                                                                                </div>
                                                                                            )}
                                                                                        </div>
                                                                                        <div className="text-xs text-gray-500 ml-4">
                                                                                            {med.dates && med.dates !== '-' ? med.dates : 'Historical'}
                                                                                        </div>
                                                                                    </div>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Fallback for legacy medications data */}
                                                        {!patient.currentMedications && patient.medications && patient.medications.length > 0 && (
                                                            <div className="bg-green-50 rounded-lg border border-green-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'medications')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-green-600">💊</span>
                                                                            Medications ({patient.medications.length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'medications') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    <div className="mt-3 space-y-2">
                                                                        {patient.medications.slice(0, isSectionExpanded(index, 'medications') ? patient.medications.length : 3).map((med, mIndex) => (
                                                                            <div key={mIndex} className="bg-white rounded-lg p-3 border border-green-200">
                                                                                <div className="flex justify-between items-start">
                                                                                    <div className="flex-1">
                                                                                        <div className="font-medium text-gray-900">{med.name || med.medication || med.medication_name}</div>
                                                                                        <div className="text-sm text-gray-600 mt-1">{med.dosage || med.dose || med.sig || 'No dosage info'}</div>
                                                                                        {med.diagnosis && med.diagnosis !== '-' && (
                                                                                            <div className="text-xs text-green-700 mt-1 bg-green-100 px-2 py-1 rounded inline-block">
                                                                                                For: {med.diagnosis}
                                                                                            </div>
                                                                                        )}
                                                                                    </div>
                                                                                    <div className="text-xs text-gray-500 ml-4">
                                                                                        {med.dates && med.dates !== '-' ? med.dates : (med.start_date ? `Since: ${med.start_date}` : 'Current')}
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        ))}

                                                                        {patient.medications.length > 3 && (
                                                                            <button
                                                                                onClick={() => toggleSection(index, 'medications')}
                                                                                className="w-full text-sm text-green-600 hover:text-green-800 font-medium py-2 text-center border border-green-300 rounded-lg hover:bg-green-100 transition-colors"
                                                                            >
                                                                                {isSectionExpanded(index, 'medications') ?
                                                                                    `Show Less (Hide ${patient.medications.length - 3} medications)` :
                                                                                    `Show ${patient.medications.length - 3} more medications`
                                                                                }
                                                                            </button>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Current Diagnoses */}
                                                        {patient.currentDiagnoses && patient.currentDiagnoses.length > 0 && (
                                                            <div className="bg-purple-50 rounded-lg border border-purple-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'currentDiagnoses')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-purple-600">🩺</span>
                                                                            Current Diagnoses ({patient.currentDiagnoses.length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'currentDiagnoses') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    <div className="mt-3 space-y-2">
                                                                        {patient.currentDiagnoses.slice(0, isSectionExpanded(index, 'currentDiagnoses') ? patient.currentDiagnoses.length : 5).map((diagnosis, dIndex) => (
                                                                            <div key={dIndex} className="bg-white rounded-lg p-3 border border-purple-200">
                                                                                <div className="flex justify-between items-start">
                                                                                    <div className="flex-1">
                                                                                        <div className="font-medium text-gray-900">{diagnosis.diagnosis_text}</div>
                                                                                        {diagnosis.acuity && diagnosis.acuity !== '' && (
                                                                                            <div className="text-sm text-purple-700 mt-1 bg-purple-100 px-2 py-1 rounded inline-block">
                                                                                                Acuity: {diagnosis.acuity}
                                                                                            </div>
                                                                                        )}
                                                                                    </div>
                                                                                    <div className="text-xs text-gray-500 ml-4">
                                                                                        {diagnosis.start_date ? `Since: ${diagnosis.start_date}` : 'Current'}
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        ))}

                                                                        {patient.currentDiagnoses.length > 5 && (
                                                                            <button
                                                                                onClick={() => toggleSection(index, 'currentDiagnoses')}
                                                                                className="w-full text-sm text-purple-600 hover:text-purple-800 font-medium py-2 text-center border border-purple-300 rounded-lg hover:bg-purple-100 transition-colors"
                                                                            >
                                                                                {isSectionExpanded(index, 'currentDiagnoses') ?
                                                                                    `Show Less (Hide ${patient.currentDiagnoses.length - 5} diagnoses)` :
                                                                                    `Show ${patient.currentDiagnoses.length - 5} more diagnoses`
                                                                                }
                                                                            </button>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Historical Diagnoses */}
                                                        {patient.historicalDiagnoses && patient.historicalDiagnoses.length > 0 && (
                                                            <div className="bg-purple-50 rounded-lg border border-purple-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'historicalDiagnoses')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-purple-600">🩺</span>
                                                                            Historical Diagnoses ({patient.historicalDiagnoses.length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'historicalDiagnoses') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    {isSectionExpanded(index, 'historicalDiagnoses') && (
                                                                        <div className="mt-3 space-y-2">
                                                                            {patient.historicalDiagnoses.map((diagnosis, dIndex) => (
                                                                                <div key={dIndex} className="bg-white rounded-lg p-3 border border-purple-200 opacity-75">
                                                                                    <div className="flex justify-between items-start">
                                                                                        <div className="flex-1">
                                                                                            <div className="font-medium text-gray-700">{diagnosis.diagnosis_text}</div>
                                                                                            {diagnosis.acuity && diagnosis.acuity !== '' && (
                                                                                                <div className="text-sm text-gray-600 mt-1 bg-gray-100 px-2 py-1 rounded inline-block">
                                                                                                    Acuity: {diagnosis.acuity}
                                                                                                </div>
                                                                                            )}
                                                                                        </div>
                                                                                        <div className="text-xs text-gray-500 ml-4">
                                                                                            {diagnosis.start_date ? `Since: ${diagnosis.start_date}` : 'Historical'}
                                                                                        </div>
                                                                                    </div>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Fallback for legacy diagnoses data */}
                                                        {!patient.currentDiagnoses && ((patient.current_diagnoses && patient.current_diagnoses.length > 0) || (patient.diagnoses && patient.diagnoses.length > 0)) && (
                                                            <div className="bg-purple-50 rounded-lg border border-purple-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'diagnoses')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-purple-600">🩺</span>
                                                                            Diagnoses ({(patient.current_diagnoses || patient.diagnoses || []).length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'diagnoses') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    <div className="mt-3 space-y-2">
                                                                        {(patient.current_diagnoses || patient.diagnoses || []).slice(0, isSectionExpanded(index, 'diagnoses') ? (patient.current_diagnoses || patient.diagnoses || []).length : 5).map((diagnosis, dIndex) => (
                                                                            <div key={dIndex} className="bg-white rounded-lg p-3 border border-purple-200">
                                                                                <div className="flex justify-between items-start">
                                                                                    <div className="flex-1">
                                                                                        <div className="font-medium text-gray-900">{diagnosis.diagnosis_text || diagnosis.condition || diagnosis.name}</div>
                                                                                        {diagnosis.acuity && diagnosis.acuity !== '' && (
                                                                                            <div className="text-sm text-purple-700 mt-1 bg-purple-100 px-2 py-1 rounded inline-block">
                                                                                                Acuity: {diagnosis.acuity}
                                                                                            </div>
                                                                                        )}
                                                                                    </div>
                                                                                    <div className="text-xs text-gray-500 ml-4">
                                                                                        {diagnosis.start_date ? `Since: ${diagnosis.start_date}` :
                                                                                            diagnosis.diagnosed_date ? `Diagnosed: ${diagnosis.diagnosed_date}` : 'Current'}
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        ))}

                                                                        {(patient.current_diagnoses || patient.diagnoses || []).length > 5 && (
                                                                            <button
                                                                                onClick={() => toggleSection(index, 'diagnoses')}
                                                                                className="w-full text-sm text-purple-600 hover:text-purple-800 font-medium py-2 text-center border border-purple-300 rounded-lg hover:bg-purple-100 transition-colors"
                                                                            >
                                                                                {isSectionExpanded(index, 'diagnoses') ?
                                                                                    `Show Less (Hide ${(patient.current_diagnoses || patient.diagnoses || []).length - 5} diagnoses)` :
                                                                                    `Show ${(patient.current_diagnoses || patient.diagnoses || []).length - 5} more diagnoses`
                                                                                }
                                                                            </button>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Health Concerns */}
                                                        {(patient.allHealthConcerns && patient.allHealthConcerns.length > 0) ||
                                                            (patient.healthConcernNotes && patient.healthConcernNotes.length > 0) ||
                                                            (patient.activeHealthConcerns && patient.activeHealthConcerns.length > 0) ||
                                                            (patient.inactiveHealthConcerns && patient.inactiveHealthConcerns.length > 0) ? (
                                                            <div className="bg-indigo-50 rounded-lg border border-indigo-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'healthConcerns')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-indigo-600">🏥</span>
                                                                            Health Concerns ({(patient.allHealthConcerns || []).length + (patient.healthConcernNotes || []).length + (patient.activeHealthConcerns || []).length + (patient.inactiveHealthConcerns || []).length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'healthConcerns') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    {isSectionExpanded(index, 'healthConcerns') && (
                                                                        <div className="mt-3 space-y-4">
                                                                            {/* Health Concern Notes */}
                                                                            {patient.healthConcernNotes && patient.healthConcernNotes.length > 0 && (
                                                                                <div>
                                                                                    <h6 className="text-sm font-medium text-indigo-700 mb-2">📝 Notes ({patient.healthConcernNotes.length})</h6>
                                                                                    <div className="space-y-2">
                                                                                        {patient.healthConcernNotes.map((note, nIndex) => (
                                                                                            <div key={nIndex} className="bg-white rounded-lg p-3 border border-indigo-200">
                                                                                                <div className="text-sm text-gray-900">{getHealthConcernText(note)}</div>
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            )}

                                                                            {/* Active Health Concerns */}
                                                                            {patient.activeHealthConcerns && patient.activeHealthConcerns.length > 0 && (
                                                                                <div>
                                                                                    <h6 className="text-sm font-medium text-indigo-700 mb-2">✅ Active Concerns ({patient.activeHealthConcerns.length})</h6>
                                                                                    <div className="space-y-2">
                                                                                        {patient.activeHealthConcerns.map((concern, cIndex) => (
                                                                                            <div key={cIndex} className="bg-white rounded-lg p-3 border border-indigo-200">
                                                                                                <div className="font-medium text-gray-900">{getHealthConcernText(concern)}</div>
                                                                                                {concern.status && (
                                                                                                    <div className="text-sm text-indigo-700 mt-1 bg-indigo-100 px-2 py-1 rounded inline-block">
                                                                                                        Status: {concern.status}
                                                                                                    </div>
                                                                                                )}
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            )}

                                                                            {/* Inactive Health Concerns */}
                                                                            {patient.inactiveHealthConcerns && patient.inactiveHealthConcerns.length > 0 && (
                                                                                <div>
                                                                                    <h6 className="text-sm font-medium text-gray-600 mb-2">⏸️ Inactive Concerns ({patient.inactiveHealthConcerns.length})</h6>
                                                                                    <div className="space-y-2">
                                                                                        {patient.inactiveHealthConcerns.map((concern, cIndex) => (
                                                                                            <div key={cIndex} className="bg-white rounded-lg p-3 border border-gray-200 opacity-75">
                                                                                                <div className="font-medium text-gray-700">{getHealthConcernText(concern)}</div>
                                                                                                {concern.status && (
                                                                                                    <div className="text-sm text-gray-600 mt-1 bg-gray-100 px-2 py-1 rounded inline-block">
                                                                                                        Status: {concern.status}
                                                                                                    </div>
                                                                                                )}
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            )}

                                                                            {/* All Health Concerns (if others are empty) */}
                                                                            {patient.allHealthConcerns && patient.allHealthConcerns.length > 0 && !patient.activeHealthConcerns?.length && !patient.inactiveHealthConcerns?.length && (
                                                                                <div>
                                                                                    <h6 className="text-sm font-medium text-indigo-700 mb-2">🏥 All Health Concerns ({patient.allHealthConcerns.length})</h6>
                                                                                    <div className="space-y-2">
                                                                                        {patient.allHealthConcerns.map((concern, cIndex) => (
                                                                                            <div key={cIndex} className="bg-white rounded-lg p-3 border border-indigo-200">
                                                                                                <div className="font-medium text-gray-900">{getHealthConcernText(concern)}</div>
                                                                                                {concern.status && (
                                                                                                    <div className="text-sm text-indigo-700 mt-1 bg-indigo-100 px-2 py-1 rounded inline-block">
                                                                                                        Status: {concern.status}
                                                                                                    </div>
                                                                                                )}
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ) : null}

                                                        {/* Comprehensive Allergies */}
                                                        {(patient.drugAllergies && patient.drugAllergies.length > 0) ||
                                                            (patient.foodAllergies && patient.foodAllergies.length > 0) ||
                                                            (patient.environmentalAllergies && patient.environmentalAllergies.length > 0) ||
                                                            (patient.allAllergies && patient.allAllergies.length > 0) ? (
                                                            <div className="bg-orange-50 rounded-lg border border-orange-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'allergies')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-orange-600">🌡️</span>
                                                                            Allergies ({(patient.drugAllergies || []).length + (patient.foodAllergies || []).length + (patient.environmentalAllergies || []).length + (patient.allAllergies || []).length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'allergies') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    {isSectionExpanded(index, 'allergies') && (
                                                                        <div className="mt-3 space-y-4">
                                                                            {/* Drug Allergies */}
                                                                            {patient.drugAllergies && patient.drugAllergies.length > 0 && (
                                                                                <div>
                                                                                    <h6 className="text-sm font-medium text-orange-700 mb-2">💊 Drug Allergies ({patient.drugAllergies.length})</h6>
                                                                                    <div className="space-y-2">
                                                                                        {patient.drugAllergies.map((allergy, aIndex) => (
                                                                                            <div key={aIndex} className="bg-white rounded-lg p-3 border border-orange-200">
                                                                                                <div className="flex justify-between items-start">
                                                                                                    <div className="flex-1">
                                                                                                        <div className="font-medium text-gray-900">{allergy.allergen || allergy.name || 'Unknown Drug Allergy'}</div>
                                                                                                        {allergy.reaction && (
                                                                                                            <div className="text-sm text-gray-600 mt-1">Reaction: {allergy.reaction}</div>
                                                                                                        )}
                                                                                                    </div>
                                                                                                    {allergy.severity && (
                                                                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ml-4 ${allergy.severity === 'Severe' ? 'bg-red-100 text-red-800' :
                                                                                                            allergy.severity === 'Moderate' ? 'bg-orange-100 text-orange-800' :
                                                                                                                'bg-yellow-100 text-yellow-800'
                                                                                                            }`}>
                                                                                                            {allergy.severity}
                                                                                                        </span>
                                                                                                    )}
                                                                                                </div>
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            )}

                                                                            {/* Food Allergies */}
                                                                            {patient.foodAllergies && patient.foodAllergies.length > 0 && (
                                                                                <div>
                                                                                    <h6 className="text-sm font-medium text-orange-700 mb-2">🍎 Food Allergies ({patient.foodAllergies.length})</h6>
                                                                                    <div className="space-y-2">
                                                                                        {patient.foodAllergies.map((allergy, aIndex) => (
                                                                                            <div key={aIndex} className="bg-white rounded-lg p-3 border border-orange-200">
                                                                                                <div className="flex justify-between items-start">
                                                                                                    <div className="flex-1">
                                                                                                        <div className="font-medium text-gray-900">{allergy.allergen || allergy.name || 'Unknown Food Allergy'}</div>
                                                                                                        {allergy.reaction && (
                                                                                                            <div className="text-sm text-gray-600 mt-1">Reaction: {allergy.reaction}</div>
                                                                                                        )}
                                                                                                    </div>
                                                                                                    {allergy.severity && (
                                                                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ml-4 ${allergy.severity === 'Severe' ? 'bg-red-100 text-red-800' :
                                                                                                            allergy.severity === 'Moderate' ? 'bg-orange-100 text-orange-800' :
                                                                                                                'bg-yellow-100 text-yellow-800'
                                                                                                            }`}>
                                                                                                            {allergy.severity}
                                                                                                        </span>
                                                                                                    )}
                                                                                                </div>
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            )}

                                                                            {/* Environmental Allergies */}
                                                                            {patient.environmentalAllergies && patient.environmentalAllergies.length > 0 && (
                                                                                <div>
                                                                                    <h6 className="text-sm font-medium text-orange-700 mb-2">🌿 Environmental Allergies ({patient.environmentalAllergies.length})</h6>
                                                                                    <div className="space-y-2">
                                                                                        {patient.environmentalAllergies.map((allergy, aIndex) => (
                                                                                            <div key={aIndex} className="bg-white rounded-lg p-3 border border-orange-200">
                                                                                                <div className="flex justify-between items-start">
                                                                                                    <div className="flex-1">
                                                                                                        <div className="font-medium text-gray-900">{allergy.allergen || allergy.name || 'Unknown Environmental Allergy'}</div>
                                                                                                        {allergy.reaction && (
                                                                                                            <div className="text-sm text-gray-600 mt-1">Reaction: {allergy.reaction}</div>
                                                                                                        )}
                                                                                                    </div>
                                                                                                    {allergy.severity && (
                                                                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ml-4 ${allergy.severity === 'Severe' ? 'bg-red-100 text-red-800' :
                                                                                                            allergy.severity === 'Moderate' ? 'bg-orange-100 text-orange-800' :
                                                                                                                'bg-yellow-100 text-yellow-800'
                                                                                                            }`}>
                                                                                                            {allergy.severity}
                                                                                                        </span>
                                                                                                    )}
                                                                                                </div>
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            )}

                                                                            {/* All Allergies (if others are empty) */}
                                                                            {patient.allAllergies && patient.allAllergies.length > 0 && !patient.drugAllergies?.length && !patient.foodAllergies?.length && !patient.environmentalAllergies?.length && (
                                                                                <div>
                                                                                    <h6 className="text-sm font-medium text-orange-700 mb-2">🌡️ All Allergies ({patient.allAllergies.length})</h6>
                                                                                    <div className="space-y-2">
                                                                                        {patient.allAllergies.map((allergy, aIndex) => (
                                                                                            <div key={aIndex} className="bg-white rounded-lg p-3 border border-orange-200">
                                                                                                <div className="flex justify-between items-start">
                                                                                                    <div className="flex-1">
                                                                                                        <div className="font-medium text-gray-900">{allergy.allergen || allergy.name || 'Unknown Allergy'}</div>
                                                                                                        {allergy.reaction && (
                                                                                                            <div className="text-sm text-gray-600 mt-1">Reaction: {allergy.reaction}</div>
                                                                                                        )}
                                                                                                    </div>
                                                                                                    {allergy.severity && (
                                                                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ml-4 ${allergy.severity === 'Severe' ? 'bg-red-100 text-red-800' :
                                                                                                            allergy.severity === 'Moderate' ? 'bg-orange-100 text-orange-800' :
                                                                                                                'bg-yellow-100 text-yellow-800'
                                                                                                            }`}>
                                                                                                            {allergy.severity}
                                                                                                        </span>
                                                                                                    )}
                                                                                                </div>
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ) : null}

                                                        {/* Fallback for legacy allergies data */}
                                                        {!patient.drugAllergies && !patient.foodAllergies && !patient.environmentalAllergies && patient.allergies && patient.allergies.length > 0 && (
                                                            <div className="bg-orange-50 rounded-lg border border-orange-200">
                                                                <div className="p-4">
                                                                    <button
                                                                        onClick={() => toggleSection(index, 'legacyAllergies')}
                                                                        className="w-full flex items-center justify-between text-left"
                                                                    >
                                                                        <h5 className="text-sm font-semibold text-gray-900 flex items-center">
                                                                            <span className="h-4 w-4 mr-2 text-orange-600">⚠️</span>
                                                                            Allergies ({patient.allergies.length})
                                                                        </h5>
                                                                        {isSectionExpanded(index, 'legacyAllergies') ? (
                                                                            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
                                                                        ) : (
                                                                            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                                                                        )}
                                                                    </button>

                                                                    {isSectionExpanded(index, 'legacyAllergies') && (
                                                                        <div className="mt-3 space-y-2">
                                                                            {patient.allergies.map((allergy, aIndex) => (
                                                                                <div key={aIndex} className="bg-white rounded-lg p-3 border border-orange-200">
                                                                                    <div className="flex justify-between items-center">
                                                                                        <div>
                                                                                            <span className="font-medium text-gray-900">{allergy.allergen}</span>
                                                                                            <span className="mx-2 text-gray-400">•</span>
                                                                                            <span className="text-sm text-gray-600">{allergy.reaction}</span>
                                                                                        </div>
                                                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${allergy.severity === 'Severe' ? 'bg-red-100 text-red-800' :
                                                                                            allergy.severity === 'Moderate' ? 'bg-orange-100 text-orange-800' :
                                                                                                'bg-yellow-100 text-yellow-800'
                                                                                            }`}>
                                                                                            {allergy.severity}
                                                                                        </span>
                                                                                    </div>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}



                                                        {/* Medical History */}
                                                        {patient.medical_history && patient.medical_history.length > 0 && (
                                                            <div>
                                                                <h5 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                                                                    <DocumentTextIcon className="h-4 w-4 mr-2 text-purple-600" />
                                                                    Medical History
                                                                </h5>
                                                                <div className="space-y-2">
                                                                    {patient.medical_history.map((condition, hIndex) => (
                                                                        <div key={hIndex} className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                                                                            <div className="flex justify-between items-center">
                                                                                <div>
                                                                                    <span className="font-medium text-gray-900">{condition.condition}</span>
                                                                                    <div className="text-sm text-gray-600">Diagnosed: {condition.diagnosed_date}</div>
                                                                                </div>
                                                                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${condition.status === 'Active' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                                                                                    }`}>
                                                                                    {condition.status}
                                                                                </span>
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Lab Results */}
                                                        {patient.lab_results && patient.lab_results.length > 0 && (
                                                            <div>
                                                                <h5 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                                                                    <span className="h-4 w-4 mr-2 text-blue-600">🧪</span>
                                                                    Recent Lab Results
                                                                </h5>
                                                                <div className="space-y-3">
                                                                    {patient.lab_results.slice(0, 2).map((lab, lIndex) => {
                                                                        const expandKey = `${index}-${lIndex}`;
                                                                        const isExpanded = expandedLabResults[expandKey];

                                                                        return (
                                                                            <div key={lIndex} className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                                                                                <div className="flex justify-between items-start mb-2">
                                                                                    <div className="font-medium text-gray-900">{lab.test_name}</div>
                                                                                    <div className="flex items-center space-x-2">
                                                                                        <div className="text-sm text-gray-500">{lab.date}</div>
                                                                                        {/* Lab Result Actions - Always show */}
                                                                                        <div className="flex items-center space-x-1">
                                                                                            <button
                                                                                                onClick={(e) => {
                                                                                                    e.stopPropagation();
                                                                                                    handleViewLabResult(lab, index, lIndex);
                                                                                                }}
                                                                                                className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
                                                                                                title="View Lab Result Details"
                                                                                            >
                                                                                                <EyeIcon className="h-4 w-4" />
                                                                                            </button>
                                                                                            <button
                                                                                                onClick={(e) => {
                                                                                                    e.stopPropagation();
                                                                                                    handleDownloadLabResult(lab);
                                                                                                }}
                                                                                                className="p-1 text-green-600 hover:text-green-800 hover:bg-green-100 rounded transition-colors"
                                                                                                title="Download Lab Result"
                                                                                            >
                                                                                                <ArrowDownTrayIcon className="h-4 w-4" />
                                                                                            </button>
                                                                                        </div>
                                                                                    </div>
                                                                                </div>

                                                                                {/* Basic Results Display */}
                                                                                {!isExpanded && (
                                                                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                                                                                        {Object.entries(lab.results || {}).map(([key, value]) => (
                                                                                            <div key={key} className="text-sm">
                                                                                                <span className="text-gray-600">{key}:</span>
                                                                                                <span className="ml-1 font-medium text-gray-900">{value}</span>
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                )}

                                                                                {/* Expanded Results Display */}
                                                                                {isExpanded && (
                                                                                    <div className="mt-3 p-4 bg-white rounded-lg border border-blue-300">
                                                                                        <h6 className="font-semibold text-gray-900 mb-3">Detailed Lab Results</h6>
                                                                                        <div className="space-y-3">
                                                                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                                                                <div>
                                                                                                    <span className="text-sm font-medium text-gray-700">Test Name:</span>
                                                                                                    <span className="ml-2 text-sm text-gray-900">{lab.test_name}</span>
                                                                                                </div>
                                                                                                <div>
                                                                                                    <span className="text-sm font-medium text-gray-700">Date:</span>
                                                                                                    <span className="ml-2 text-sm text-gray-900">{lab.date}</span>
                                                                                                </div>
                                                                                            </div>

                                                                                            <div>
                                                                                                <h7 className="text-sm font-medium text-gray-700 block mb-2">Results:</h7>
                                                                                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                                                                                    {Object.entries(lab.results || {}).map(([key, value]) => (
                                                                                                        <div key={key} className="bg-gray-50 rounded p-3">
                                                                                                            <div className="text-xs font-medium text-gray-500 uppercase">{key}</div>
                                                                                                            <div className="text-sm font-semibold text-gray-900 mt-1">{value}</div>
                                                                                                        </div>
                                                                                                    ))}
                                                                                                </div>
                                                                                            </div>

                                                                                            {/* Additional lab info if available */}
                                                                                            {(lab.reference_range || lab.notes || lab.status) && (
                                                                                                <div className="pt-3 border-t border-gray-200">
                                                                                                    {lab.reference_range && (
                                                                                                        <div className="mb-2">
                                                                                                            <span className="text-sm font-medium text-gray-700">Reference Range:</span>
                                                                                                            <span className="ml-2 text-sm text-gray-900">{lab.reference_range}</span>
                                                                                                        </div>
                                                                                                    )}
                                                                                                    {lab.status && (
                                                                                                        <div className="mb-2">
                                                                                                            <span className="text-sm font-medium text-gray-700">Status:</span>
                                                                                                            <span className="ml-2 text-sm text-gray-900">{lab.status}</span>
                                                                                                        </div>
                                                                                                    )}
                                                                                                    {lab.notes && (
                                                                                                        <div>
                                                                                                            <span className="text-sm font-medium text-gray-700">Notes:</span>
                                                                                                            <span className="ml-2 text-sm text-gray-900">{lab.notes}</span>
                                                                                                        </div>
                                                                                                    )}
                                                                                                </div>
                                                                                            )}
                                                                                        </div>
                                                                                    </div>
                                                                                )}

                                                                                {/* Lab Result Document Info */}
                                                                                {(lab.document_url || lab.pdf_url || lab.file_url) && (
                                                                                    <div className="mt-2 pt-2 border-t border-blue-200">
                                                                                        <div className="flex items-center text-xs text-blue-600">
                                                                                            <DocumentTextIcon className="h-3 w-3 mr-1" />
                                                                                            Lab document available
                                                                                            {lab.file_size && <span className="ml-1">({lab.file_size})</span>}
                                                                                        </div>
                                                                                    </div>
                                                                                )}
                                                                            </div>
                                                                        );
                                                                    })}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Upcoming Appointments */}
                                                        {patient.appointments && patient.appointments.length > 0 && (
                                                            <div>
                                                                <h5 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                                                                    <CalendarIcon className="h-4 w-4 mr-2 text-indigo-600" />
                                                                    Upcoming Appointments
                                                                </h5>
                                                                <div className="space-y-2">
                                                                    {patient.appointments.map((appt, appIndex) => (
                                                                        <div key={appIndex} className="bg-indigo-50 rounded-lg p-3 border border-indigo-200">
                                                                            <div className="flex justify-between items-center">
                                                                                <div>
                                                                                    <div className="font-medium text-gray-900">{appt.type} - {appt.provider}</div>
                                                                                    <div className="text-sm text-gray-600">{appt.date} at {appt.time}</div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default PatientData; 
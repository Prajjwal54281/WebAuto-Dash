
import React, { useState, useEffect } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { jobsApi, adaptersApi, realtimeApi } from '../services/api';
import { useSocket } from '../hooks/useSocket';
import JobProgressTracker from '../components/JobProgressTracker';
import toast from 'react-hot-toast';
import {
    PlusIcon,
    ArrowPathIcon,
    CheckCircleIcon,
    ExclamationCircleIcon,
    ClockIcon,
    TrashIcon,
    XMarkIcon,
    PlayIcon,
    StopIcon,
    ArrowTrendingUpIcon,
    BoltIcon,
    WrenchScrewdriverIcon,
    ChartBarIcon,
    BeakerIcon,
    FunnelIcon,
    Squares2X2Icon,
    ShieldCheckIcon,
    UserIcon,
    ChevronDownIcon,
    GlobeAltIcon,
    EyeIcon,
    ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

// Supported Medical Portals Configuration
const SUPPORTED_PORTALS = [
    // Future portals can be added here
];

// Static medication list - Replace with API call if needed
const MEDICATIONS = [
    'Methadone', 'Hydrocodone', 'Oxycodone', 'Tramadol', 'Morphine',
    'Buprenorphine', 'Fentanyl', 'Diazepam', 'Clonidine', 'Hydroxyzine',
    'Lamictal', 'Oxcarbazepine', 'Escitalopram', 'Zoloft', 'Wellbutrin',
    'Bupropion', 'Topamax', 'Topiramate', 'Clonazepam', 'Alprazolam',
    'Xanax', 'Remeron', 'Mirtazapine'
];

// Helper function to format date to MM/DD/YYYY format
const formatDateToMMDDYYYY = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const year = date.getFullYear();
    return `${month}/${day}/${year}`;
};

// Helper function to get today's date in MM/DD/YYYY format
const getTodayDateMMDDYYYY = () => {
    const today = new Date();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    const year = today.getFullYear();
    return `${month}/${day}/${year}`;
};

// Helper function to convert YYYY-MM-DD to MM/DD/YYYY
const convertFromDateInput = (yyyymmdd) => {
    if (!yyyymmdd || typeof yyyymmdd !== 'string' || yyyymmdd.trim() === '') {
        return '';
    }

    // Ensure the date is in YYYY-MM-DD format
    const datePattern = /^\d{4}-\d{2}-\d{2}$/;
    if (!datePattern.test(yyyymmdd)) {
        console.warn(`Invalid date format: ${yyyymmdd}, expected YYYY-MM-DD`);
        return '';
    }

    const [year, month, day] = yyyymmdd.split('-');

    // Validate date components
    const yearNum = parseInt(year, 10);
    const monthNum = parseInt(month, 10);
    const dayNum = parseInt(day, 10);

    if (yearNum < 1900 || yearNum > 2100 || monthNum < 1 || monthNum > 12 || dayNum < 1 || dayNum > 31) {
        console.warn(`Invalid date values: ${yyyymmdd}`);
        return '';
    }

    // Return formatted date
    return `${month}/${day}/${year}`;
};

// Helper function to convert MM/DD/YYYY to YYYY-MM-DD for HTML date input
const convertToDateInput = (mmddyyyy) => {
    if (!mmddyyyy || typeof mmddyyyy !== 'string' || mmddyyyy.trim() === '') {
        return '';
    }

    // Handle both MM/DD/YYYY and M/D/YYYY formats
    const datePattern = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
    const match = mmddyyyy.match(datePattern);

    if (!match) {
        console.warn(`Invalid date format: ${mmddyyyy}, expected MM/DD/YYYY`);
        return '';
    }

    const [, month, day, year] = match;

    // Validate date components
    const yearNum = parseInt(year, 10);
    const monthNum = parseInt(month, 10);
    const dayNum = parseInt(day, 10);

    if (yearNum < 1900 || yearNum > 2100 || monthNum < 1 || monthNum > 12 || dayNum < 1 || dayNum > 31) {
        console.warn(`Invalid date values: ${mmddyyyy}`);
        return '';
    }

    // Pad with zeros and return
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
};

// Resume Controls Component
const ResumeControls = ({ job, onRetry, onForceRestart, onAnalyze }) => {
    const [showDetails, setShowDetails] = useState(false);
    const [analysis, setAnalysis] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    useEffect(() => {
        // Fetch resume analysis when component mounts
        if (job.status === 'COMPLETED' || job.status === 'FAILED') {
            analyzeJob();
        }
    }, [job.id, job.status]);

    const analyzeJob = async () => {
        setIsAnalyzing(true);
        try {
            const response = await jobsApi.getResumeAnalysis(job.id);
            if (response.data.success) {
                setAnalysis(response.data.analysis);
            }
        } catch (error) {
            console.error('Failed to analyze job for resume:', error);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const hasResumableFailures = analysis && analysis.incomplete_medications > 0;

    if (!analysis && !isAnalyzing) {
        return null;
    }

    if (isAnalyzing) {
        return (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-2">
                <div className="flex items-center">
                    <ArrowPathIcon className="h-4 w-4 text-blue-600 mr-2 animate-spin" />
                    <span className="text-sm text-blue-800">Analyzing resume opportunities...</span>
                </div>
            </div>
        );
    }

    if (!hasResumableFailures) {
        return null;
    }

    return (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-2">
            <div className="flex items-center justify-between">
                <div className="flex items-center">
                    <ArrowPathIcon className="h-5 w-5 text-yellow-600 mr-2" />
                    <span className="text-sm font-medium text-yellow-800">
                        Resume Available - {analysis.incomplete_medications} patients need medication retry
                    </span>
                </div>
                <button
                    onClick={() => setShowDetails(!showDetails)}
                    className="text-yellow-600 hover:text-yellow-800"
                >
                    <ChevronDownIcon className={`h-4 w-4 transform ${showDetails ? 'rotate-180' : ''}`} />
                </button>
            </div>

            {showDetails && (
                <div className="mt-3 text-sm text-yellow-700">
                    <div className="grid grid-cols-2 gap-4 mb-3">
                        <div>
                            <span className="font-medium">✅ Complete:</span> {analysis.successful_medications || 0} patients
                        </div>
                        <div>
                            <span className="font-medium">❌ Missing Medications:</span> {analysis.incomplete_medications || 0} patients
                        </div>
                        <div>
                            <span className="font-medium">📊 Success Rate:</span> {analysis.success_rate?.toFixed(1)}%
                        </div>
                        <div>
                            <span className="font-medium">⏱️ Time Savings:</span> ~{analysis.estimated_time_savings || 0} minutes
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={() => onRetry(job.id, 'resume')}
                            className="px-3 py-1 bg-yellow-600 text-white rounded hover:bg-yellow-700 text-xs"
                        >
                            🔄 Resume (Retry Failed Only)
                        </button>
                        <button
                            onClick={() => onForceRestart(job.id)}
                            className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-xs"
                        >
                            🔄 Force Restart (All Patients)
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

// Enhanced Searchable Medication Dropdown Component
const SearchableMedicationDropdown = ({ value, onChange, medications = MEDICATIONS, placeholder = "Search medications..." }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const filteredMedications = medications.filter(med =>
        med.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleSelect = (medication) => {
        onChange(medication);
        setIsOpen(false);
        setSearchQuery('');
    };

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (isOpen && !event.target.closest('.medication-dropdown')) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isOpen]);

    return (
        <div className="relative medication-dropdown">
            <div className="relative">
                <input
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onFocus={() => setIsOpen(true)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
                    placeholder={placeholder}
                />
                <button
                    type="button"
                    onClick={() => setIsOpen(!isOpen)}
                    className="absolute inset-y-0 right-0 px-3 flex items-center"
                >
                    <ChevronDownIcon className={`h-4 w-4 text-gray-400 transform transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </button>
            </div>

            {isOpen && (
                <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg">
                    <div className="p-2 border-b border-gray-200">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                            placeholder="Type to search..."
                            autoFocus
                        />
                    </div>
                    <div className="max-h-48 overflow-y-auto">
                        {filteredMedications.length > 0 ? (
                            filteredMedications.map((medication) => (
                                <button
                                    key={medication}
                                    type="button"
                                    onClick={() => handleSelect(medication)}
                                    className="w-full px-4 py-2 text-left hover:bg-blue-50 focus:bg-blue-50 focus:outline-none text-sm"
                                >
                                    {medication}
                                </button>
                            ))
                        ) : (
                            <div className="px-4 py-2 text-gray-500 text-sm">No medications found</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

const Jobs = () => {
    const [jobs, setJobs] = useState([]);
    const [adapters, setAdapters] = useState([]);
    const [medications, setMedications] = useState(MEDICATIONS);
    const [loading, setLoading] = useState(true);
    const [showNewJobModal, setShowNewJobModal] = useState(false);
    const [showBatchModal, setShowBatchModal] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [showJobDetailsModal, setShowJobDetailsModal] = useState(false);
    const [selectedJobForDetails, setSelectedJobForDetails] = useState(null);
    const [jobToDelete, setJobToDelete] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [viewMode, setViewMode] = useState('cards');
    const [filterStatus, setFilterStatus] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [newJob, setNewJob] = useState({
        job_name: '',
        portal_name: '',
        target_url: '',
        adapter_id: '',
        extraction_mode: 'ALL_PATIENTS',
        input_patient_identifier: '',
        doctor_name: '',
        medication: '',
        start_date: '',
        end_date: ''
    });
    const [batchJobs, setBatchJobs] = useState([{
        job_name: '',
        portal_name: '',
        target_url: '',
        adapter_id: '',
        extraction_mode: 'ALL_PATIENTS',
        input_patient_identifier: '',
        doctor_name: '',
        medication: '',
        start_date: '',
        end_date: ''
    }]);

    const socket = useSocket();
    const [searchParams] = useSearchParams();

    // Filter jobs based on status and search term
    const filteredJobs = jobs.filter(job => {
        const matchesStatus = filterStatus === 'all' || job.status === filterStatus;
        const matchesSearch = !searchTerm ||
            job.job_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            job.adapter_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            job.input_patient_identifier?.toLowerCase().includes(searchTerm.toLowerCase());
        return matchesStatus && matchesSearch;
    });

    // Group jobs by status for better organization
    const jobsByStatus = {
        active: filteredJobs.filter(job => ['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING'].includes(job.status)),
        completed: filteredJobs.filter(job => job.status === 'COMPLETED'),
        failed: filteredJobs.filter(job => job.status === 'FAILED')
    };

    useEffect(() => {
        if (socket) {
            // Listen for real-time job updates
            socket.on('job_progress_update', (data) => {
                // Update is handled by individual JobProgressTracker components
            });

            socket.on('job_retried', (data) => {
                toast.success(`Job #${data.job_id} restarted!`);
                fetchJobs();
            });

            socket.on('job_cancelled', (data) => {
                toast.success(`Job #${data.job_id} cancelled!`);
                fetchJobs();
            });

            socket.on('batch_jobs_created', (data) => {
                toast.success(`Created ${data.created_count} batch jobs!`);
                fetchJobs();
            });

            return () => {
                socket.off('job_progress_update');
                socket.off('job_retried');
                socket.off('job_cancelled');
                socket.off('batch_jobs_created');
            };
        }
    }, [socket]);

    useEffect(() => {
        fetchJobs();
        fetchAdapters();
        fetchMedications();

        // Check URL params for batch mode
        if (searchParams.get('create') === 'batch') {
            setShowBatchModal(true);
        }
    }, [currentPage, searchParams]);

    // Handle pre-selected adapter from URL parameters
    useEffect(() => {
        const preSelectedAdapter = searchParams.get('adapter');
        if (preSelectedAdapter && adapters.length > 0) {
            const selectedAdapter = adapters.find(adapter => adapter.id === parseInt(preSelectedAdapter));
            if (selectedAdapter) {
                setNewJob(prev => ({
                    ...prev,
                    adapter_id: preSelectedAdapter
                }));
                setShowNewJobModal(true);
            }
        }
    }, [searchParams, adapters]);

    // Auto-refresh jobs every 10 seconds for active jobs
    useEffect(() => {
        const interval = setInterval(() => {
            if (jobsByStatus.active.length > 0) {
                fetchJobs();
            }
        }, 10000);
        return () => clearInterval(interval);
    }, [jobsByStatus.active.length]);

    const fetchJobs = async () => {
        try {
            const response = await jobsApi.getAll(currentPage, 20);
            const jobsData = response.data.jobs || [];
            const paginationData = response.data.pagination || { pages: 1 };

            setJobs(jobsData);
            setTotalPages(paginationData.pages);
        } catch (error) {
            console.error('Failed to fetch jobs:', error);
            toast.error('Failed to load jobs');
        } finally {
            setLoading(false);
        }
    };

    const fetchAdapters = async () => {
        try {
            const response = await adaptersApi.getActive();
            const adaptersData = response.data.adapters || [];
            setAdapters(adaptersData);
        } catch (error) {
            console.error('Failed to fetch adapters:', error);
            toast.error('Failed to load adapters');
        }
    };

    const fetchMedications = async () => {
        try {
            setMedications(MEDICATIONS);
        } catch (error) {
            console.error('Failed to fetch medications, using static list:', error);
            setMedications(MEDICATIONS);
        }
    };

    const handleCreateJob = async (e) => {
        e.preventDefault();

        // Enhanced validation
        if (!newJob.job_name?.trim()) {
            toast.error('Job name is required');
            return;
        }

        if (!newJob.target_url?.trim()) {
            toast.error('Target URL is required');
            return;
        }

        if (!newJob.adapter_id) {
            toast.error('Portal adapter is required');
            return;
        }

        if (newJob.extraction_mode === 'SINGLE_PATIENT' && !newJob.input_patient_identifier?.trim()) {
            toast.error('Patient identifier is required for single patient extraction');
            return;
        }

        try {
            // Create job data matching orchestrator expectations
            const jobData = {
                job_name: newJob.job_name.trim(),
                target_url: newJob.target_url.trim(),
                adapter_id: newJob.adapter_id,
                extraction_mode: newJob.extraction_mode
            };

            // Add patient identifier for single patient mode (orchestrator uses this field)
            if (newJob.extraction_mode === 'SINGLE_PATIENT' && newJob.input_patient_identifier?.trim()) {
                jobData.input_patient_identifier = newJob.input_patient_identifier.trim();
            }

            // Create job_parameters object (orchestrator passes this to adapter)
            const jobParameters = {};

            // Add medication report parameters that orchestrator expects
            // Only add parameters if they have actual values
            if (newJob.doctor_name?.trim()) {
                jobParameters.doctor_name = newJob.doctor_name.trim();
            }

            if (newJob.medication?.trim()) {
                jobParameters.medication = newJob.medication.trim();
            }

            // Convert dates from HTML date input format (YYYY-MM-DD) to MM/DD/YYYY for adapter
            // Only add dates if they have values
            if (newJob.start_date && newJob.start_date.trim()) {
                const convertedStartDate = convertFromDateInput(newJob.start_date);
                if (convertedStartDate) {
                    jobParameters.start_date = convertedStartDate;
                }
            }

            if (newJob.end_date && newJob.end_date.trim()) {
                const convertedEndDate = convertFromDateInput(newJob.end_date);
                if (convertedEndDate) {
                    jobParameters.stop_date = convertedEndDate; // Note: adapter expects 'stop_date'
                }
            }

            // Add extraction mode for the adapter
            if (newJob.extraction_mode === 'SINGLE_PATIENT' && newJob.input_patient_identifier?.trim()) {
                jobParameters.extraction_mode = 'Target Patient by Name';
                jobParameters.target_patient_name = newJob.input_patient_identifier.trim();
            } else {
                jobParameters.extraction_mode = 'All Patients';
            }

            // Only add job_parameters if we have actual parameters
            if (Object.keys(jobParameters).length > 0) {
                jobData.job_parameters = jobParameters;
            } else {
                // If no parameters, add default empty object to avoid backend issues
                jobData.job_parameters = {};
            }

            console.log('Creating job with data:', jobData);
            console.log('Job parameters:', jobParameters);

            const response = await jobsApi.create(jobData);

            setShowNewJobModal(false);
            setNewJob({
                job_name: '',
                portal_name: '',
                target_url: '',
                adapter_id: '',
                extraction_mode: 'ALL_PATIENTS',
                input_patient_identifier: '',
                doctor_name: '',
                medication: '',
                start_date: '',
                end_date: ''
            });

            fetchJobs();
            toast.success('Job created successfully!');

        } catch (error) {
            console.error('Failed to create job:', error);
            console.error('Error details:', error.response?.data);

            // More specific error messages based on response
            const errorMessage = error.response?.data?.error || error.response?.data?.message || error.message;

            if (error.response?.status === 400) {
                toast.error(`Invalid job data: ${errorMessage}`);
            } else if (error.response?.status === 422) {
                toast.error(`Validation error: ${errorMessage}`);
            } else if (error.response?.status === 500) {
                toast.error(`Server error: ${errorMessage}. Please check the logs.`);
            } else {
                toast.error(`Failed to create job: ${errorMessage}`);
            }
        }
    };

    const handleCreateBatchJobs = async (e) => {
        e.preventDefault();

        // Validate all jobs in the batch
        const validationErrors = [];
        const processedJobs = batchJobs.map((job, index) => {
            if (!job.job_name?.trim()) {
                validationErrors.push(`Job #${index + 1}: Job name is required`);
            }
            if (!job.target_url?.trim()) {
                validationErrors.push(`Job #${index + 1}: Target URL is required`);
            }
            if (!job.adapter_id) {
                validationErrors.push(`Job #${index + 1}: Portal adapter is required`);
            }
            if (job.extraction_mode === 'SINGLE_PATIENT' && !job.input_patient_identifier?.trim()) {
                validationErrors.push(`Job #${index + 1}: Patient identifier is required for single patient extraction`);
            }

            // Separate job data from adapter parameters
            const jobData = {
                job_name: job.job_name?.trim() || '',
                target_url: job.target_url?.trim() || '',
                adapter_id: job.adapter_id,
                extraction_mode: job.extraction_mode
            };

            // Add patient identifier for single patient mode
            if (job.extraction_mode === 'SINGLE_PATIENT' && job.input_patient_identifier?.trim()) {
                jobData.input_patient_identifier = job.input_patient_identifier.trim();
            }

            // Create job_parameters object for the adapter
            const jobParameters = {};

            // Add required medication report parameters only if they have values
            if (job.doctor_name?.trim()) {
                jobParameters.doctor_name = job.doctor_name.trim();
            }

            if (job.medication?.trim()) {
                jobParameters.medication = job.medication.trim();
            }

            // Convert dates from HTML date input format (YYYY-MM-DD) to MM/DD/YYYY for adapter
            // Only add if they have values
            if (job.start_date && job.start_date.trim()) {
                const convertedStartDate = convertFromDateInput(job.start_date);
                if (convertedStartDate) {
                    jobParameters.start_date = convertedStartDate;
                }
            }

            if (job.end_date && job.end_date.trim()) {
                const convertedEndDate = convertFromDateInput(job.end_date);
                if (convertedEndDate) {
                    jobParameters.stop_date = convertedEndDate; // Note: adapter expects 'stop_date'
                }
            }

            // Set extraction mode for the adapter
            if (job.extraction_mode === 'SINGLE_PATIENT' && job.input_patient_identifier?.trim()) {
                jobParameters.extraction_mode = 'Target Patient by Name';
                jobParameters.target_patient_name = job.input_patient_identifier.trim();
            } else {
                jobParameters.extraction_mode = 'All Patients';
            }

            // Add job_parameters to the payload
            if (Object.keys(jobParameters).length > 0) {
                jobData.job_parameters = jobParameters;
            } else {
                // Ensure we have at least an empty object
                jobData.job_parameters = {};
            }

            return jobData;
        });

        if (validationErrors.length > 0) {
            toast.error(`Validation errors:\n${validationErrors.join('\n')}`, {
                duration: 6000,
                style: { whiteSpace: 'pre-line' }
            });
            return;
        }

        try {
            console.log('Creating batch jobs with data:', processedJobs);

            const response = await realtimeApi.createBatchJobs({
                jobs: processedJobs,
                start_immediately: true
            });

            if (response.data.success) {
                setShowBatchModal(false);
                setBatchJobs([{
                    job_name: '',
                    portal_name: '',
                    target_url: '',
                    adapter_id: '',
                    extraction_mode: 'ALL_PATIENTS',
                    input_patient_identifier: '',
                    doctor_name: '',
                    medication: '',
                    start_date: '',
                    end_date: ''
                }]);
                fetchJobs();
                toast.success(`Created ${response.data.created_jobs.length} batch jobs!`);
            } else {
                toast.error(`Batch job creation failed: ${response.data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to create batch jobs:', error);
            console.error('Error details:', error.response?.data);

            const errorMessage = error.response?.data?.error || error.response?.data?.message || error.message;
            toast.error(`Failed to create batch jobs: ${errorMessage}`);
        }
    };

    const handlePortalChange = (portalName, setJobFunction) => {
        const selectedPortal = SUPPORTED_PORTALS.find(p => p.name === portalName);
        setJobFunction(prev => ({
            ...prev,
            portal_name: portalName,
            target_url: selectedPortal ? selectedPortal.url : ''
        }));
    };

    const handleRetryJob = async (jobId) => {
        try {
            await realtimeApi.retryJob(jobId);
            toast.success('Job restarted successfully!');
            fetchJobs();
        } catch (error) {
            console.error('Failed to retry job:', error);
            toast.error('Failed to restart job');
        }
    };

    const handleCancelJob = async (jobId) => {
        try {
            const response = await realtimeApi.cancelJob(jobId);
            if (response.data && response.data.success) {
                toast.success('Job cancelled successfully!');
                // Wait a moment before refreshing to allow backend to process
                setTimeout(() => {
                    fetchJobs();
                }, 1500);
            } else {
                throw new Error(response.data?.message || 'Failed to cancel job');
            }
        } catch (error) {
            console.error('Failed to cancel job:', error);
            toast.error('Failed to cancel job: ' + (error.response?.data?.message || error.message));
        }
    };

    const handleConfirmLogin = async (jobId) => {
        try {
            await jobsApi.confirmLogin(jobId);
            fetchJobs();
            toast.success('Login confirmed successfully!');
        } catch (error) {
            console.error('Failed to confirm login:', error);
            toast.error('Failed to confirm login');
        }
    };

    const handleHealthCheck = async () => {
        try {
            const response = await realtimeApi.healthCheckJobs();
            if (response.data.success) {
                toast.success(`Health check complete! Fixed ${response.data.fixed_jobs.length} stuck jobs.`);
                fetchJobs();
            }
        } catch (error) {
            toast.error('Health check failed');
        }
    };

    const handleDeleteJob = async () => {
        if (!jobToDelete) return;

        try {
            await jobsApi.delete(jobToDelete.id);
            setJobs(jobs.filter(job => job.id !== jobToDelete.id));
            setShowDeleteModal(false);
            setJobToDelete(null);
            toast.success('Job deleted successfully!');
        } catch (error) {
            console.error('Failed to delete job:', error);
            toast.error('Failed to delete job');
        }
    };

    const handleBulkDeleteFailed = async () => {
        if (window.confirm(`Delete all ${jobsByStatus.failed.length} failed jobs?`)) {
            try {
                const deletePromises = jobsByStatus.failed.map(job => jobsApi.delete(job.id));
                await Promise.all(deletePromises);
                fetchJobs();
                toast.success(`Deleted ${jobsByStatus.failed.length} failed jobs!`);
            } catch (error) {
                toast.error('Failed to delete some jobs');
            }
        }
    };

    const handleBulkConfirmLogins = async () => {
        const waitingJobs = jobsByStatus.active.filter(job => job.status === 'AWAITING_USER_CONFIRMATION');
        try {
            const confirmPromises = waitingJobs.map(job => jobsApi.confirmLogin(job.id));
            await Promise.all(confirmPromises);
            fetchJobs();
            toast.success(`Confirmed logins for ${waitingJobs.length} jobs!`);
        } catch (error) {
            toast.error('Failed to confirm some logins');
        }
    };

    const handleRetryJobWithResume = async (jobId, mode = 'resume') => {
        try {
            const response = await jobsApi.retryWithResume(jobId, mode);
            if (response.data.success) {
                toast.success(`Job retry started (${mode} mode)!`);
                fetchJobs();
            } else {
                throw new Error(response.data.error || 'Failed to start retry');
            }
        } catch (error) {
            console.error('Failed to retry job:', error);
            toast.error('Failed to retry job: ' + (error.response?.data?.error || error.message));
        }
    };

    const handleForceRestart = async (jobId) => {
        if (window.confirm('Are you sure you want to restart this job from scratch? This will process ALL patients again.')) {
            await handleRetryJobWithResume(jobId, 'restart');
        }
    };

    const handleShowJobDetails = (job) => {
        setSelectedJobForDetails(job);
        setShowJobDetailsModal(true);
    };

    const addBatchJob = () => {
        setBatchJobs([...batchJobs, {
            job_name: '',
            portal_name: '',
            target_url: '',
            adapter_id: '',
            extraction_mode: 'ALL_PATIENTS',
            input_patient_identifier: '',
            doctor_name: '',
            medication: '',
            start_date: '',
            end_date: ''
        }]);
    };

    const removeBatchJob = (index) => {
        setBatchJobs(batchJobs.filter((_, i) => i !== index));
    };

    const updateBatchJob = (index, field, value) => {
        const updated = [...batchJobs];
        updated[index][field] = value;
        setBatchJobs(updated);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="relative">
                    <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
                    <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                        <BoltIcon className="h-6 w-6 text-blue-500" />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Extraction Jobs</h1>
                    <p className="mt-2 text-lg text-gray-600">
                        Monitor and manage medical data extraction jobs with real-time updates
                    </p>
                </div>

                <div className="flex flex-col sm:flex-row mt-4 lg:mt-0 space-y-2 sm:space-y-0 sm:space-x-3">
                    <button
                        onClick={() => setShowBatchModal(true)}
                        className="inline-flex items-center justify-center px-6 py-3 border border-transparent shadow-sm text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transform hover:scale-105 transition-all duration-200"
                    >
                        <ArrowTrendingUpIcon className="h-5 w-5 mr-2" />
                        Batch Operations
                    </button>

                    <button
                        onClick={() => setShowNewJobModal(true)}
                        className="inline-flex items-center justify-center px-6 py-3 border border-transparent shadow-sm text-sm font-medium rounded-xl text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transform hover:scale-105 transition-all duration-200"
                    >
                        <PlusIcon className="h-5 w-5 mr-2" />
                        New Job
                    </button>

                    <button
                        onClick={() => fetchJobs()}
                        className="inline-flex items-center justify-center px-6 py-3 border border-gray-300 shadow-sm text-sm font-medium rounded-xl text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                        <ArrowPathIcon className="h-5 w-5 mr-2" />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Filters and Search */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
                    <div className="flex items-center space-x-4">
                        {/* Search */}
                        <div className="relative">
                            <input
                                type="text"
                                placeholder="Search jobs..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-4 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>

                        {/* Status Filter */}
                        <select
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value)}
                            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="all">All Status</option>
                            <option value="PENDING_LOGIN">Pending Login</option>
                            <option value="LAUNCHING_BROWSER">Launching Browser</option>
                            <option value="AWAITING_USER_CONFIRMATION">Awaiting Confirmation</option>
                            <option value="EXTRACTING">Extracting</option>
                            <option value="COMPLETED">Completed</option>
                            <option value="FAILED">Failed</option>
                        </select>
                    </div>

                    <div className="flex items-center space-x-2">
                        {/* View Mode Toggle */}
                        <div className="flex bg-gray-100 rounded-lg p-1">
                            <button
                                onClick={() => setViewMode('cards')}
                                className={`p-2 rounded-md ${viewMode === 'cards' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-500'}`}
                            >
                                <Squares2X2Icon className="h-5 w-5" />
                            </button>
                        </div>

                        {/* Stats */}
                        <div className="text-sm text-gray-500">
                            {filteredJobs.length} of {jobs.length} jobs
                        </div>
                    </div>
                </div>
            </div>

            {/* Compact Jobs Summary */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
                    {/* Compact Status Overview */}
                    <div className="flex flex-wrap items-center gap-4 lg:gap-6">
                        <div className="flex items-center space-x-2">
                            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                            <span className="text-sm text-gray-600">Active:</span>
                            <span className="font-semibold text-blue-600">{jobsByStatus.active.length}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                            <span className="text-sm text-gray-600">Completed:</span>
                            <span className="font-semibold text-green-600">{jobsByStatus.completed.length}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                            <span className="text-sm text-gray-600">Failed:</span>
                            <span className="font-semibold text-red-600">{jobsByStatus.failed.length}</span>
                        </div>
                    </div>

                    {/* Management Actions */}
                    <div className="flex flex-wrap items-center gap-2 lg:gap-3">
                        <button
                            onClick={handleHealthCheck}
                            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            <ShieldCheckIcon className="h-4 w-4 mr-1" />
                            Clear Hung Tasks
                        </button>
                        {jobsByStatus.failed.length > 0 && (
                            <button
                                onClick={handleBulkDeleteFailed}
                                className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                            >
                                <TrashIcon className="h-4 w-4 mr-1" />
                                Delete Failed
                            </button>
                        )}
                        {jobsByStatus.active.filter(job => job.status === 'AWAITING_USER_CONFIRMATION').length > 0 && (
                            <button
                                onClick={handleBulkConfirmLogins}
                                className="inline-flex items-center px-3 py-2 border border-green-300 shadow-sm text-sm leading-4 font-medium rounded-md text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                            >
                                <CheckCircleIcon className="h-4 w-4 mr-1" />
                                Confirm All Logins
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Jobs List - Sectioned by Status */}
            {filteredJobs.length > 0 ? (
                <div className="space-y-8">
                    {/* Active Jobs Section */}
                    {jobsByStatus.active.length > 0 && (
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-xl font-semibold text-gray-900 flex items-center">
                                    <div className="w-3 h-3 bg-blue-500 rounded-full mr-3"></div>
                                    Active Jobs ({jobsByStatus.active.length})
                                </h3>
                                <div className="text-sm text-gray-500">
                                    Currently running extraction jobs
                                </div>
                            </div>
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                                {jobsByStatus.active.map((job) => (
                                    <div key={job.id} className="relative">
                                        <JobProgressTracker
                                            job={job}
                                            onJobUpdate={fetchJobs}
                                            onDelete={(job) => {
                                                setJobToDelete(job);
                                                setShowDeleteModal(true);
                                            }}
                                            onConfirmLogin={() => handleConfirmLogin(job.id)}
                                        />
                                        <button
                                            onClick={() => handleShowJobDetails(job)}
                                            className="absolute top-4 right-4 p-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 hover:border-gray-300 transition-colors z-10"
                                            title="Show job details"
                                        >
                                            <EyeIcon className="h-4 w-4 text-gray-600" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Completed Jobs Section */}
                    {jobsByStatus.completed.length > 0 && (
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-xl font-semibold text-gray-900 flex items-center">
                                    <CheckCircleIcon className="h-6 w-6 text-green-500 mr-3" />
                                    Successfully Completed Jobs ({jobsByStatus.completed.length})
                                </h3>
                                <div className="text-sm text-gray-500">
                                    Jobs that finished successfully
                                </div>
                            </div>
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                                {jobsByStatus.completed.map((job) => (
                                    <div key={job.id} className="relative">
                                        <JobProgressTracker
                                            job={job}
                                            onJobUpdate={fetchJobs}
                                            onDelete={(job) => {
                                                setJobToDelete(job);
                                                setShowDeleteModal(true);
                                            }}
                                        />
                                        <ResumeControls
                                            job={job}
                                            onRetry={handleRetryJobWithResume}
                                            onForceRestart={handleForceRestart}
                                        />
                                        <button
                                            onClick={() => handleShowJobDetails(job)}
                                            className="absolute top-4 right-4 p-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 hover:border-gray-300 transition-colors z-10"
                                            title="Show job details"
                                        >
                                            <EyeIcon className="h-4 w-4 text-gray-600" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Failed Jobs Section */}
                    {jobsByStatus.failed.length > 0 && (
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-xl font-semibold text-gray-900 flex items-center">
                                    <ExclamationCircleIcon className="h-6 w-6 text-red-500 mr-3" />
                                    Failed Jobs ({jobsByStatus.failed.length})
                                </h3>
                                <div className="flex items-center space-x-4">
                                    <div className="text-sm text-gray-500">
                                        Jobs that encountered errors
                                    </div>
                                    <button
                                        onClick={handleBulkDeleteFailed}
                                        className="inline-flex items-center px-3 py-1.5 border border-red-300 shadow-sm text-xs font-medium rounded text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                                    >
                                        <TrashIcon className="h-3 w-3 mr-1" />
                                        Delete All Failed
                                    </button>
                                </div>
                            </div>
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                                {jobsByStatus.failed.map((job) => (
                                    <div key={job.id} className="relative">
                                        <JobProgressTracker
                                            job={job}
                                            onJobUpdate={fetchJobs}
                                            onDelete={(job) => {
                                                setJobToDelete(job);
                                                setShowDeleteModal(true);
                                            }}
                                        />
                                        <ResumeControls
                                            job={job}
                                            onRetry={handleRetryJobWithResume}
                                            onForceRestart={handleForceRestart}
                                        />
                                        <button
                                            onClick={() => handleShowJobDetails(job)}
                                            className="absolute top-4 right-4 p-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 hover:border-gray-300 transition-colors z-10"
                                            title="Show job details"
                                        >
                                            <EyeIcon className="h-4 w-4 text-gray-600" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                <div className="text-center py-12">
                    <BoltIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                        {searchTerm || filterStatus !== 'all' ? 'No matching jobs found' : 'No jobs yet'}
                    </h3>
                    <p className="text-gray-500 mb-6">
                        {searchTerm || filterStatus !== 'all'
                            ? 'Try adjusting your search or filter criteria.'
                            : 'Create your first extraction job to get started.'}
                    </p>
                    {(!searchTerm && filterStatus === 'all') && (
                        <button
                            onClick={() => setShowNewJobModal(true)}
                            className="inline-flex items-center px-6 py-3 border border-transparent shadow-sm text-base font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            <PlusIcon className="h-5 w-5 mr-2" />
                            Create First Job
                        </button>
                    )}
                </div>
            )}

            {/* New Job Modal */}
            {showNewJobModal && (
                <JobModal
                    onClose={() => setShowNewJobModal(false)}
                    onSubmit={handleCreateJob}
                    job={newJob}
                    setJob={setNewJob}
                    adapters={adapters}
                    medications={medications}
                    title="Create New Job"
                    onPortalChange={handlePortalChange}
                />
            )}

            {/* Batch Jobs Modal */}
            {showBatchModal && (
                <BatchJobsModal
                    onClose={() => setShowBatchModal(false)}
                    onSubmit={handleCreateBatchJobs}
                    jobs={batchJobs}
                    adapters={adapters}
                    medications={medications}
                    addJob={addBatchJob}
                    removeJob={removeBatchJob}
                    updateJob={updateBatchJob}
                    onPortalChange={handlePortalChange}
                />
            )}

            {/* Job Details Modal */}
            {showJobDetailsModal && selectedJobForDetails && (
                <JobDetailsModal
                    job={selectedJobForDetails}
                    onClose={() => {
                        setShowJobDetailsModal(false);
                        setSelectedJobForDetails(null);
                    }}
                />
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteModal && (
                <DeleteConfirmModal
                    onClose={() => setShowDeleteModal(false)}
                    onConfirm={handleDeleteJob}
                    jobName={jobToDelete?.job_name || `Job #${jobToDelete?.id}`}
                />
            )}
        </div>
    );
};

// Job Details Modal Component
const JobDetailsModal = ({ job, onClose }) => {
    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleString();
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'COMPLETED': return 'text-green-600 bg-green-100';
            case 'FAILED': return 'text-red-600 bg-red-100';
            case 'PENDING_LOGIN':
            case 'LAUNCHING_BROWSER':
            case 'AWAITING_USER_CONFIRMATION':
            case 'EXTRACTING': return 'text-blue-600 bg-blue-100';
            default: return 'text-gray-600 bg-gray-100';
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-8 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-2xl font-bold text-gray-900 flex items-center">
                        <EyeIcon className="h-7 w-7 text-blue-500 mr-2" />
                        Job Details
                    </h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <XMarkIcon className="h-6 w-6" />
                    </button>
                </div>

                <div className="space-y-6">
                    {/* Basic Information */}
                    <div className="bg-gray-50 rounded-lg p-6">
                        <h4 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Job Name</label>
                                <p className="mt-1 text-sm text-gray-900">{job.job_name || 'N/A'}</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Job ID</label>
                                <p className="mt-1 text-sm text-gray-900">#{job.id}</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Status</label>
                                <span className={`mt-1 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                                    {job.status?.replace(/_/g, ' ') || 'Unknown'}
                                </span>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Adapter</label>
                                <p className="mt-1 text-sm text-gray-900">{job.adapter_name || 'N/A'}</p>
                            </div>
                        </div>
                    </div>

                    {/* Configuration */}
                    <div className="bg-gray-50 rounded-lg p-6">
                        <h4 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="md:col-span-2">
                                <label className="block text-sm font-medium text-gray-700">Target URL</label>
                                <p className="mt-1 text-sm text-gray-900 break-all">{job.target_url || 'N/A'}</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Extraction Mode</label>
                                <p className="mt-1 text-sm text-gray-900">{job.extraction_mode?.replace(/_/g, ' ') || 'N/A'}</p>
                            </div>
                            {job.input_patient_identifier && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Patient Identifier</label>
                                    <p className="mt-1 text-sm text-gray-900">{job.input_patient_identifier}</p>
                                </div>
                            )}
                            {job.doctor_name && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Doctor Name</label>
                                    <p className="mt-1 text-sm text-gray-900">{job.doctor_name}</p>
                                </div>
                            )}
                            {job.medication && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Medication</label>
                                    <p className="mt-1 text-sm text-gray-900">{job.medication}</p>
                                </div>
                            )}
                            {(job.start_date || job.end_date) && (
                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium text-gray-700">Date Range</label>
                                    <p className="mt-1 text-sm text-gray-900">
                                        {job.start_date || 'N/A'} to {job.end_date || 'N/A'}
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Timestamps */}
                    <div className="bg-gray-50 rounded-lg p-6">
                        <h4 className="text-lg font-semibold text-gray-900 mb-4">Timestamps</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Created</label>
                                <p className="mt-1 text-sm text-gray-900">{formatDate(job.created_at)}</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Updated</label>
                                <p className="mt-1 text-sm text-gray-900">{formatDate(job.updated_at)}</p>
                            </div>
                            {job.started_at && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Started</label>
                                    <p className="mt-1 text-sm text-gray-900">{formatDate(job.started_at)}</p>
                                </div>
                            )}
                            {job.completed_at && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Completed</label>
                                    <p className="mt-1 text-sm text-gray-900">{formatDate(job.completed_at)}</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Progress Information */}
                    {(job.progress_details || job.error_message) && (
                        <div className="bg-gray-50 rounded-lg p-6">
                            <h4 className="text-lg font-semibold text-gray-900 mb-4">Progress Information</h4>
                            {job.progress_details && (
                                <div className="mb-4">
                                    <label className="block text-sm font-medium text-gray-700">Progress Details</label>
                                    <div className="mt-1 p-3 bg-white border border-gray-200 rounded-md">
                                        <pre className="text-sm text-gray-900 whitespace-pre-wrap">{JSON.stringify(job.progress_details, null, 2)}</pre>
                                    </div>
                                </div>
                            )}
                            {job.error_message && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700">Error Message</label>
                                    <div className="mt-1 p-3 bg-red-50 border border-red-200 rounded-md">
                                        <pre className="text-sm text-red-900 whitespace-pre-wrap">{job.error_message}</pre>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="flex justify-end pt-6">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

// Job Modal Component with Portal Dropdown
const JobModal = ({ onClose, onSubmit, job, setJob, adapters, medications, title, onPortalChange }) => {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden">
                {/* Simplified Header */}
                <div className="bg-gradient-to-r from-blue-600 to-indigo-700 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-xl font-bold text-white">{title}</h3>
                            <p className="text-blue-100 text-sm">Configure data extraction job</p>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-blue-100 hover:text-white transition-colors duration-200 p-2 hover:bg-white hover:bg-opacity-20 rounded-full"
                        >
                            <XMarkIcon className="h-5 w-5" />
                        </button>
                    </div>
                </div>

                {/* Modal Content - Optimized for smaller height */}
                <div className="px-6 py-4 overflow-y-auto max-h-[calc(85vh-100px)]">

                    <form onSubmit={onSubmit} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Job Name <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={job.job_name}
                                    onChange={(e) => setJob(prev => ({ ...prev, job_name: e.target.value }))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="e.g., Patient Data Extraction"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Medical Portal <span className="text-red-500">*</span>
                                </label>
                                <div className="relative">
                                    <select
                                        value={job.portal_name || ''}
                                        onChange={(e) => onPortalChange(e.target.value, setJob)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none pr-10"
                                        required
                                    >
                                        <option value="">Select Medical Portal...</option>
                                        {SUPPORTED_PORTALS.map(portal => (
                                            <option key={portal.name} value={portal.name}>
                                                {portal.name}
                                            </option>
                                        ))}
                                    </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                        <GlobeAltIcon className="h-4 w-4 text-gray-400" />
                                    </div>
                                </div>
                                {job.portal_name && (
                                    <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                        <div className="flex items-center text-sm text-blue-700">
                                            <CheckCircleIcon className="h-4 w-4 mr-2 text-blue-500" />
                                            Portal URL: {job.target_url}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Portal Adapter <span className="text-red-500">*</span>
                                </label>
                                <select
                                    value={job.adapter_id}
                                    onChange={(e) => setJob(prev => ({ ...prev, adapter_id: e.target.value }))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                >
                                    <option value="">Select an adapter</option>
                                    {adapters.map((adapter) => (
                                        <option key={adapter.id} value={adapter.id}>
                                            {adapter.name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Extraction Mode</label>
                                <select
                                    value={job.extraction_mode}
                                    onChange={(e) => setJob(prev => ({ ...prev, extraction_mode: e.target.value }))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                >
                                    <option value="SINGLE_PATIENT">Single Patient</option>
                                    <option value="ALL_PATIENTS">All Patients</option>
                                </select>
                            </div>
                        </div>

                        {job.extraction_mode === 'SINGLE_PATIENT' && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Patient Identifier <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={job.input_patient_identifier}
                                    onChange={(e) => setJob(prev => ({ ...prev, input_patient_identifier: e.target.value }))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="Patient ID, MRN, or search term"
                                    required={job.extraction_mode === 'SINGLE_PATIENT'}
                                />
                            </div>
                        )}

                        {/* Medication Report Parameters */}
                        <div className="border-t pt-4 mt-4">
                            <h4 className="text-lg font-medium text-gray-900 mb-3">Medication Report Parameters</h4>
                            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                <div className="flex items-start">
                                    <svg className="w-5 h-5 text-blue-400 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                    </svg>
                                    <div>
                                        <h5 className="text-sm font-medium text-blue-900 mb-1">Date Format Notice</h5>
                                        <p className="text-sm text-blue-700">
                                            Date inputs use your browser's locale format display, but we process all dates as <strong>MM/DD/YYYY</strong> format internally.
                                            Please enter dates in Month/Day/Year order regardless of how they appear in the picker.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Doctor/Provider Name</label>
                                    <input
                                        type="text"
                                        value={job.doctor_name}
                                        onChange={(e) => setJob(prev => ({ ...prev, doctor_name: e.target.value }))}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="Enter doctor's name"
                                    />
                                    {/* Simplified Case Sensitivity Warning */}
                                    <div className="mt-1 flex items-center space-x-2 p-2 bg-amber-50 border border-amber-200 rounded-md">
                                        <ExclamationTriangleIcon className="h-4 w-4 text-amber-500 flex-shrink-0" />
                                        <p className="text-sm font-medium text-amber-800">Case sensitive</p>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Medication</label>
                                    <SearchableMedicationDropdown
                                        value={job.medication}
                                        onChange={(value) => setJob(prev => ({ ...prev, medication: value }))}
                                        medications={medications}
                                        placeholder="Search for medication..."
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Start Date
                                    </label>
                                    <input
                                        type="date"
                                        value={job.start_date}
                                        onChange={(e) => setJob(prev => ({ ...prev, start_date: e.target.value }))}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        End Date
                                    </label>
                                    <input
                                        type="date"
                                        value={job.end_date}
                                        onChange={(e) => setJob(prev => ({ ...prev, end_date: e.target.value }))}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex space-x-3 pt-4">
                            <button
                                type="button"
                                onClick={onClose}
                                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                Create Job
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

// Batch Jobs Modal Component with Portal Dropdown
const BatchJobsModal = ({ onClose, onSubmit, jobs, adapters, medications, addJob, removeJob, updateJob, onPortalChange }) => {
    const handlePortalChangeForBatch = (index, portalName) => {
        const selectedPortal = SUPPORTED_PORTALS.find(p => p.name === portalName);
        updateJob(index, 'portal_name', portalName);
        updateJob(index, 'target_url', selectedPortal ? selectedPortal.url : '');
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-8 max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-2xl font-bold text-gray-900 flex items-center">
                        <ArrowTrendingUpIcon className="h-7 w-7 text-purple-500 mr-2" />
                        Batch Job Creation
                    </h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <XMarkIcon className="h-6 w-6" />
                    </button>
                </div>

                <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                    <h4 className="font-semibold text-purple-900 mb-2">Batch Operations</h4>
                    <p className="text-purple-700 text-sm">
                        Create multiple extraction jobs at once. Each job will start automatically after creation.
                    </p>
                </div>

                <form onSubmit={onSubmit} className="space-y-6">
                    {jobs.map((job, index) => (
                        <div key={index} className="border border-gray-200 rounded-lg p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h4 className="font-medium text-gray-900">Job #{index + 1}</h4>
                                {jobs.length > 1 && (
                                    <button
                                        type="button"
                                        onClick={() => removeJob(index)}
                                        className="text-red-400 hover:text-red-600"
                                    >
                                        <TrashIcon className="h-5 w-5" />
                                    </button>
                                )}
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Job Name <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={job.job_name}
                                        onChange={(e) => updateJob(index, 'job_name', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                        placeholder={`Batch Job ${index + 1}`}
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Medical Portal <span className="text-red-500">*</span>
                                    </label>
                                    <div className="relative">
                                        <select
                                            value={job.portal_name || ''}
                                            onChange={(e) => handlePortalChangeForBatch(index, e.target.value)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent appearance-none pr-10"
                                            required
                                        >
                                            <option value="">Select Medical Portal...</option>
                                            {SUPPORTED_PORTALS.map(portal => (
                                                <option key={portal.name} value={portal.name}>
                                                    {portal.name}
                                                </option>
                                            ))}
                                        </select>
                                        <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                                            <GlobeAltIcon className="h-4 w-4 text-gray-400" />
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Portal Adapter <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        value={job.adapter_id}
                                        onChange={(e) => updateJob(index, 'adapter_id', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                        required
                                    >
                                        <option value="">Select an adapter</option>
                                        {adapters.map((adapter) => (
                                            <option key={adapter.id} value={adapter.id}>
                                                {adapter.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Extraction Mode</label>
                                    <select
                                        value={job.extraction_mode}
                                        onChange={(e) => updateJob(index, 'extraction_mode', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                    >
                                        <option value="SINGLE_PATIENT">Single Patient</option>
                                        <option value="ALL_PATIENTS">All Patients</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Doctor Name</label>
                                    <input
                                        type="text"
                                        value={job.doctor_name}
                                        onChange={(e) => updateJob(index, 'doctor_name', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                        placeholder="Enter doctor's name"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Medication</label>
                                    <SearchableMedicationDropdown
                                        value={job.medication}
                                        onChange={(value) => updateJob(index, 'medication', value)}
                                        medications={medications}
                                        placeholder="Search for medication..."
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                                {job.extraction_mode === 'SINGLE_PATIENT' && (
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Patient Identifier <span className="text-red-500">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            value={job.input_patient_identifier}
                                            onChange={(e) => updateJob(index, 'input_patient_identifier', e.target.value)}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                            placeholder="Patient ID, MRN, or search term"
                                            required={job.extraction_mode === 'SINGLE_PATIENT'}
                                        />
                                    </div>
                                )}

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Start Date
                                        <span className="ml-2 text-xs font-medium text-purple-600 bg-purple-100 px-2 py-1 rounded">MM/DD/YYYY</span>
                                    </label>
                                    <input
                                        type="date"
                                        value={job.start_date}  // Direct value, no conversion
                                        onChange={(e) => updateJob(index, 'start_date', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        End Date
                                        <span className="ml-2 text-xs font-medium text-purple-600 bg-purple-100 px-2 py-1 rounded">MM/DD/YYYY</span>
                                    </label>
                                    <input
                                        type="date"
                                        value={job.end_date}  // Direct value, no conversion
                                        onChange={(e) => updateJob(index, 'end_date', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                    />
                                </div>
                            </div>
                        </div>
                    ))}

                    <button
                        type="button"
                        onClick={addJob}
                        className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-purple-400 hover:text-purple-600 transition-colors"
                    >
                        <PlusIcon className="h-5 w-5 mx-auto mb-1" />
                        Add Another Job
                    </button>

                    <div className="flex space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-purple-500"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-purple-500"
                        >
                            Create {jobs.length} Job{jobs.length !== 1 ? 's' : ''}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// Delete Confirmation Modal
const DeleteConfirmModal = ({ onClose, onConfirm, jobName }) => {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4">
                <div className="flex items-center mb-6">
                    <ExclamationCircleIcon className="h-8 w-8 text-red-500 mr-3" />
                    <h3 className="text-xl font-bold text-gray-900">Delete Job</h3>
                </div>

                <p className="text-gray-600 mb-6">
                    Are you sure you want to delete "{jobName}"? This action cannot be undone.
                </p>

                <div className="flex space-x-3">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                        Delete
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Jobs;
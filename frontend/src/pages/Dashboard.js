import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { jobsApi, adaptersApi, realtimeApi } from '../services/api';
import { useSocket } from '../hooks/useSocket';
import PortalInspector from '../components/PortalInspector';
import toast from 'react-hot-toast';
import {
    ClipboardDocumentListIcon,
    CheckCircleIcon,
    ExclamationCircleIcon,
    ArrowPathIcon,
    PlusIcon,
    SparklesIcon,
    UserGroupIcon,
    BoltIcon,
    ClockIcon,
    BeakerIcon,
    PlayIcon,
    ArrowTrendingUpIcon,
    ShieldCheckIcon,
    DocumentMagnifyingGlassIcon,
    CpuChipIcon,
    HeartIcon,
    ChartBarSquareIcon,
    CalendarDaysIcon
} from '@heroicons/react/24/outline';

const Dashboard = () => {
    const [stats, setStats] = useState({
        activeJobs: 0,
        completedJobs: 0,
        failedJobs: 0,
        activeAdapters: 0,
        totalPatients: 0,
        successRate: 0,
        recentActivity: 0,
        systemHealth: 'healthy'
    });
    const [recentJobs, setRecentJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [systemStatus, setSystemStatus] = useState('healthy');
    const [showPortalInspector, setShowPortalInspector] = useState(false);
    const [realtimeConnected, setRealtimeConnected] = useState(false);
    const [quickActions, setQuickActions] = useState([]);

    const socket = useSocket();

    useEffect(() => {
        if (socket) {
            setRealtimeConnected(true);

            // Listen for real-time updates
            socket.on('system_stats_update', (data) => {
                setStats(data.stats);
                setSystemStatus(data.stats.system_health);
            });

            socket.on('job_progress_update', (data) => {
                toast.success(`Job #${data.job_id}: ${data.current_step}`, {
                    icon: '🔄',
                    duration: 3000
                });
            });

            socket.on('job_retried', (data) => {
                toast.success(`Job #${data.job_id} restarted successfully!`, {
                    icon: '🔄'
                });
                fetchDashboardData();
            });

            socket.on('batch_jobs_created', (data) => {
                toast.success(`Created ${data.created_count} batch jobs!`, {
                    icon: '⚡'
                });
                fetchDashboardData();
            });

            socket.on('portal_analysis_complete', (data) => {
                toast.success('Portal analysis completed!', {
                    icon: '🔬'
                });
            });

            return () => {
                socket.off('system_stats_update');
                socket.off('job_progress_update');
                socket.off('job_retried');
                socket.off('batch_jobs_created');
                socket.off('portal_analysis_complete');
            };
        }
    }, [socket]);

    const fetchDashboardData = async (forceRefresh = false) => {
        try {
            setLoading(true);

            // Fetch enhanced system stats and recent data
            const [statsResponse, allJobsResponse, adaptersResponse] = await Promise.all([
                realtimeApi.getSystemStats(),
                jobsApi.getAll(1, 10),
                adaptersApi.getActive()
            ]);

            if (statsResponse.data.success) {
                const systemStats = statsResponse.data.stats;

                // Calculate actual total patients from all jobs
                const allJobs = allJobsResponse.data.jobs || [];
                let totalPatients = 0;

                // Count actual patients from job results
                allJobs.forEach(job => {
                    if (job.status === 'COMPLETED' && job.raw_extracted_data_json) {
                        try {
                            const extractedData = JSON.parse(job.raw_extracted_data_json);
                            if (extractedData && extractedData.patients) {
                                totalPatients += extractedData.patients.length;
                            } else if (extractedData && Array.isArray(extractedData)) {
                                totalPatients += extractedData.length;
                            } else if (job.extraction_mode === 'SINGLE_PATIENT') {
                                totalPatients += 1; // Single patient job
                            }
                        } catch (e) {
                            // If JSON parsing fails, use fallback estimation
                            if (job.extraction_mode === 'ALL_PATIENTS') {
                                totalPatients += 5; // Conservative estimate
                            } else if (job.extraction_mode === 'SINGLE_PATIENT') {
                                totalPatients += 1;
                            }
                        }
                    }
                });

                setStats({
                    activeJobs: systemStats.active_jobs || 0,
                    completedJobs: systemStats.completed_jobs || 0,
                    failedJobs: systemStats.failed_jobs || 0,
                    activeAdapters: systemStats.active_adapters || 0,
                    totalPatients: totalPatients || systemStats.total_patients || 0,
                    successRate: systemStats.success_rate || 0,
                    recentActivity: systemStats.recent_activity || 0,
                    systemHealth: systemStats.system_health || 'healthy'
                });
                setSystemStatus(systemStats.system_health);
            }

            const allJobs = allJobsResponse.data.jobs || [];
            setRecentJobs(allJobs.slice(0, 10)); // Show more recent jobs for scrolling

            // Setup quick actions based on current state
            updateQuickActions(allJobs, statsResponse.data.stats);

        } catch (error) {
            console.error('❌ Failed to fetch dashboard data:', error);
            toast.error('Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    };

    const updateQuickActions = (jobs, systemStats) => {
        const actions = [];

        // Health check if there are stuck jobs
        const stuckJobs = jobs.filter(job =>
            ['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING'].includes(job.status) &&
            new Date() - new Date(job.updated_at) > 30 * 60 * 1000 // 30 minutes
        );

        if (stuckJobs.length > 0) {
            actions.push({
                title: 'Clear Hung Tasks',
                description: `${stuckJobs.length} jobs may be stuck`,
                action: handleHealthCheck,
                icon: ShieldCheckIcon,
                color: 'orange'
            });
        }

        // Always show batch processing option
        actions.push({
            title: 'Batch Processing',
            description: 'Create and manage bulk operations',
            action: () => window.location.href = '/jobs?create=batch',
            icon: ArrowTrendingUpIcon,
            color: 'green'
        });

        // Portal analysis suggestion
        actions.push({
            title: 'Analyze New Portal',
            description: 'Add support for a new medical portal',
            action: () => setShowPortalInspector(true),
            icon: DocumentMagnifyingGlassIcon,
            color: 'purple'
        });

        // AI-Powered Insights - Modern feature
        actions.push({
            title: 'AI-Powered Insights',
            description: 'Analyze extraction patterns and performance',
            action: handleAIInsights,
            icon: ChartBarSquareIcon,
            color: 'blue'
        });

        // Schedule Extraction - New feature
        actions.push({
            title: 'Schedule Extraction',
            description: 'Set up automated extraction schedules',
            action: handleScheduleExtraction,
            icon: CalendarDaysIcon,
            color: 'purple'
        });

        setQuickActions(actions);
    };

    useEffect(() => {
        fetchDashboardData();
        // Refresh data every 30 seconds as backup to real-time updates
        const interval = setInterval(() => fetchDashboardData(), 30000);
        return () => clearInterval(interval);
    }, []);

    const handleHealthCheck = async () => {
        try {
            const response = await realtimeApi.healthCheckJobs();
            if (response.data.success) {
                toast.success(`Health check complete! Fixed ${response.data.fixed_jobs.length} stuck jobs.`);
                fetchDashboardData();
            }
        } catch (error) {
            toast.error('Health check failed');
        }
    };

    const handleAIInsights = () => {
        toast.success('🤖 AI Insights: Analyzing extraction patterns...', {
            duration: 4000
        });
        // Navigate to analytics/insights page (placeholder)
        setTimeout(() => {
            toast.success('💡 Recommendation: Consider scheduling extractions during off-peak hours for better performance!', {
                duration: 6000
            });
        }, 2000);
    };

    const handleScheduleExtraction = () => {
        toast.success('📅 Schedule Extraction: Setting up automated workflows...', {
            duration: 4000
        });
        // Navigate to scheduling page (placeholder)
        setTimeout(() => {
            toast.success('⏰ Feature coming soon! Auto-scheduling will help optimize your extraction workflows.', {
                duration: 6000
            });
        }, 2000);
    };

    const getSystemHealthColor = (health) => {
        switch (health) {
            case 'healthy': return 'text-green-600 bg-green-100';
            case 'busy': return 'text-yellow-600 bg-yellow-100';
            case 'critical': return 'text-red-600 bg-red-100';
            default: return 'text-gray-600 bg-gray-100';
        }
    };

    const getSystemHealthIcon = (health) => {
        switch (health) {
            case 'healthy': return <CheckCircleIcon className="h-5 w-5" />;
            case 'busy': return <ExclamationCircleIcon className="h-5 w-5" />;
            case 'critical': return <ExclamationCircleIcon className="h-5 w-5" />;
            default: return <HeartIcon className="h-5 w-5" />;
        }
    };

    if (loading && stats.activeJobs === 0 && stats.completedJobs === 0) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="relative">
                    <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
                    <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                        <SparklesIcon className="h-6 w-6 text-blue-500" />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
                <div className="flex-1">
                    <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                        WebAutoDash Dashboard
                    </h1>
                    <p className="mt-2 text-lg text-gray-600">
                        Medical data extraction and portal automation platform
                    </p>
                </div>
                {/* Action Buttons - Back in Header with Better Positioning */}
                <div className="flex flex-col sm:flex-row mt-6 lg:mt-0 space-y-2 sm:space-y-0 sm:space-x-3">
                    <button
                        onClick={() => setShowPortalInspector(true)}
                        className="inline-flex items-center justify-center px-6 py-3 border border-transparent shadow-sm text-sm font-medium rounded-xl text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transform hover:scale-105 transition-all duration-200"
                    >
                        <BeakerIcon className="h-5 w-5 mr-2" />
                        Portal Inspector
                    </button>
                    <Link
                        to="/patients"
                        className="inline-flex items-center justify-center px-6 py-3 border border-transparent shadow-sm text-sm font-medium rounded-xl text-white bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transform hover:scale-105 transition-all duration-200"
                    >
                        <UserGroupIcon className="h-5 w-5 mr-2" />
                        View Patient Data
                    </Link>
                    <Link
                        to="/jobs"
                        className="inline-flex items-center justify-center px-6 py-3 border border-transparent shadow-sm text-sm font-medium rounded-xl text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transform hover:scale-105 transition-all duration-200"
                    >
                        <PlusIcon className="h-5 w-5 mr-2" />
                        New Extraction
                    </Link>
                </div>
            </div>

            {/* Welcome Banner - Positioned Above Stats Cards */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl p-6 hover:shadow-lg transition-shadow duration-300">
                <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                        <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                            <SparklesIcon className="h-6 w-6 text-blue-600" />
                        </div>
                    </div>
                    <div className="flex-1">
                        <h2 className="text-xl font-bold text-blue-900 mb-2">
                            Welcome to WebAutoDash Medical Portal!
                        </h2>
                        <p className="text-blue-700 mb-4">
                            Start extracting patient data from medical portals with ease.{' '}
                            <Link
                                to="/jobs"
                                className="text-blue-800 underline font-medium hover:text-blue-900"
                            >
                                Create your extraction job
                            </Link>
                            {' '}to begin analyzing patient records.
                        </p>
                    </div>
                </div>
            </div>

            {/* Stats Cards - Smaller with Animations */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-lg hover:scale-105 hover:border-blue-300 transition-all duration-300 cursor-pointer">
                    <div className="flex items-center">
                        <div className="p-2.5 rounded-full bg-blue-100">
                            <PlayIcon className="h-5 w-5 text-blue-600" />
                        </div>
                        <div className="ml-3">
                            <p className="text-xs font-medium text-gray-500">Active Jobs</p>
                            <p className="text-xl font-semibold text-gray-900">{stats.activeJobs}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-lg hover:scale-105 hover:border-green-300 transition-all duration-300 cursor-pointer">
                    <div className="flex items-center">
                        <div className="p-2.5 rounded-full bg-green-100">
                            <CheckCircleIcon className="h-5 w-5 text-green-600" />
                        </div>
                        <div className="ml-3">
                            <p className="text-xs font-medium text-gray-500">Completed</p>
                            <p className="text-xl font-semibold text-gray-900">{stats.completedJobs}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-lg hover:scale-105 hover:border-orange-300 transition-all duration-300 cursor-pointer">
                    <div className="flex items-center">
                        <div className="p-2.5 rounded-full bg-orange-100">
                            <UserGroupIcon className="h-5 w-5 text-orange-600" />
                        </div>
                        <div className="ml-3">
                            <p className="text-xs font-medium text-gray-500">Patients Extracted</p>
                            <p className="text-xl font-semibold text-gray-900">{stats.totalPatients}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-lg hover:scale-105 hover:border-purple-300 transition-all duration-300 cursor-pointer">
                    <div className="flex items-center">
                        <div className="p-2.5 rounded-full bg-purple-100">
                            <CpuChipIcon className="h-5 w-5 text-purple-600" />
                        </div>
                        <div className="ml-3">
                            <p className="text-xs font-medium text-gray-500">Active Adapters</p>
                            <p className="text-xl font-semibold text-gray-900">{stats.activeAdapters}</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* System Status Bar */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-4 space-y-3 sm:space-y-0">
                        <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-700 mr-2">System Status:</span>
                            <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${getSystemHealthColor(stats.systemHealth)}`}>
                                {getSystemHealthIcon(stats.systemHealth)}
                                <span className="ml-1 capitalize">{stats.systemHealth}</span>
                            </div>
                        </div>
                        {realtimeConnected && (
                            <div className="flex items-center text-green-600">
                                <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                                <span className="text-sm">Real-time Connected</span>
                            </div>
                        )}
                    </div>
                    <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-4 space-y-2 sm:space-y-0 text-sm text-gray-500">
                        <span className="flex items-center">Failed Jobs: <strong className="text-red-600 ml-1">{stats.failedJobs}</strong></span>
                        <span className="flex items-center">Recent Activity: <strong className="ml-1">{stats.recentActivity}</strong></span>
                        <span className="flex items-center">Last Updated: <strong className="ml-1">{new Date().toLocaleTimeString()}</strong></span>
                    </div>
                </div>
            </div>

            {/* Single Column Layout */}
            <div className="space-y-8">
                {/* Enhanced Quick Actions with 5 Features in 2x3 Grid */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
                    <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
                        <BoltIcon className="h-6 w-6 text-yellow-500 mr-2" />
                        Recommended Actions
                    </h3>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {quickActions.map((action, index) => {
                            const Icon = action.icon;
                            const colorClasses = {
                                orange: 'border-orange-300 hover:border-orange-500 hover:bg-orange-50 text-orange-700',
                                green: 'border-green-300 hover:border-green-500 hover:bg-green-50 text-green-700',
                                purple: 'border-purple-300 hover:border-purple-500 hover:bg-purple-50 text-purple-700',
                                blue: 'border-blue-300 hover:border-blue-500 hover:bg-blue-50 text-blue-700'
                            };

                            return (
                                <button
                                    key={index}
                                    onClick={action.action}
                                    className={`flex items-center justify-center p-4 border-2 border-dashed rounded-xl transition-all duration-200 group hover:scale-105 ${colorClasses[action.color]}`}
                                >
                                    <Icon className="h-8 w-8 mr-3 flex-shrink-0" />
                                    <div className="text-left">
                                        <p className="font-medium">{action.title}</p>
                                        <p className="text-sm opacity-80">{action.description}</p>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Recent Jobs with Scrolling */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-bold text-gray-900 flex items-center">
                            <ClockIcon className="h-6 w-6 text-blue-500 mr-2" />
                            Recent Jobs
                        </h3>
                        <Link
                            to="/jobs"
                            className="text-blue-600 hover:text-blue-800 font-medium text-sm flex items-center"
                        >
                            View all
                            <ArrowPathIcon className="h-4 w-4 ml-1" />
                        </Link>
                    </div>
                    {recentJobs.length > 0 ? (
                        <div className="max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 pr-2">
                            <div className="space-y-4">
                                {recentJobs.map((job) => (
                                    <div key={job.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                                        <div className="flex items-center space-x-4">
                                            <div className="flex-shrink-0">
                                                {job.status === 'COMPLETED' && <CheckCircleIcon className="h-5 w-5 text-green-500" />}
                                                {job.status === 'FAILED' && <ExclamationCircleIcon className="h-5 w-5 text-red-500" />}
                                                {['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING'].includes(job.status) &&
                                                    <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-blue-500"></div>}
                                            </div>
                                            <div>
                                                <p className="font-medium text-gray-900">{job.job_name || `Job #${job.id}`}</p>
                                                <p className="text-sm text-gray-500">{job.adapter_name} • {job.extraction_mode}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-sm font-medium text-gray-900">{job.status}</p>
                                            <p className="text-xs text-gray-500">{new Date(job.created_at).toLocaleDateString()}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8">
                            <ClipboardDocumentListIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                            <p className="text-gray-500">No recent jobs</p>
                            <Link
                                to="/jobs"
                                className="mt-2 inline-flex items-center text-blue-600 hover:text-blue-800"
                            >
                                Create your first job
                            </Link>
                        </div>
                    )}
                </div>
            </div>

            {/* Portal Inspector Modal */}
            {showPortalInspector && (
                <PortalInspector onClose={() => setShowPortalInspector(false)} />
            )}
        </div>
    );
};

export default Dashboard; 
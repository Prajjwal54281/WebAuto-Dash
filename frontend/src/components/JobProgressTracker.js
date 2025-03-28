import React, { useState, useEffect } from 'react';
import { realtimeApi } from '../services/api';
import { useSocket } from '../hooks/useSocket';
import toast from 'react-hot-toast';
import {
    CheckCircleIcon,
    ExclamationCircleIcon,
    ArrowPathIcon,
    PlayIcon,
    StopIcon,
    ClockIcon,
    CpuChipIcon,
    EyeIcon,
    BoltIcon,
    TrashIcon,
    UserIcon
} from '@heroicons/react/24/outline';

const JobProgressTracker = ({ job, onJobUpdate, onDelete, onConfirmLogin, isExpanded = false, onToggleExpansion }) => {
    const [progress, setProgress] = useState({
        progress: 0,
        current_step: 'Initializing...',
        steps_completed: 0,
        total_steps: 5
    });
    const [isRetrying, setIsRetrying] = useState(false);
    const [isCancelling, setIsCancelling] = useState(false);

    const socket = useSocket();

    useEffect(() => {
        // Fetch initial progress
        fetchJobProgress();

        if (socket) {
            // Listen for real-time progress updates
            socket.on('job_progress_update', (data) => {
                if (data.job_id === job.id) {
                    setProgress(data);
                }
            });

            socket.on('job_retried', (data) => {
                if (data.job_id === job.id) {
                    setIsRetrying(false);
                    if (onJobUpdate) onJobUpdate();
                }
            });

            socket.on('job_cancelled', (data) => {
                if (data.job_id === job.id) {
                    setIsCancelling(false);
                    if (onJobUpdate) onJobUpdate();
                }
            });

            return () => {
                socket.off('job_progress_update');
                socket.off('job_retried');
                socket.off('job_cancelled');
            };
        }
    }, [socket, job.id, onJobUpdate]);

    const fetchJobProgress = async () => {
        try {
            const response = await realtimeApi.getJobProgress(job.id);
            if (response.data.success) {
                setProgress(response.data.progress);
            }
        } catch (error) {
            console.error('Failed to fetch job progress:', error);
        }
    };

    const handleRetryJob = async () => {
        setIsRetrying(true);
        try {
            await realtimeApi.retryJob(job.id);
            toast.success('Job restart initiated!');
        } catch (error) {
            toast.error('Failed to restart job');
            setIsRetrying(false);
        }
    };

    const handleCancelJob = async () => {
        setIsCancelling(true);
        try {
            const response = await realtimeApi.cancelJob(job.id);
            if (response.data && response.data.success) {
                toast.success('Job cancellation initiated! Browser will close shortly...');
                // Keep the cancelling state until the job status updates
                // Don't reset isCancelling here - let the socket update handle it
            } else {
                throw new Error(response.data?.message || 'Failed to cancel job');
            }
        } catch (error) {
            console.error('Failed to cancel job:', error);
            toast.error('Failed to cancel job: ' + (error.response?.data?.message || error.message));
            setIsCancelling(false);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'COMPLETED': return 'text-emerald-800 bg-emerald-100 border border-emerald-200';
            case 'FAILED': return 'text-red-800 bg-red-100 border border-red-200';
            case 'PENDING_LOGIN': case 'LAUNCHING_BROWSER': case 'AWAITING_USER_CONFIRMATION': case 'EXTRACTING':
                return 'text-blue-800 bg-blue-100 border border-blue-200';
            default: return 'text-gray-800 bg-gray-100 border border-gray-200';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'COMPLETED': return <CheckCircleIcon className="h-5 w-5" />;
            case 'FAILED': return <ExclamationCircleIcon className="h-5 w-5" />;
            case 'PENDING_LOGIN': case 'LAUNCHING_BROWSER': case 'AWAITING_USER_CONFIRMATION': case 'EXTRACTING':
                return <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-blue-500"></div>;
            default: return <ClockIcon className="h-5 w-5" />;
        }
    };

    const isJobActive = (status) => {
        return ['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING'].includes(status);
    };

    const isJobFinished = (status) => {
        return ['COMPLETED', 'FAILED'].includes(status);
    };

    const progressPercentage = Math.round((progress.steps_completed / progress.total_steps) * 100);

    return (
        <div className="bg-white border border-gray-100 rounded-2xl p-6 hover:shadow-xl shadow-lg transition-all duration-300 hover:transform hover:scale-105">
            {/* Job Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3 min-w-0 flex-1">
                    <div className={`p-2 rounded-lg ${getStatusColor(job.status)}`}>
                        {getStatusIcon(job.status)}
                    </div>
                    <div className="min-w-0 flex-1">
                        <h3 className="font-semibold text-gray-900 truncate">
                            {job.job_name || `Job #${job.id}`}
                        </h3>
                        <p className="text-sm text-gray-600 truncate">
                            {job.adapter_name} • {job.extraction_mode}
                        </p>
                    </div>
                </div>

                <div className="flex items-center space-x-1 flex-shrink-0">
                    {onToggleExpansion && (
                        <button
                            onClick={onToggleExpansion}
                            className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                            title="Toggle Details"
                        >
                            <EyeIcon className="h-4 w-4" />
                        </button>
                    )}
                </div>
            </div>

            {/* Prominent Action Buttons for AWAITING_USER_CONFIRMATION */}
            {job.status === 'AWAITING_USER_CONFIRMATION' && onConfirmLogin && (
                <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center">
                                <UserIcon className="h-5 w-5 text-amber-600" />
                            </div>
                            <div>
                                <p className="font-medium text-amber-900">User Action Required</p>
                                <p className="text-sm text-amber-700">Please confirm your login to continue extraction</p>
                            </div>
                        </div>
                        <button
                            onClick={() => onConfirmLogin(job.id)}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 font-medium text-sm"
                        >
                            Confirm Login
                        </button>
                    </div>
                </div>
            )}

            {/* Progress Bar for Active Jobs */}
            {isJobActive(job.status) && (
                <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700 truncate flex-1 pr-2">
                            {progress.current_step}
                        </span>
                        <span className="text-sm text-gray-500 flex-shrink-0">
                            {progress.steps_completed}/{progress.total_steps} steps
                        </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 shadow-inner">
                        <div
                            className="bg-gradient-to-r from-blue-500 to-indigo-600 h-3 rounded-full transition-all duration-500 shadow-sm"
                            style={{ width: `${progressPercentage}%` }}
                        />
                    </div>
                </div>
            )}

            {/* Status and Basic Info */}
            <div className="flex items-center justify-between mb-3">
                <div>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                        {job.status.replace(/_/g, ' ')}
                    </span>
                </div>
                <div className="text-right">
                    <p className="text-xs text-gray-500">
                        Created: {new Date(job.created_at).toLocaleDateString()}
                    </p>
                    {job.updated_at && (
                        <p className="text-xs text-gray-500">
                            Updated: {new Date(job.updated_at).toLocaleTimeString()}
                        </p>
                    )}
                </div>
            </div>

            {/* Action Buttons Row */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-200">
                <div className="flex items-center space-x-2">
                    {/* Cancel Button for Active Jobs */}
                    {isJobActive(job.status) && (
                        <button
                            onClick={handleCancelJob}
                            disabled={isCancelling}
                            className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                        >
                            {isCancelling ? (
                                <ArrowPathIcon className="h-4 w-4 mr-1 animate-spin" />
                            ) : (
                                <StopIcon className="h-4 w-4 mr-1" />
                            )}
                            Cancel
                        </button>
                    )}

                    {/* Retry Button for Failed Jobs */}
                    {job.status === 'FAILED' && (
                        <button
                            onClick={handleRetryJob}
                            disabled={isRetrying}
                            className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                        >
                            {isRetrying ? (
                                <ArrowPathIcon className="h-4 w-4 mr-1 animate-spin" />
                            ) : (
                                <PlayIcon className="h-4 w-4 mr-1" />
                            )}
                            Retry
                        </button>
                    )}

                    {/* Delete Button for Finished Jobs */}
                    {isJobFinished(job.status) && onDelete && (
                        <button
                            onClick={() => onDelete(job)}
                            className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                        >
                            <TrashIcon className="h-4 w-4 mr-1" />
                            Delete
                        </button>
                    )}
                </div>

                {onToggleExpansion && (
                    <button
                        onClick={onToggleExpansion}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                        {isExpanded ? 'Hide Details' : 'Show Details'}
                    </button>
                )}
            </div>

            {/* Expandable Details */}
            {isExpanded && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="space-y-3">
                        {job.target_url && (
                            <div>
                                <p className="text-xs font-medium text-gray-500">Target URL:</p>
                                <p className="text-sm text-gray-900 break-all">{job.target_url}</p>
                            </div>
                        )}

                        {job.input_patient_identifier && (
                            <div>
                                <p className="text-xs font-medium text-gray-500">Patient ID:</p>
                                <p className="text-sm text-gray-900">{job.input_patient_identifier}</p>
                            </div>
                        )}

                        {job.error_message && (
                            <div>
                                <p className="text-xs font-medium text-red-500">Error Message:</p>
                                <div className="text-sm text-red-700 bg-red-50 p-3 rounded border-l-4 border-red-400 max-h-40 overflow-y-auto">
                                    <pre className="whitespace-pre-wrap break-words text-xs font-mono">
                                        {job.error_message}
                                    </pre>
                                </div>
                            </div>
                        )}

                        {isJobActive(job.status) && (
                            <div>
                                <p className="text-xs font-medium text-gray-500">Current Progress:</p>
                                <p className="text-sm text-blue-700 break-words">{progress.current_step}</p>
                                <div className="mt-2">
                                    <div className="text-xs text-gray-500 mb-1">
                                        Progress: {progressPercentage}% ({progress.steps_completed}/{progress.total_steps} steps)
                                    </div>
                                </div>
                            </div>
                        )}

                        {job.raw_extracted_data_json && (
                            <div>
                                <p className="text-xs font-medium text-green-500">Extraction Completed:</p>
                                <p className="text-sm text-green-700">Data successfully extracted</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default JobProgressTracker; 
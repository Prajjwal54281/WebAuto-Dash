import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adaptersApi, clearApiCache, portalInspectorApi } from '../services/api';
import toast from 'react-hot-toast';
import {
    CheckCircleIcon,
    XCircleIcon,
    ArrowPathIcon,
    PlayIcon,
    DocumentTextIcon,
    CloudArrowUpIcon,
    TrashIcon,
    ExclamationTriangleIcon,
    XMarkIcon
} from '@heroicons/react/24/outline';

const Adapters = () => {
    const [adapters, setAdapters] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [syncing, setSyncing] = useState(false);
    const [refreshing, setRefreshing] = useState(false);

    // Simplified delete modal state
    const [deleteModal, setDeleteModal] = useState({
        show: false,
        adapter: null
    });
    const [deleteInput, setDeleteInput] = useState('');
    const [deleting, setDeleting] = useState(false);

    // Job conflict modal state
    const [jobConflictModal, setJobConflictModal] = useState({
        show: false,
        adapter: null,
        jobs: []
    });

    const navigate = useNavigate();

    useEffect(() => {
        fetchAdapters();
    }, []);

    const fetchAdapters = async (forceRefresh = false) => {
        try {
            if (!forceRefresh) {
                setLoading(true);
            } else {
                setRefreshing(true);
            }
            setError(null);

            console.log('🔄 Fetching adapters, forceRefresh:', forceRefresh);

            if (forceRefresh) {
                clearApiCache();
                await new Promise(resolve => setTimeout(resolve, 100));
            }

            const noCacheHeaders = forceRefresh ? {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            } : null;

            const response = await adaptersApi.getActive(noCacheHeaders);
            console.log('📡 Adapters API response:', response);

            if (response.data && response.data.adapters) {
                const newAdapters = response.data.adapters;
                console.log(`📋 Updating adapters: ${adapters.length} → ${newAdapters.length}`);
                setAdapters(newAdapters);

                if (forceRefresh) {
                    console.log('🔄 Force refresh completed successfully');
                }
            } else {
                console.error('❌ Invalid response structure:', response.data);
                setError('Invalid response from server. Please try again.');
            }
        } catch (error) {
            console.error('❌ Failed to fetch adapters:', error);
            const errorMessage = error.response?.data?.detail || error.response?.data?.error || error.message;
            setError(`Failed to load portal adapters: ${errorMessage}. Please try again.`);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const handleSyncAdapters = async () => {
        try {
            setSyncing(true);
            console.log('🔄 Starting adapter sync...');

            clearApiCache();
            await new Promise(resolve => setTimeout(resolve, 100));

            const response = await portalInspectorApi.syncAdapters();
            console.log('📡 Sync response:', response.data);

            if (response.data.success) {
                const {
                    synced_count,
                    new_adapters = [],
                    updated_adapters = [],
                    removed_adapters = [],
                    unchanged_adapters = []
                } = response.data;

                let messages = [];
                if (new_adapters.length > 0) {
                    messages.push(`Added ${new_adapters.length} new adapter(s)`);
                }
                if (updated_adapters.length > 0) {
                    messages.push(`Updated ${updated_adapters.length} adapter(s)`);
                }
                if (removed_adapters.length > 0) {
                    messages.push(`Removed ${removed_adapters.length} deleted adapter(s)`);
                }
                if (unchanged_adapters.length > 0) {
                    messages.push(`${unchanged_adapters.length} adapter(s) unchanged`);
                }

                if (messages.length > 0) {
                    toast.success(`Sync complete! ${messages.join(', ')}`, { duration: 4000 });
                } else {
                    toast.success('All adapters are already in sync!');
                }

                console.log('🔄 Refreshing adapter list after sync...');
                clearApiCache();
                await new Promise(resolve => setTimeout(resolve, 500));
                await fetchAdapters(true);
            } else {
                toast.error(`Sync failed: ${response.data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('❌ Failed to sync adapters:', error);
            const errorMessage = error.response?.data?.detail || error.response?.data?.error || error.message;
            toast.error(`Failed to sync adapters: ${errorMessage}`);
        } finally {
            setSyncing(false);
        }
    };

    const handleForceRefresh = async () => {
        try {
            console.log('🔄 Starting force refresh...');
            await fetchAdapters(true);
            toast.success('Adapters refreshed successfully!');
        } catch (error) {
            console.error('❌ Force refresh failed:', error);
            toast.error('Failed to refresh adapters');
        }
    };

    // Simplified delete functionality - using adapter display name
    const handleDeleteAdapter = (adapter) => {
        setDeleteModal({
            show: true,
            adapter: adapter
        });
        setDeleteInput('');
    };

    const confirmDeleteAdapter = async () => {
        const adapter = deleteModal.adapter;
        if (!adapter) return;

        // Check that user typed the exact adapter name
        if (deleteInput !== adapter.name) {
            toast.error('Please type the exact adapter name to confirm deletion');
            return;
        }

        try {
            setDeleting(true);
            console.log('🗑️ Deleting adapter:', adapter.name);

            const response = await portalInspectorApi.deleteAdapter(adapter.id);

            if (response.data.success) {
                toast.success(`Adapter "${adapter.name}" deleted successfully!`);

                // Remove from local state
                setAdapters(prev => prev.filter(a => a.id !== adapter.id));

                // Close modal
                closeDeleteModal();
            } else {
                const errorMessage = response.data.error || 'Unknown error';

                // Check if the error is about associated jobs
                if (response.data.associated_jobs && response.data.associated_jobs.length > 0) {
                    setJobConflictModal({
                        show: true,
                        adapter: adapter,
                        jobs: response.data.associated_jobs
                    });
                    closeDeleteModal();
                } else {
                    toast.error(`Failed to delete adapter: ${errorMessage}`);
                }
            }
        } catch (error) {
            console.error('❌ Failed to delete adapter:', error);
            const errorMessage = error.response?.data?.detail || error.response?.data?.error || error.message;

            if (error.response?.status === 404) {
                toast.error('Adapter not found. It may have already been deleted.');
                setAdapters(prev => prev.filter(a => a.id !== adapter.id));
                closeDeleteModal();
            } else if (error.response?.status === 400 && error.response?.data?.associated_jobs) {
                // Handle job conflict error
                setJobConflictModal({
                    show: true,
                    adapter: adapter,
                    jobs: error.response.data.associated_jobs
                });
                closeDeleteModal();
            } else {
                toast.error(`Failed to delete adapter: ${errorMessage}`);
            }
        } finally {
            setDeleting(false);
        }
    };

    const closeDeleteModal = () => {
        setDeleteModal({
            show: false,
            adapter: null
        });
        setDeleteInput('');
    };

    const closeJobConflictModal = () => {
        setJobConflictModal({
            show: false,
            adapter: null,
            jobs: []
        });
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
                <span className="ml-4 text-gray-600">Loading portal adapters...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <div className="flex">
                    <XCircleIcon className="h-5 w-5 text-red-400" />
                    <div className="ml-3">
                        <h3 className="text-sm font-medium text-red-800">Error</h3>
                        <p className="mt-1 text-sm text-red-700">{error}</p>
                        <button
                            onClick={() => fetchAdapters(true)}
                            className="mt-2 text-sm text-red-600 hover:text-red-500 underline"
                        >
                            Try again
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Portal Adapters</h1>
                    <p className="mt-2 text-gray-600">
                        Manage portal adapters for automated data extraction from medical portals
                    </p>
                </div>
                <div className="flex space-x-3">
                    <button
                        onClick={handleSyncAdapters}
                        disabled={syncing || refreshing}
                        className="inline-flex items-center px-4 py-2 border border-green-300 text-sm font-medium rounded-md shadow-sm text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Sync adapter files from filesystem to database"
                    >
                        {syncing ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-green-500 mr-2"></div>
                        ) : (
                            <CloudArrowUpIcon className="h-4 w-4 mr-2" />
                        )}
                        {syncing ? 'Syncing...' : 'Sync Adapters'}
                    </button>
                    <button
                        onClick={handleForceRefresh}
                        disabled={syncing || refreshing}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Force refresh adapter list from database"
                    >
                        {refreshing ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-blue-500 mr-2"></div>
                        ) : (
                            <ArrowPathIcon className="h-4 w-4 mr-2" />
                        )}
                        {refreshing ? 'Refreshing...' : 'Refresh'}
                    </button>
                    <button
                        onClick={() => navigate('/jobs')}
                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                        <PlayIcon className="h-4 w-4 mr-2" />
                        Create New Job
                    </button>
                </div>
            </div>

            {/* Stats Card */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="flex items-center">
                                <DocumentTextIcon className="h-8 w-8 text-blue-500 mr-3" />
                                <div>
                                    <p className="text-sm font-medium text-gray-500">Portal Adapters</p>
                                    <p className="text-3xl font-bold text-gray-900">{adapters.length}</p>
                                </div>
                            </div>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-gray-500">Active</p>
                            <p className="text-2xl font-semibold text-green-600">
                                {adapters.filter(a => a.is_active).length}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Adapters List */}
            <div className="bg-white shadow overflow-hidden sm:rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                        Available Portal Adapters
                    </h3>
                    <p className="mt-1 text-sm text-gray-500">
                        Portal adapters configured for data extraction from medical portals
                    </p>
                </div>

                {adapters.length === 0 ? (
                    <div className="text-center py-12">
                        <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
                        <h3 className="mt-2 text-sm font-medium text-gray-900">No portal adapters</h3>
                        <p className="mt-1 text-sm text-gray-500">
                            No portal adapters have been configured yet. Try syncing from filesystem.
                        </p>
                        <div className="mt-6">
                            <button
                                onClick={handleSyncAdapters}
                                disabled={syncing || refreshing}
                                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {syncing ? (
                                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                                ) : (
                                    <CloudArrowUpIcon className="h-4 w-4 mr-2" />
                                )}
                                {syncing ? 'Syncing...' : 'Sync Adapters'}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-200">
                        {adapters.map((adapter) => (
                            <div key={adapter.id} className="px-6 py-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center">
                                        <div className="flex-shrink-0">
                                            {adapter.is_active ? (
                                                <CheckCircleIcon className="h-6 w-6 text-green-400" />
                                            ) : (
                                                <XCircleIcon className="h-6 w-6 text-red-400" />
                                            )}
                                        </div>
                                        <div className="ml-4">
                                            <div className="flex items-center">
                                                <h4 className="text-lg font-medium text-gray-900">
                                                    {adapter.name}
                                                </h4>
                                                <span className={`ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${adapter.is_active
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-red-100 text-red-800'
                                                    }`}>
                                                    {adapter.is_active ? 'Active' : 'Inactive'}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-600 mt-1">
                                                {adapter.description || 'No description available'}
                                            </p>
                                            <div className="mt-2 flex items-center text-sm text-gray-500">
                                                <DocumentTextIcon className="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" />
                                                <span className="truncate mr-4">{adapter.script_filename}</span>
                                                <span>•</span>
                                                <span className="ml-4">Created {formatDate(adapter.created_at)}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-3">
                                        <button
                                            onClick={() => navigate(`/jobs?adapter=${adapter.id}`)}
                                            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                            title="Use this adapter to create a new job"
                                        >
                                            <PlayIcon className="h-4 w-4 mr-2" />
                                            Use Adapter
                                        </button>
                                        <button
                                            onClick={() => handleDeleteAdapter(adapter)}
                                            disabled={deleting}
                                            className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                            title="Delete this adapter"
                                        >
                                            {deleting ? (
                                                <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-red-500"></div>
                                            ) : (
                                                <TrashIcon className="h-4 w-4" />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Usage Instructions */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <div className="flex">
                    <div className="flex-shrink-0">
                        <DocumentTextIcon className="h-5 w-5 text-blue-400" />
                    </div>
                    <div className="ml-3">
                        <h3 className="text-sm font-medium text-blue-800">
                            How to Use Portal Adapters
                        </h3>
                        <div className="mt-2 text-sm text-blue-700">
                            <ol className="list-decimal list-inside space-y-1">
                                <li>Select an active portal adapter from the list above</li>
                                <li>Click "Use Adapter" to create a new extraction job</li>
                                <li>Configure the job parameters (portal, extraction mode, patient ID if needed)</li>
                                <li>Start the job and follow the login instructions</li>
                                <li>Monitor the extraction progress and view results</li>
                            </ol>
                        </div>
                    </div>
                </div>
            </div>

            {/* Simplified Delete Confirmation Modal */}
            {deleteModal.show && (
                <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
                    <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                        <div className="px-6 py-4">
                            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full mb-4">
                                <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
                            </div>
                            <h3 className="text-lg font-medium text-gray-900 text-center mb-4">
                                Delete Adapter
                            </h3>

                            <p className="text-sm text-gray-500 text-center mb-4">
                                Are you sure you want to delete the adapter "{deleteModal.adapter?.name}"?
                                This action cannot be undone.
                            </p>

                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Type the adapter name to confirm:
                                </label>
                                <div className="bg-gray-100 p-2 rounded text-sm font-mono text-gray-800 mb-2">
                                    {deleteModal.adapter?.name}
                                </div>
                                <input
                                    type="text"
                                    value={deleteInput}
                                    onChange={(e) => setDeleteInput(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                                    placeholder="Enter adapter name"
                                    autoComplete="off"
                                />
                            </div>

                            <div className="flex justify-end space-x-3">
                                <button
                                    onClick={closeDeleteModal}
                                    disabled={deleting}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={confirmDeleteAdapter}
                                    disabled={deleting || deleteInput !== deleteModal.adapter?.name}
                                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {deleting ? (
                                        <>
                                            <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2 inline-block"></div>
                                            Deleting...
                                        </>
                                    ) : (
                                        'Delete Adapter'
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Enhanced Job Conflict Error Modal */}
            {jobConflictModal.show && (
                <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
                    <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">

                        {/* Red Gradient Header */}
                        <div className="bg-gradient-to-r from-red-600 to-red-700 px-6 py-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h3 className="text-xl font-bold text-white">Cannot Delete Adapter</h3>
                                    <p className="text-red-100 text-sm mt-1">This adapter has active or associated jobs</p>
                                </div>
                                <button
                                    onClick={closeJobConflictModal}
                                    className="text-red-100 hover:text-white transition-colors duration-200 p-2 hover:bg-white hover:bg-opacity-20 rounded-full"
                                >
                                    <XMarkIcon className="h-6 w-6" />
                                </button>
                            </div>
                        </div>

                        {/* Modal Content */}
                        <div className="px-6 py-4 overflow-y-auto max-h-[calc(90vh-120px)]">

                            {/* Error Explanation */}
                            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                                <div className="flex items-start">
                                    <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" />
                                    <div>
                                        <h4 className="text-sm font-medium text-red-800 mb-1">Deletion Blocked</h4>
                                        <p className="text-sm text-red-700">
                                            The adapter "<strong>{jobConflictModal.adapter?.name}</strong>" cannot be deleted because it has
                                            <strong> {jobConflictModal.jobs.length} associated job(s)</strong>.
                                            You must delete or reassign these jobs before removing the adapter.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Associated Jobs List */}
                            <div className="mb-6">
                                <h4 className="text-lg font-medium text-gray-900 mb-4">Associated Jobs</h4>
                                <div className="space-y-3 max-h-64 overflow-y-auto">
                                    {jobConflictModal.jobs.map((job, index) => (
                                        <div key={job.id || index} className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1">
                                                    <div className="flex items-center">
                                                        <h5 className="font-medium text-gray-900">
                                                            {job.job_name || `Job #${job.id}`}
                                                        </h5>
                                                        <span className={`ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${job.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                                                            job.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                                                                job.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' :
                                                                    'bg-yellow-100 text-yellow-800'
                                                            }`}>
                                                            {job.status || 'Unknown'}
                                                        </span>
                                                    </div>
                                                    <div className="mt-2 text-sm text-gray-600">
                                                        <div className="grid grid-cols-2 gap-4">
                                                            <div>
                                                                <span className="font-medium">Job ID:</span> {job.id}
                                                            </div>
                                                            <div>
                                                                <span className="font-medium">Created:</span> {formatDate(job.created_at)}
                                                            </div>
                                                            {job.extraction_parameters?.doctor_name && (
                                                                <div>
                                                                    <span className="font-medium">Doctor:</span> {job.extraction_parameters.doctor_name}
                                                                </div>
                                                            )}
                                                            {job.extraction_parameters?.medication && (
                                                                <div>
                                                                    <span className="font-medium">Medication:</span> {job.extraction_parameters.medication}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="ml-4">
                                                    <button
                                                        onClick={() => {
                                                            closeJobConflictModal();
                                                            navigate(`/jobs`);
                                                        }}
                                                        className="inline-flex items-center px-3 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                                    >
                                                        View Job
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Resolution Instructions */}
                            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                                <h4 className="text-sm font-medium text-blue-900 mb-2">How to Resolve This</h4>
                                <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                                    <li>Go to the Jobs page and review the associated jobs listed above</li>
                                    <li>Delete any jobs that are no longer needed</li>
                                    <li>For completed jobs, consider if you need to keep them for data retention</li>
                                    <li>Once all associated jobs are removed, you can delete this adapter</li>
                                </ol>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex justify-end space-x-3">
                                <button
                                    onClick={closeJobConflictModal}
                                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-500"
                                >
                                    Close
                                </button>
                                <button
                                    onClick={() => {
                                        closeJobConflictModal();
                                        navigate('/jobs');
                                    }}
                                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    Go to Jobs Page
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Adapters;
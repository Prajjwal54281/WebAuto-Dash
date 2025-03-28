import React, { useState, useEffect } from 'react';
import { io } from 'socket.io-client';
import { portalInspectorApi, liveInspectorApi } from '../services/api';
import toast from 'react-hot-toast';

const LiveInspection = () => {
    const [isInspecting, setIsInspecting] = useState(false);
    const [inspectionId, setInspectionId] = useState(null);
    const [inspectionStatus, setInspectionStatus] = useState('');
    const [inspectionLogs, setInspectionLogs] = useState([]);
    const [formData, setFormData] = useState({
        portal_name: '',
        portal_url: '',
        recording_mode: 'full',
        timeout_minutes: 30,
        headless: false,
        selector_strategy: 'id',
        generate_adapter: true
    });
    const [socket, setSocket] = useState(null);
    const [results, setResults] = useState(null);
    const [syncing, setSyncing] = useState(false);
    const [capabilities, setCapabilities] = useState(null);

    // Initialize socket connection
    useEffect(() => {
        const newSocket = io('http://localhost:5005');
        setSocket(newSocket);

        // Listen for v2 live inspection updates
        newSocket.on('live_inspection_started', (data) => {
            console.log('Live inspection started:', data);
            setInspectionLogs(prev => [...prev, {
                type: 'start',
                message: data.message || '🚀 Advanced live inspection started',
                timestamp: data.timestamp
            }]);
            setInspectionStatus('🚀 Advanced inspection started - browser launching...');
        });

        newSocket.on('live_inspection_update', (data) => {
            console.log('Live inspection update:', data);
            setInspectionLogs(prev => [...prev, {
                type: data.event?.event_type || 'update',
                message: data.event?.message || JSON.stringify(data.event),
                timestamp: data.timestamp
            }]);

            // Update status based on event type
            if (data.event?.event_type === 'navigation') {
                setInspectionStatus('🌐 Navigation detected - analyzing page structure');
            } else if (data.event?.event_type === 'click') {
                setInspectionStatus('🖱️ Click event recorded');
            } else if (data.event?.event_type === 'network') {
                setInspectionStatus('🌐 Network request intercepted');
            } else if (data.event?.event_type === 'popup') {
                setInspectionStatus('📋 Popup dialog detected');
            } else {
                setInspectionStatus('📊 Recording user interactions...');
            }
        });

        newSocket.on('live_inspection_complete_v2', (data) => {
            console.log('Live inspection complete v2:', data);
            setIsInspecting(false);
            setInspectionStatus('✅ Advanced Inspection Complete!');
            setResults(data.results);
            setInspectionLogs(prev => [...prev, {
                type: 'complete',
                message: data.message || '✅ Advanced live inspection completed successfully!',
                timestamp: data.timestamp
            }]);
        });

        newSocket.on('live_inspection_error_v2', (data) => {
            console.log('Live inspection error v2:', data);
            setIsInspecting(false);
            setInspectionStatus('❌ Inspection Failed');
            setInspectionLogs(prev => [...prev, {
                type: 'error',
                message: `❌ Error: ${data.error}`,
                timestamp: data.timestamp
            }]);
        });

        newSocket.on('live_inspection_stop_requested_v2', (data) => {
            console.log('Live inspection stop requested:', data);
            setInspectionStatus('🛑 Stopping inspection - finalizing analysis...');
            setInspectionLogs(prev => [...prev, {
                type: 'stop',
                message: data.message || '🛑 Stop requested - finalizing analysis...',
                timestamp: data.timestamp
            }]);
        });

        return () => {
            newSocket.close();
        };
    }, []);

    // Load capabilities on component mount
    useEffect(() => {
        const loadCapabilities = async () => {
            try {
                const response = await liveInspectorApi.getCapabilities();
                setCapabilities(response.data);
            } catch (error) {
                console.error('Failed to load capabilities:', error);
            }
        };
        loadCapabilities();
    }, []);

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const startLiveInspection = async () => {
        if (!formData.portal_name || !formData.portal_url) {
            alert('Please fill in portal name and URL');
            return;
        }

        try {
            setIsInspecting(true);
            setInspectionStatus('🚀 Starting advanced live inspection...');
            setInspectionLogs([]);
            setResults(null);

            const response = await liveInspectorApi.startInspection(formData);

            if (response.data.success) {
                setInspectionStatus('🌐 Advanced browser launching...');
                setInspectionLogs([{
                    type: 'start',
                    message: response.data.message,
                    timestamp: new Date().toISOString()
                }]);

                // Display v2 features
                if (response.data.features) {
                    setInspectionLogs(prev => [...prev, {
                        type: 'features',
                        message: `Advanced features enabled: ${response.data.features.join(', ')}`,
                        timestamp: new Date().toISOString()
                    }]);
                }
            } else {
                setIsInspecting(false);
                setInspectionStatus('❌ Failed to start');
                alert(`Failed to start inspection: ${response.data.error}`);
            }
        } catch (error) {
            setIsInspecting(false);
            setInspectionStatus('❌ Connection Error');
            alert(`Error starting inspection: ${error.response?.data?.error || error.message}`);
        }
    };

    const stopInspection = async () => {
        if (!inspectionId) {
            // If we don't have an inspection ID, try to stop any active inspection
            try {
                const response = await liveInspectorApi.stopInspection('active');
                if (response.data.success) {
                    setInspectionStatus('🔄 Stopping inspection...');
                }
            } catch (error) {
                console.error('Error stopping inspection:', error);
            }
            return;
        }

        try {
            const response = await liveInspectorApi.stopInspection(inspectionId);
            if (response.data.success) {
                setInspectionStatus('🔄 Stopping advanced inspection...');
            }
        } catch (error) {
            console.error('Error stopping inspection:', error);
        }
    };

    const downloadAdapter = () => {
        if (!results?.analysis_results?.adapter_code) return;

        // Generate clean filename that matches backend convention
        let portalNameClean = formData.portal_name
            .replace(/[^a-zA-Z0-9\-_ ]/g, '') // Remove special characters
            .replace(/\s+/g, '_') // Replace spaces with underscores
            .replace(/-/g, '_') // Replace hyphens with underscores
            .toLowerCase()
            .replace(/_+/g, '_') // Replace multiple underscores with single
            .replace(/^_|_$/g, ''); // Remove leading/trailing underscores

        const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
        const filename = `${portalNameClean}_live_adapter_${timestamp}.py`;

        const blob = new Blob([results.analysis_results.adapter_code], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    };

    const downloadResults = () => {
        if (!results) return;

        // Generate clean filename that matches backend convention
        let portalNameClean = formData.portal_name
            .replace(/[^a-zA-Z0-9\-_ ]/g, '') // Remove special characters
            .replace(/\s+/g, '_') // Replace spaces with underscores
            .replace(/-/g, '_') // Replace hyphens with underscores
            .toLowerCase()
            .replace(/_+/g, '_') // Replace multiple underscores with single
            .replace(/^_|_$/g, ''); // Remove leading/trailing underscores

        const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
        const filename = `${portalNameClean}_inspection_results_${timestamp}.json`;

        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    };

    const handleSyncAdapters = async () => {
        try {
            setSyncing(true);
            console.log('Syncing adapters from filesystem...');

            const response = await portalInspectorApi.syncAdapters();
            console.log('Sync response:', response.data);

            if (response.data.success) {
                const { synced_count, new_adapters } = response.data;

                if (synced_count > 0) {
                    toast.success(
                        `Successfully synced ${synced_count} adapter${synced_count > 1 ? 's' : ''} to the database!\n${new_adapters.join(', ')}`,
                        { duration: 5000 }
                    );
                } else {
                    toast.success('All adapters are already in sync!');
                }
            } else {
                toast.error(`Sync failed: ${response.data.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to sync adapters:', error);
            toast.error(`Failed to sync adapters: ${error.response?.data?.error || error.message}`);
        } finally {
            setSyncing(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-6">
            <div className="bg-white rounded-lg shadow-lg p-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-4">🔍 Live Portal Inspector</h1>
                    <p className="text-gray-600 text-lg">
                        Navigate your patient portal manually while our system records and analyzes the structure to automatically generate an adapter.
                    </p>
                </div>

                {/* Configuration Form */}
                {!isInspecting && !results && (
                    <div className="bg-gray-50 rounded-lg p-6 mb-6">
                        <h2 className="text-xl font-semibold mb-4">Portal Configuration</h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Portal Name
                                </label>
                                <input
                                    type="text"
                                    name="portal_name"
                                    value={formData.portal_name}
                                    onChange={handleInputChange}
                                    placeholder="e.g., Dr. Smith's Patient Portal"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Portal URL
                                </label>
                                <input
                                    type="url"
                                    name="portal_url"
                                    value={formData.portal_url}
                                    onChange={handleInputChange}
                                    placeholder="https://portal.hospital.com"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    required
                                />
                            </div>
                        </div>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Recording Mode
                            </label>
                            <select
                                name="recording_mode"
                                value={formData.recording_mode}
                                onChange={handleInputChange}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="full">Full Recording (All interactions)</option>
                                <option value="login_only">Login Analysis Only</option>
                                <option value="navigation_only">Navigation Patterns Only</option>
                            </select>
                        </div>

                        <div className="mb-6">
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    name="generate_adapter"
                                    checked={formData.generate_adapter}
                                    onChange={handleInputChange}
                                    className="mr-2"
                                />
                                <span className="text-sm text-gray-700">
                                    Automatically generate adapter code after inspection
                                </span>
                            </label>
                        </div>

                        <button
                            onClick={startLiveInspection}
                            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
                        >
                            🚀 Start Live Inspection
                        </button>
                    </div>
                )}

                {/* Instructions Panel */}
                {!isInspecting && !results && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
                        <h3 className="text-lg font-semibold text-blue-900 mb-3">📋 How It Works</h3>
                        <ol className="list-decimal list-inside space-y-2 text-blue-800">
                            <li>Click "Start Live Inspection" - a new browser window will open</li>
                            <li>Navigate to your patient portal and login normally</li>
                            <li>Browse patient lists, view patient details, explore different sections</li>
                            <li>The system records your clicks, forms, and navigation patterns</li>
                            <li>Close the browser when done - adapter code is automatically generated</li>
                        </ol>
                    </div>
                )}

                {/* Status Panel */}
                {isInspecting && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-green-900">Inspection Status</h3>
                            <button
                                onClick={stopInspection}
                                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm"
                            >
                                Stop Inspection
                            </button>
                        </div>

                        <div className="text-green-800 mb-4">
                            <p className="text-lg font-medium">{inspectionStatus}</p>
                            {inspectionId && (
                                <p className="text-sm text-green-600">Inspection ID: {inspectionId}</p>
                            )}
                        </div>

                        <div className="bg-white rounded-md p-4 max-h-60 overflow-y-auto">
                            <h4 className="font-medium mb-2">Real-time Log</h4>
                            <div className="space-y-1 text-sm">
                                {inspectionLogs.map((log, index) => (
                                    <div key={index} className="flex items-start space-x-2">
                                        <span className="text-gray-500 text-xs">
                                            {new Date(log.timestamp).toLocaleTimeString()}
                                        </span>
                                        <span className={`font-medium ${log.type === 'error' ? 'text-red-600' :
                                            log.type === 'complete' ? 'text-green-600' :
                                                'text-blue-600'
                                            }`}>
                                            {log.message}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* Results Panel */}
                {results && (
                    <div className="bg-gray-50 rounded-lg p-6">
                        <h3 className="text-xl font-semibold mb-4">🎉 Inspection Results</h3>

                        {/* Summary Stats */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                            <div className="bg-white rounded-lg p-4 text-center">
                                <div className="text-2xl font-bold text-blue-600">
                                    {results.inspection_summary?.total_actions || 0}
                                </div>
                                <div className="text-sm text-gray-600">Actions Recorded</div>
                            </div>

                            <div className="bg-white rounded-lg p-4 text-center">
                                <div className="text-2xl font-bold text-green-600">
                                    {results.inspection_summary?.pages_visited || 0}
                                </div>
                                <div className="text-sm text-gray-600">Pages Visited</div>
                            </div>

                            <div className="bg-white rounded-lg p-4 text-center">
                                <div className="text-2xl font-bold text-purple-600">
                                    {results.inspection_summary?.elements_discovered || 0}
                                </div>
                                <div className="text-sm text-gray-600">Elements Found</div>
                            </div>

                            <div className="bg-white rounded-lg p-4 text-center">
                                <div className="text-2xl font-bold text-orange-600">
                                    {Math.round(results.inspection_summary?.inspection_duration / 60) || 0}m
                                </div>
                                <div className="text-sm text-gray-600">Duration</div>
                            </div>
                        </div>

                        {/* Portal Characteristics */}
                        {results.portal_characteristics && (
                            <div className="bg-white rounded-lg p-4 mb-4">
                                <h4 className="font-semibold mb-2">Portal Characteristics</h4>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <span className="font-medium">Complexity:</span>
                                        <span className="ml-2 capitalize">{results.portal_characteristics.complexity}</span>
                                    </div>
                                    <div>
                                        <span className="font-medium">Recommended Approach:</span>
                                        <span className="ml-2">{results.portal_characteristics.recommended_approach}</span>
                                    </div>
                                    <div>
                                        <span className="font-medium">Has Patient Tables:</span>
                                        <span className="ml-2">{results.portal_characteristics.has_patient_tables ? '✅' : '❌'}</span>
                                    </div>
                                    <div>
                                        <span className="font-medium">Has Forms:</span>
                                        <span className="ml-2">{results.portal_characteristics.has_forms ? '✅' : '❌'}</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Sync Information */}
                        {results.analysis_results?.adapter_code && (
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                                <div className="flex items-start">
                                    <div className="flex-shrink-0">
                                        <div className="w-5 h-5 bg-blue-400 rounded-full flex items-center justify-center">
                                            <span className="text-white text-xs">ℹ</span>
                                        </div>
                                    </div>
                                    <div className="ml-3">
                                        <h4 className="text-sm font-medium text-blue-800">Next Steps</h4>
                                        <p className="mt-1 text-sm text-blue-700">
                                            Your adapter has been generated! Click <strong>"Sync to Database"</strong> to make it
                                            available in the Portal Adapters page for creating extraction jobs.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex flex-wrap gap-3">
                            {results.analysis_results?.adapter_code && (
                                <button
                                    onClick={downloadAdapter}
                                    className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-medium"
                                >
                                    📥 Download Adapter Code
                                </button>
                            )}

                            <button
                                onClick={downloadResults}
                                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium"
                            >
                                📄 Download Full Report
                            </button>

                            <button
                                onClick={handleSyncAdapters}
                                disabled={syncing}
                                className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                                title="Sync generated adapter to database for use in jobs"
                            >
                                {syncing ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                                        Syncing...
                                    </>
                                ) : (
                                    <>🔄 Sync to Database</>
                                )}
                            </button>

                            <button
                                onClick={() => {
                                    setResults(null);
                                    setInspectionLogs([]);
                                    setInspectionStatus('');
                                    setInspectionId(null);
                                }}
                                className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-lg font-medium"
                            >
                                🔄 New Inspection
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default LiveInspection; 
import React, { useState, useEffect } from 'react';
import { portalInspectorApi } from '../services/api';
import { useSocket } from '../hooks/useSocket';
import toast from 'react-hot-toast';
import {
    BeakerIcon,
    EyeIcon,
    EyeSlashIcon,
    CodeBracketIcon,
    PlayIcon,
    DocumentArrowDownIcon,
    CheckCircleIcon,
    ExclamationCircleIcon,
    ArrowPathIcon,
    CpuChipIcon,
    GlobeAltIcon,
    WrenchScrewdriverIcon,
    SparklesIcon,
    ClipboardDocumentListIcon,
    ShieldCheckIcon,
    BoltIcon,
    AcademicCapIcon,
    ClockIcon,
    PhotoIcon,
    TrashIcon,
    ExclamationTriangleIcon,
    CogIcon,
    XMarkIcon
} from '@heroicons/react/24/outline';

const PortalInspector = ({ onClose }) => {
    const [activeTab, setActiveTab] = useState('analyze');
    const [showPassword, setShowPassword] = useState(false);
    const [portalConfig, setPortalConfig] = useState({
        name: '',
        url: '',
        username: '',
        password: '',
        login_url: ''
    });
    const [analysisType, setAnalysisType] = useState('comprehensive');
    const [analyzing, setAnalyzing] = useState(false);
    const [analysisResults, setAnalysisResults] = useState(null);
    const [selectorTest, setSelectorTest] = useState({
        selector: '',
        expected_count: 1,
        action: 'find'
    });
    const [testResults, setTestResults] = useState(null);
    const [savedAnalyses, setSavedAnalyses] = useState([]);
    const [portalAdapters, setPortalAdapters] = useState([]);
    const [generatedCode, setGeneratedCode] = useState('');
    const [deleteConfirm, setDeleteConfirm] = useState(null);

    const socket = useSocket();

    useEffect(() => {
        fetchSavedAnalyses();
        fetchPortalAdapters();

        if (socket) {
            socket.on('portal_analysis_progress', (data) => {
                toast.loading(data.message, { id: data.analysis_id });
            });

            socket.on('portal_analysis_complete', (data) => {
                toast.success('Portal analysis complete!', { id: data.analysis_id });
                setAnalyzing(false);
                setAnalysisResults(data.results);
                setActiveTab('results');
            });

            socket.on('portal_analysis_error', (data) => {
                toast.error(`Analysis failed: ${data.error}`, { id: data.analysis_id });
                setAnalyzing(false);
            });

            return () => {
                socket.off('portal_analysis_progress');
                socket.off('portal_analysis_complete');
                socket.off('portal_analysis_error');
            };
        }
    }, [socket]);

    const fetchSavedAnalyses = async () => {
        try {
            const response = await portalInspectorApi.getSavedAnalyses();
            setSavedAnalyses(response.data.analyses || []);
        } catch (error) {
            console.error('Failed to fetch saved analyses:', error);
        }
    };

    const fetchPortalAdapters = async () => {
        try {
            const response = await portalInspectorApi.getPortalAdapters();
            setPortalAdapters(response.data.adapters || []);
        } catch (error) {
            console.error('Failed to fetch portal adapters:', error);
        }
    };

    const handleDeleteAdapter = async (adapterId, adapterName) => {
        if (deleteConfirm !== adapterId) {
            setDeleteConfirm(adapterId);
            return;
        }

        try {
            await portalInspectorApi.deleteAdapter(adapterId);
            toast.success(`Adapter "${adapterName}" deleted successfully!`);
            fetchPortalAdapters(); // Refresh the list
            setDeleteConfirm(null);
        } catch (error) {
            toast.error(`Failed to delete adapter: ${error.response?.data?.error || error.message}`);
            setDeleteConfirm(null);
        }
    };

    const handleAnalyzePortal = async (e) => {
        e.preventDefault();
        setAnalyzing(true);
        setAnalysisResults(null);

        try {
            if (analysisType === 'quick') {
                await portalInspectorApi.quickAnalyzePortal(portalConfig);
                toast.success('Quick portal analysis started!');
            } else {
                await portalInspectorApi.analyzePortal(portalConfig);
                toast.success('Comprehensive portal analysis started!');
            }
        } catch (error) {
            toast.error('Failed to start analysis');
            setAnalyzing(false);
        }
    };

    const handleTestSelector = async (e) => {
        e.preventDefault();

        if (!analysisResults) {
            toast.error('Please run portal analysis first');
            return;
        }

        try {
            const response = await portalInspectorApi.testSelector({
                ...selectorTest,
                portal_url: portalConfig.url
            });
            setTestResults(response.data);
            toast.success('Selector test completed!');
        } catch (error) {
            toast.error('Selector test failed');
            setTestResults({ success: false, error: error.message });
        }
    };

    const handleGenerateAdapter = async () => {
        if (!analysisResults) {
            toast.error('Please run portal analysis first');
            return;
        }

        try {
            const response = await portalInspectorApi.generateAdapter({
                portal_config: portalConfig,
                analysis_results: analysisResults
            });
            setGeneratedCode(response.data.adapter_code);
            setActiveTab('code');
            toast.success('Adapter code generated!');
        } catch (error) {
            toast.error('Failed to generate adapter');
        }
    };

    const handleLoadAnalysis = async (filename) => {
        try {
            const response = await portalInspectorApi.getAnalysisDetails(filename);
            setAnalysisResults(response.data);
            setActiveTab('results');
            toast.success('Analysis loaded!');
        } catch (error) {
            toast.error('Failed to load analysis');
        }
    };

    const tabs = [
        { id: 'analyze', name: 'Analyze Portal', icon: BeakerIcon },
        { id: 'results', name: 'Results', icon: ClipboardDocumentListIcon },
        { id: 'test', name: 'Test Selectors', icon: EyeIcon },
        { id: 'adapters', name: 'Portal Adapters', icon: CogIcon },
        { id: 'code', name: 'Generated Code', icon: CodeBracketIcon },
        { id: 'saved', name: 'Saved Analyses', icon: DocumentArrowDownIcon }
    ];

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <h2 className="text-3xl font-bold text-gray-900 flex items-center">
                        <BeakerIcon className="h-8 w-8 text-purple-500 mr-3" />
                        Portal Inspector
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
                    >
                        ×
                    </button>
                </div>

                {/* Tab Navigation */}
                <div className="flex border-b border-gray-200">
                    {tabs.map((tab) => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center px-6 py-4 font-medium ${activeTab === tab.id
                                    ? 'text-purple-600 border-b-2 border-purple-600 bg-purple-50'
                                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                                    }`}
                            >
                                <Icon className="h-5 w-5 mr-2" />
                                {tab.name}
                            </button>
                        );
                    })}
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
                    {/* Analyze Portal Tab */}
                    {activeTab === 'analyze' && (
                        <div className="space-y-6">
                            {/* Portal Analysis Header */}
                            <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl p-6 text-white mb-6">
                                <div className="flex items-center mb-4">
                                    <BeakerIcon className="h-8 w-8 mr-3" />
                                    <h2 className="text-2xl font-bold">Portal Analysis</h2>
                                </div>
                                <p className="text-purple-100">
                                    Automatically analyze medical portals to identify login flows, data extraction points, and generate adapter code.
                                </p>
                            </div>

                            {/* Analysis Type Selection - New Modern Design */}
                            <div className="mb-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Choose Your Analysis Approach</h3>
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    {/* Quick Analysis Card */}
                                    <div
                                        className={`group relative overflow-hidden rounded-xl border-2 cursor-pointer transition-all duration-300 transform hover:scale-[1.02] ${analysisType === 'quick'
                                            ? 'border-yellow-400 bg-gradient-to-br from-yellow-50 to-orange-50 shadow-lg'
                                            : 'border-gray-200 bg-white hover:border-yellow-300 hover:shadow-md'
                                            }`}
                                        onClick={() => setAnalysisType('quick')}
                                    >
                                        {/* Background animation */}
                                        <div className="absolute inset-0 bg-gradient-to-r from-yellow-200/0 to-orange-200/0 group-hover:from-yellow-200/20 group-hover:to-orange-200/20 transition-all duration-300"></div>

                                        {/* Selection Indicator */}
                                        <div className={`absolute top-4 right-4 w-6 h-6 rounded-full border-2 transition-all duration-200 ${analysisType === 'quick'
                                            ? 'border-yellow-400 bg-yellow-400 scale-110'
                                            : 'border-gray-300 bg-white group-hover:border-yellow-300 group-hover:scale-105'
                                            }`}>
                                            {analysisType === 'quick' && (
                                                <CheckCircleIcon className="w-6 h-6 text-white animate-pulse" />
                                            )}
                                        </div>

                                        <div className="relative p-6">
                                            {/* Header */}
                                            <div className="flex items-center mb-4">
                                                <div className={`flex items-center justify-center w-12 h-12 rounded-xl mr-4 transition-all duration-300 ${analysisType === 'quick'
                                                    ? 'bg-yellow-100 scale-110'
                                                    : 'bg-yellow-50 group-hover:bg-yellow-100 group-hover:scale-105'
                                                    }`}>
                                                    <BoltIcon className="h-7 w-7 text-yellow-600" />
                                                </div>
                                                <div>
                                                    <h4 className="text-xl font-bold text-gray-900">Quick Analysis</h4>
                                                    <div className="flex items-center text-sm text-gray-600">
                                                        <ClockIcon className="h-4 w-4 mr-1" />
                                                        <span>2-3 minutes</span>
                                                        <span className="ml-2 text-yellow-600">⚡ Fast</span>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Description */}
                                            <p className="text-gray-600 mb-4">
                                                Fast portal inspection for urgent needs. Basic portal detection, login analysis, and simple data extraction patterns.
                                            </p>

                                            {/* Features */}
                                            <div className="space-y-2">
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-yellow-400 rounded-full mr-3 animate-pulse"></div>
                                                    Portal type identification
                                                </div>
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-yellow-400 rounded-full mr-3 animate-pulse" style={{ animationDelay: '0.1s' }}></div>
                                                    Login functionality check
                                                </div>
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-yellow-400 rounded-full mr-3 animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                                                    Basic data structure analysis
                                                </div>
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-yellow-400 rounded-full mr-3 animate-pulse" style={{ animationDelay: '0.3s' }}></div>
                                                    Immediate recommendations
                                                </div>
                                            </div>
                                        </div>

                                        {/* Bottom accent */}
                                        <div className={`h-1 w-full transition-all duration-300 ${analysisType === 'quick'
                                            ? 'bg-gradient-to-r from-yellow-400 to-orange-400'
                                            : 'bg-gray-100 group-hover:bg-gradient-to-r group-hover:from-yellow-300 group-hover:to-orange-300'
                                            }`}></div>
                                    </div>

                                    {/* Comprehensive Analysis Card */}
                                    <div
                                        className={`group relative overflow-hidden rounded-xl border-2 cursor-pointer transition-all duration-300 transform hover:scale-[1.02] ${analysisType === 'comprehensive'
                                            ? 'border-purple-400 bg-gradient-to-br from-purple-50 to-blue-50 shadow-lg'
                                            : 'border-gray-200 bg-white hover:border-purple-300 hover:shadow-md'
                                            }`}
                                        onClick={() => setAnalysisType('comprehensive')}
                                    >
                                        {/* Background animation */}
                                        <div className="absolute inset-0 bg-gradient-to-r from-purple-200/0 to-blue-200/0 group-hover:from-purple-200/20 group-hover:to-blue-200/20 transition-all duration-300"></div>

                                        {/* Selection Indicator */}
                                        <div className={`absolute top-4 right-4 w-6 h-6 rounded-full border-2 transition-all duration-200 ${analysisType === 'comprehensive'
                                            ? 'border-purple-400 bg-purple-400 scale-110'
                                            : 'border-gray-300 bg-white group-hover:border-purple-300 group-hover:scale-105'
                                            }`}>
                                            {analysisType === 'comprehensive' && (
                                                <CheckCircleIcon className="w-6 h-6 text-white animate-pulse" />
                                            )}
                                        </div>

                                        <div className="relative p-6">
                                            {/* Header */}
                                            <div className="flex items-center mb-4">
                                                <div className={`flex items-center justify-center w-12 h-12 rounded-xl mr-4 transition-all duration-300 ${analysisType === 'comprehensive'
                                                    ? 'bg-purple-100 scale-110'
                                                    : 'bg-purple-50 group-hover:bg-purple-100 group-hover:scale-105'
                                                    }`}>
                                                    <BeakerIcon className="h-7 w-7 text-purple-600" />
                                                </div>
                                                <div>
                                                    <h4 className="text-xl font-bold text-gray-900">Comprehensive Analysis</h4>
                                                    <div className="flex items-center text-sm text-gray-600">
                                                        <ClockIcon className="h-4 w-4 mr-1" />
                                                        <span>5-7 minutes</span>
                                                        <SparklesIcon className="h-4 w-4 ml-2 text-purple-500" />
                                                        <span className="ml-1 text-purple-600">Advanced</span>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Description */}
                                            <p className="text-gray-600 mb-4">
                                                Deep portal analysis with 5-phase inspection: technology detection, authentication flow, navigation mapping, data element discovery, and interaction pattern analysis.
                                            </p>

                                            {/* Features */}
                                            <div className="space-y-2">
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-purple-400 rounded-full mr-3 animate-pulse"></div>
                                                    5-phase comprehensive analysis
                                                </div>
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-purple-400 rounded-full mr-3 animate-pulse" style={{ animationDelay: '0.1s' }}></div>
                                                    Advanced CAPTCHA detection
                                                </div>
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-purple-400 rounded-full mr-3 animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                                                    Multi-strategy data extraction
                                                </div>
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-purple-400 rounded-full mr-3 animate-pulse" style={{ animationDelay: '0.3s' }}></div>
                                                    Auto-generated adapter code
                                                </div>
                                                <div className="flex items-center text-sm text-gray-700">
                                                    <div className="w-2 h-2 bg-purple-400 rounded-full mr-3 animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                                                    Database integration
                                                </div>
                                            </div>
                                        </div>

                                        {/* Bottom accent */}
                                        <div className={`h-1 w-full transition-all duration-300 ${analysisType === 'comprehensive'
                                            ? 'bg-gradient-to-r from-purple-400 to-blue-400'
                                            : 'bg-gray-100 group-hover:bg-gradient-to-r group-hover:from-purple-300 group-hover:to-blue-300'
                                            }`}></div>
                                    </div>
                                </div>
                            </div>

                            <form onSubmit={handleAnalyzePortal} className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Portal Name</label>
                                        <input
                                            type="text"
                                            value={portalConfig.name}
                                            onChange={(e) => setPortalConfig(prev => ({ ...prev, name: e.target.value }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                            placeholder="e.g., Epic MyChart"
                                            required
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Portal URL</label>
                                        <input
                                            type="url"
                                            value={portalConfig.url}
                                            onChange={(e) => setPortalConfig(prev => ({ ...prev, url: e.target.value }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                            placeholder="https://portal.example.com"
                                            required
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                                        <input
                                            type="text"
                                            value={portalConfig.username}
                                            onChange={(e) => setPortalConfig(prev => ({ ...prev, username: e.target.value }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                            required
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                                        <div className="flex items-center">
                                            <input
                                                type={showPassword ? 'text' : 'password'}
                                                value={portalConfig.password}
                                                onChange={(e) => setPortalConfig(prev => ({ ...prev, password: e.target.value }))}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                                required
                                            />
                                            <button
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    setShowPassword(!showPassword);
                                                }}
                                                className="text-gray-400 hover:text-gray-600 text-sm px-2"
                                            >
                                                {showPassword ? <EyeIcon className="h-5 w-5" /> : <EyeSlashIcon className="h-5 w-5" />}
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Login URL (optional)</label>
                                    <input
                                        type="url"
                                        value={portalConfig.login_url}
                                        onChange={(e) => setPortalConfig(prev => ({ ...prev, login_url: e.target.value }))}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                        placeholder="Leave empty to auto-detect"
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={analyzing}
                                    className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-3 rounded-lg font-medium hover:from-purple-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {analyzing ? (
                                        <div className="flex items-center justify-center">
                                            <ArrowPathIcon className="animate-spin h-5 w-5 mr-2" />
                                            Analyzing Portal...
                                        </div>
                                    ) : (
                                        <div className="flex items-center justify-center">
                                            <BeakerIcon className="h-5 w-5 mr-2" />
                                            {analysisType === 'quick' ? '⚡ Start Quick Analysis' : '🔬 Start Comprehensive Analysis'}
                                        </div>
                                    )}
                                </button>
                            </form>
                        </div>
                    )}

                    {/* Results Tab */}
                    {activeTab === 'results' && (
                        <div className="space-y-6">
                            {analysisResults ? (
                                <>
                                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                                        <h3 className="font-semibold text-green-900 flex items-center mb-2">
                                            <CheckCircleIcon className="h-5 w-5 mr-2" />
                                            Analysis Complete
                                        </h3>
                                        <p className="text-green-700 text-sm">
                                            Portal analysis completed successfully. Review the findings below.
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        {/* Login Elements */}
                                        <div className="bg-white border border-gray-200 rounded-lg p-4">
                                            <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                                                <CpuChipIcon className="h-5 w-5 mr-2 text-blue-500" />
                                                Login Elements
                                            </h4>
                                            <div className="space-y-2">
                                                {Array.isArray(analysisResults.login_elements) && analysisResults.login_elements.length > 0 ? (
                                                    analysisResults.login_elements.map((element, index) => (
                                                        <div key={index} className="text-sm bg-gray-50 p-2 rounded">
                                                            <span className="font-mono text-blue-600">{element.selector}</span>
                                                            <span className="text-gray-600 ml-2">({element.type})</span>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <p className="text-gray-500 text-sm">No login elements found</p>
                                                )}
                                            </div>
                                        </div>

                                        {/* Data Elements */}
                                        <div className="bg-white border border-gray-200 rounded-lg p-4">
                                            <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                                                <ClipboardDocumentListIcon className="h-5 w-5 mr-2 text-green-500" />
                                                Data Elements
                                            </h4>
                                            <div className="space-y-2">
                                                {Array.isArray(analysisResults.data_elements) && analysisResults.data_elements.length > 0 ? (
                                                    analysisResults.data_elements.map((element, index) => (
                                                        <div key={index} className="text-sm bg-gray-50 p-2 rounded">
                                                            <span className="font-mono text-green-600">{element.selector}</span>
                                                            <span className="text-gray-600 ml-2">({element.data_type})</span>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <p className="text-gray-500 text-sm">No data elements found</p>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex space-x-4">
                                        <button
                                            onClick={handleGenerateAdapter}
                                            className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 text-white py-3 rounded-lg font-medium hover:from-green-700 hover:to-emerald-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                                        >
                                            <div className="flex items-center justify-center">
                                                <WrenchScrewdriverIcon className="h-5 w-5 mr-2" />
                                                Generate Adapter Code
                                            </div>
                                        </button>

                                        <button
                                            onClick={() => setActiveTab('test')}
                                            className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-medium hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            <div className="flex items-center justify-center">
                                                <EyeIcon className="h-5 w-5 mr-2" />
                                                Test Selectors
                                            </div>
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <div className="text-center py-12">
                                    <BeakerIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Analysis Results</h3>
                                    <p className="text-gray-500 mb-4">Run a portal analysis to see results here.</p>
                                    <button
                                        onClick={() => setActiveTab('analyze')}
                                        className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700"
                                    >
                                        Start Analysis
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Test Selectors Tab */}
                    {activeTab === 'test' && (
                        <div className="space-y-6">
                            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                                <h3 className="font-semibold text-yellow-900 flex items-center mb-2">
                                    <EyeIcon className="h-5 w-5 mr-2" />
                                    Selector Testing
                                </h3>
                                <p className="text-yellow-700 text-sm">
                                    Test CSS selectors to ensure they work correctly on the portal.
                                </p>
                            </div>

                            <form onSubmit={handleTestSelector} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">CSS Selector</label>
                                    <input
                                        type="text"
                                        value={selectorTest.selector}
                                        onChange={(e) => setSelectorTest(prev => ({ ...prev, selector: e.target.value }))}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                                        placeholder="e.g., input[type='email'], .patient-name"
                                        required
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Expected Count</label>
                                        <input
                                            type="number"
                                            value={selectorTest.expected_count}
                                            onChange={(e) => setSelectorTest(prev => ({ ...prev, expected_count: parseInt(e.target.value) }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            min="1"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
                                        <select
                                            value={selectorTest.action}
                                            onChange={(e) => setSelectorTest(prev => ({ ...prev, action: e.target.value }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        >
                                            <option value="find">Find Element</option>
                                            <option value="click">Click Element</option>
                                            <option value="get_text">Get Text</option>
                                            <option value="get_value">Get Value</option>
                                        </select>
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-medium hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <div className="flex items-center justify-center">
                                        <PlayIcon className="h-5 w-5 mr-2" />
                                        Test Selector
                                    </div>
                                </button>
                            </form>

                            {testResults && (
                                <div className={`border rounded-lg p-4 ${testResults.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                                    }`}>
                                    <h4 className={`font-semibold mb-2 flex items-center ${testResults.success ? 'text-green-900' : 'text-red-900'
                                        }`}>
                                        {testResults.success ? (
                                            <CheckCircleIcon className="h-5 w-5 mr-2" />
                                        ) : (
                                            <ExclamationCircleIcon className="h-5 w-5 mr-2" />
                                        )}
                                        Test Results
                                    </h4>
                                    <div className="text-sm space-y-1">
                                        <p><strong>Elements Found:</strong> {testResults.count || 0}</p>
                                        {testResults.result && <p><strong>Result:</strong> {testResults.result}</p>}
                                        {testResults.error && <p><strong>Error:</strong> {testResults.error}</p>}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Generated Code Tab */}
                    {activeTab === 'code' && (
                        <div className="space-y-6">
                            {generatedCode ? (
                                <>
                                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                                        <h3 className="font-semibold text-green-900 flex items-center mb-2">
                                            <SparklesIcon className="h-5 w-5 mr-2" />
                                            Adapter Code Generated
                                        </h3>
                                        <p className="text-green-700 text-sm">
                                            Python adapter code has been generated based on the portal analysis.
                                        </p>
                                    </div>

                                    <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                                        <pre className="text-green-400 text-sm font-mono whitespace-pre-wrap">
                                            {generatedCode}
                                        </pre>
                                    </div>

                                    <button
                                        onClick={() => {
                                            navigator.clipboard.writeText(generatedCode);
                                            toast.success('Code copied to clipboard!');
                                        }}
                                        className="w-full bg-gradient-to-r from-gray-600 to-gray-700 text-white py-3 rounded-lg font-medium hover:from-gray-700 hover:to-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500"
                                    >
                                        <div className="flex items-center justify-center">
                                            <DocumentArrowDownIcon className="h-5 w-5 mr-2" />
                                            Copy to Clipboard
                                        </div>
                                    </button>
                                </>
                            ) : (
                                <div className="text-center py-12">
                                    <CodeBracketIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Generated Code</h3>
                                    <p className="text-gray-500 mb-4">Generate adapter code from analysis results.</p>
                                    <button
                                        onClick={() => setActiveTab('results')}
                                        className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700"
                                    >
                                        View Results
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Portal Adapters Tab */}
                    {activeTab === 'adapters' && (
                        <div className="space-y-6">
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <h3 className="font-semibold text-blue-900 flex items-center mb-2">
                                    <CogIcon className="h-5 w-5 mr-2" />
                                    Portal Adapters Management
                                </h3>
                                <p className="text-blue-700 text-sm">
                                    Manage your saved portal adapters. You can delete adapters that are no longer needed.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 gap-4">
                                {portalAdapters.length === 0 ? (
                                    <div className="text-center py-8">
                                        <CogIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                                        <p className="text-gray-500">No portal adapters found</p>
                                        <p className="text-sm text-gray-400">Create some adapters using the Portal Analysis tab</p>
                                    </div>
                                ) : (
                                    portalAdapters.map((adapter) => (
                                        <div key={adapter.id} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1">
                                                    <div className="flex items-center">
                                                        <h4 className="font-semibold text-gray-900">{adapter.name}</h4>
                                                        <span className={`ml-3 px-2 py-1 text-xs rounded-full ${adapter.is_active
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-gray-100 text-gray-800'
                                                            }`}>
                                                            {adapter.is_active ? 'Active' : 'Inactive'}
                                                        </span>
                                                    </div>
                                                    <p className="text-sm text-gray-600 mt-1">{adapter.description}</p>
                                                    <div className="flex items-center mt-2 text-xs text-gray-500">
                                                        <span>Created: {new Date(adapter.created_at).toLocaleDateString()}</span>
                                                        {adapter.updated_at && (
                                                            <span className="ml-4">Updated: {new Date(adapter.updated_at).toLocaleDateString()}</span>
                                                        )}
                                                        {adapter.script_filename && (
                                                            <span className="ml-4">File: {adapter.script_filename}</span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    <button
                                                        onClick={() => handleDeleteAdapter(adapter.id, adapter.name)}
                                                        className="text-red-600 hover:text-red-800 p-2 rounded-lg hover:bg-red-50 transition-colors"
                                                        title="Delete adapter"
                                                    >
                                                        <TrashIcon className="h-5 w-5" />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>

                            {/* Enhanced Delete Confirmation Modal */}
                            {deleteConfirm && (
                                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                                    <div className="bg-white rounded-xl shadow-2xl max-w-md w-full transform transition-all">
                                        {/* Modal Header */}
                                        <div className="px-6 py-4 border-b border-gray-200">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center">
                                                    <div className="flex items-center justify-center w-10 h-10 bg-red-100 rounded-full mr-3">
                                                        <ExclamationTriangleIcon className="h-6 w-6 text-red-600" />
                                                    </div>
                                                    <h3 className="text-lg font-semibold text-gray-900">Delete Adapter</h3>
                                                </div>
                                                <button
                                                    onClick={() => setDeleteConfirm(null)}
                                                    className="text-gray-400 hover:text-gray-600 transition-colors"
                                                >
                                                    <XMarkIcon className="h-6 w-6" />
                                                </button>
                                            </div>
                                        </div>

                                        {/* Modal Body */}
                                        <div className="px-6 py-4">
                                            <p className="text-gray-700 mb-4">
                                                Are you sure you want to delete this adapter? This action cannot be undone.
                                            </p>

                                            {/* Adapter Info */}
                                            <div className="bg-gray-50 rounded-lg p-4 mb-4">
                                                <div className="flex items-center">
                                                    <CogIcon className="h-5 w-5 text-gray-400 mr-2" />
                                                    <span className="font-medium text-gray-900">
                                                        {portalAdapters.find(a => a.id === deleteConfirm)?.name}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-500 mt-1">
                                                    Created: {new Date(portalAdapters.find(a => a.id === deleteConfirm)?.created_at).toLocaleDateString()}
                                                </p>
                                            </div>

                                            {/* Warning */}
                                            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                                                <div className="flex">
                                                    <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2 flex-shrink-0 mt-0.5" />
                                                    <div>
                                                        <p className="text-sm text-red-800 font-medium">Warning</p>
                                                        <p className="text-sm text-red-700 mt-1">
                                                            Deleting this adapter will permanently remove all associated configuration and scripts.
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Modal Footer */}
                                        <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end space-x-3">
                                            <button
                                                onClick={() => setDeleteConfirm(null)}
                                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={() => {
                                                    const adapter = portalAdapters.find(a => a.id === deleteConfirm);
                                                    handleDeleteAdapter(deleteConfirm, adapter?.name);
                                                }}
                                                className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                            >
                                                Delete Adapter
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Saved Analyses Tab */}
                    {activeTab === 'saved' && (
                        <div className="space-y-6">
                            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                                <h3 className="font-semibold text-gray-900 flex items-center mb-2">
                                    <DocumentArrowDownIcon className="h-5 w-5 mr-2" />
                                    Saved Portal Analyses
                                </h3>
                                <p className="text-gray-700 text-sm">
                                    Previously analyzed portals that can be reloaded for further work.
                                </p>
                            </div>

                            {savedAnalyses.length > 0 ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {savedAnalyses.map((analysis, index) => (
                                        <div key={index} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                                            <h4 className="font-semibold text-gray-900 mb-2">{analysis.name}</h4>
                                            <p className="text-sm text-gray-600 mb-2">{analysis.url}</p>
                                            <p className="text-xs text-gray-500 mb-3">
                                                Analyzed: {new Date(analysis.created_at).toLocaleDateString()}
                                            </p>
                                            <button
                                                onClick={() => handleLoadAnalysis(analysis.filename)}
                                                className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors"
                                            >
                                                Load Analysis
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-12">
                                    <DocumentArrowDownIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Saved Analyses</h3>
                                    <p className="text-gray-500 mb-4">Analyze portals to save them for future use.</p>
                                    <button
                                        onClick={() => setActiveTab('analyze')}
                                        className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700"
                                    >
                                        Start Analysis
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default PortalInspector; 
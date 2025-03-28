import React, { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { jobsApi } from '../../services/api';
import {
    HomeIcon,
    ClipboardDocumentListIcon,
    WrenchScrewdriverIcon,
    Bars3Icon,
    XMarkIcon,
    UserGroupIcon,
    MagnifyingGlassIcon
} from '@heroicons/react/24/outline';
import {
    HomeIcon as HomeSolid,
    ClipboardDocumentListIcon as ClipboardSolid,
    WrenchScrewdriverIcon as WrenchSolid,
    UserGroupIcon as UserGroupSolid,
    MagnifyingGlassIcon as MagnifyingGlassSolid
} from '@heroicons/react/24/solid';

const navigation = [
    {
        name: 'Dashboard',
        to: '/',
        icon: HomeIcon,
        iconSolid: HomeSolid,
        description: 'Overview & Analytics'
    },
    {
        name: 'Patient Data',
        to: '/patients',
        icon: UserGroupIcon,
        iconSolid: UserGroupSolid,
        description: 'Extracted Records'
    },
    {
        name: 'Extraction Jobs',
        to: '/jobs',
        icon: ClipboardDocumentListIcon,
        iconSolid: ClipboardSolid,
        description: 'Manage Extractions'
    },
    {
        name: 'Live Inspector',
        to: '/live-inspection',
        icon: MagnifyingGlassIcon,
        iconSolid: MagnifyingGlassSolid,
        description: 'Analyze New Portals'
    },
    {
        name: 'Portal Adapters',
        to: '/adapters',
        icon: WrenchScrewdriverIcon,
        iconSolid: WrenchSolid,
        description: 'System Configuration'
    },
];

const MainLayout = () => {
    const [activeJobsCount, setActiveJobsCount] = useState(0);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const location = useLocation();

    useEffect(() => {
        const fetchActiveJobs = async () => {
            try {
                const response = await jobsApi.getActive();
                // Handle the response format: { success: true, active_jobs: {...} }
                const activeJobs = response.data.active_jobs || {};
                setActiveJobsCount(Object.keys(activeJobs).length);
            } catch (error) {
                console.error('Failed to fetch active jobs:', error);
                setActiveJobsCount(0);
            }
        };

        // Fetch immediately
        fetchActiveJobs();

        // Poll every 10 seconds for updates (reduced from 5 seconds)
        const interval = setInterval(fetchActiveJobs, 10000);

        return () => clearInterval(interval);
    }, []);

    const isActive = (path) => {
        if (path === '/') {
            return location.pathname === '/';
        }
        return location.pathname.startsWith(path);
    };

    return (
        <div className="h-screen bg-gray-50 flex overflow-hidden">
            {/* Mobile/Tablet sidebar overlay */}
            {sidebarOpen && (
                <div className="fixed inset-0 z-40 xl:hidden">
                    <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
                </div>
            )}

            {/* Sidebar - Responsive */}
            <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-xl transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} transition-transform duration-300 ease-in-out xl:translate-x-0 xl:static xl:inset-0 border-r border-gray-200 flex flex-col`}>
                {/* Header */}
                <div className="flex items-center justify-between h-16 px-6 bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 border-b border-blue-800 flex-shrink-0">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-lg">
                                <span className="text-blue-600 font-bold text-xl">W</span>
                            </div>
                        </div>
                        <div className="ml-4">
                            <h1 className="text-xl font-bold text-white">WebAutoDash</h1>
                            <p className="text-xs text-blue-200">Medical Data Extraction</p>
                        </div>
                    </div>
                    <button
                        onClick={() => setSidebarOpen(false)}
                        className="xl:hidden text-white hover:text-gray-200 p-2"
                    >
                        <XMarkIcon className="h-6 w-6" />
                    </button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-6 py-6 overflow-y-auto">
                    <div className="space-y-2">
                        {navigation.map((item) => {
                            const isCurrentPage = isActive(item.to);
                            const IconComponent = isCurrentPage ? item.iconSolid : item.icon;

                            return (
                                <Link
                                    key={item.name}
                                    to={item.to}
                                    onClick={() => setSidebarOpen(false)}
                                    className={`group flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${isCurrentPage
                                        ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg'
                                        : 'text-gray-700 hover:bg-blue-50 hover:text-blue-700'
                                        }`}
                                >
                                    <IconComponent
                                        className={`flex-shrink-0 h-5 w-5 mr-3 ${isCurrentPage ? 'text-white' : 'text-gray-500 group-hover:text-blue-600'
                                            }`}
                                    />
                                    <div className="flex-1">
                                        <div className="font-semibold">{item.name}</div>
                                        <div className={`text-xs mt-0.5 ${isCurrentPage ? 'text-blue-100' : 'text-gray-500 group-hover:text-blue-600'
                                            }`}>
                                            {item.description}
                                        </div>
                                    </div>
                                </Link>
                            );
                        })}
                    </div>
                </nav>

                {/* Bottom Section */}
                <div className="flex-shrink-0 p-6 border-t border-gray-200 bg-gray-50">
                    {/* Active Jobs Indicator */}
                    {activeJobsCount > 0 && (
                        <div className="mb-4 p-3 bg-green-50 rounded-xl border border-green-200">
                            <div className="flex items-center">
                                <div className="flex-shrink-0">
                                    <div className="h-3 w-3 bg-green-400 rounded-full animate-pulse"></div>
                                </div>
                                <div className="ml-3">
                                    <p className="text-sm font-medium text-green-800">
                                        {activeJobsCount} Active Extraction{activeJobsCount !== 1 ? 's' : ''}
                                    </p>
                                    <p className="text-xs text-green-600">Processing patient data...</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* System Status */}
                    <div className="p-3 bg-blue-50 rounded-xl border border-blue-200">
                        <div className="flex items-center">
                            <div className="w-2 h-2 bg-green-400 rounded-full mr-3"></div>
                            <div>
                                <p className="text-sm font-medium text-gray-700">System Status</p>
                                <p className="text-xs text-green-600 font-semibold">Online & Secure</p>
                                <p className="text-xs text-gray-500 mt-1">made by Prajjwal Mishra</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Mobile/Tablet Layout */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Mobile/Tablet header */}
                <div className="xl:hidden bg-white shadow-sm border-b border-gray-200">
                    <div className="flex items-center justify-between h-16 px-4">
                        <button
                            onClick={() => setSidebarOpen(true)}
                            className="text-gray-500 hover:text-gray-600 p-2 rounded-lg hover:bg-gray-100"
                        >
                            <Bars3Icon className="h-6 w-6" />
                        </button>
                        <div className="flex items-center">
                            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
                                <span className="text-white font-bold text-sm">W</span>
                            </div>
                            <h1 className="text-lg font-semibold text-gray-900">WebAutoDash</h1>
                        </div>
                        {/* Show active jobs indicator on mobile/tablet */}
                        {activeJobsCount > 0 ? (
                            <div className="flex items-center bg-green-100 px-2 py-1 rounded-full">
                                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2"></div>
                                <span className="text-xs font-medium text-green-800">{activeJobsCount}</span>
                            </div>
                        ) : (
                            <div className="w-10"></div>
                        )}
                    </div>
                </div>

                {/* Main content */}
                <main className="flex-1 overflow-y-auto">
                    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-4 sm:py-6">
                        <Outlet />
                    </div>
                </main>
            </div>
        </div>
    );
};

export default MainLayout; 
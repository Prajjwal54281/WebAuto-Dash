import React, { useState, useEffect } from 'react';
import { realtimeApi } from '../services/api';
import { useSocket } from '../hooks/useSocket';
import {
    CpuChipIcon,
    HeartIcon,
    ClockIcon,
    ChartBarIcon,
    ExclamationTriangleIcon,
    CheckCircleIcon,
    ArrowTrendingUpIcon,
    ArrowTrendingDownIcon,
    BoltIcon,
    WrenchScrewdriverIcon
} from '@heroicons/react/24/outline';

const SystemMonitor = ({ className = '' }) => {
    const [stats, setStats] = useState({
        total_jobs: 0,
        active_jobs: 0,
        completed_jobs: 0,
        failed_jobs: 0,
        recent_activity: 0,
        success_rate: 0,
        active_adapters: 0,
        system_health: 'healthy',
        last_updated: new Date().toISOString()
    });
    const [isLoading, setIsLoading] = useState(true);
    const [healthHistory, setHealthHistory] = useState([]);

    const socket = useSocket();

    useEffect(() => {
        fetchSystemStats();

        if (socket) {
            socket.on('system_stats_update', (data) => {
                setStats(data.stats);
                updateHealthHistory(data.stats);
            });

            return () => {
                socket.off('system_stats_update');
            };
        }
    }, [socket]);

    const fetchSystemStats = async () => {
        try {
            const response = await realtimeApi.getSystemStats();
            if (response.data.success) {
                setStats(response.data.stats);
                updateHealthHistory(response.data.stats);
            }
        } catch (error) {
            console.error('Failed to fetch system stats:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const updateHealthHistory = (newStats) => {
        setHealthHistory(prev => {
            const newEntry = {
                timestamp: Date.now(),
                health: newStats.system_health,
                active_jobs: newStats.active_jobs,
                success_rate: newStats.success_rate
            };
            return [...prev.slice(-9), newEntry]; // Keep last 10 entries
        });
    };

    const getHealthColor = (health) => {
        switch (health) {
            case 'healthy': return 'text-green-600 bg-green-100';
            case 'busy': return 'text-yellow-600 bg-yellow-100';
            case 'critical': return 'text-red-600 bg-red-100';
            default: return 'text-gray-600 bg-gray-100';
        }
    };

    const getHealthIcon = (health) => {
        switch (health) {
            case 'healthy': return <CheckCircleIcon className="h-5 w-5" />;
            case 'busy': return <ExclamationTriangleIcon className="h-5 w-5" />;
            case 'critical': return <ExclamationTriangleIcon className="h-5 w-5" />;
            default: return <HeartIcon className="h-5 w-5" />;
        }
    };

    const getTrendIcon = (current, previous) => {
        if (!previous) return null;
        if (current > previous) return <ArrowTrendingUpIcon className="h-4 w-4 text-green-500" />;
        if (current < previous) return <ArrowTrendingDownIcon className="h-4 w-4 text-red-500" />;
        return null;
    };

    if (isLoading) {
        return (
            <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
                <div className="animate-pulse">
                    <div className="h-6 bg-gray-200 rounded mb-4"></div>
                    <div className="space-y-3">
                        <div className="h-4 bg-gray-200 rounded"></div>
                        <div className="h-4 bg-gray-200 rounded"></div>
                        <div className="h-4 bg-gray-200 rounded"></div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
            {/* Header */}
            <div className="p-6 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                        <CpuChipIcon className="h-6 w-6 text-blue-500 mr-2" />
                        System Monitor
                    </h3>
                    <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${getHealthColor(stats.system_health)}`}>
                        {getHealthIcon(stats.system_health)}
                        <span className="ml-1 capitalize">{stats.system_health}</span>
                    </div>
                </div>
            </div>

            {/* Detailed Metrics Only */}
            <div className="p-6">
                <div className="space-y-4">
                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                        <span className="text-sm text-gray-600">Total Jobs</span>
                        <div className="flex items-center space-x-2">
                            <span className="text-sm font-medium text-gray-900">{stats.total_jobs}</span>
                            {healthHistory.length >= 2 && getTrendIcon(
                                stats.total_jobs,
                                healthHistory[healthHistory.length - 2]?.total_jobs
                            )}
                        </div>
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                        <span className="text-sm text-gray-600">Failed Jobs</span>
                        <div className="flex items-center space-x-2">
                            <span className="text-sm font-medium text-gray-900">{stats.failed_jobs}</span>
                            {healthHistory.length >= 2 && getTrendIcon(
                                stats.failed_jobs,
                                healthHistory[healthHistory.length - 2]?.failed_jobs
                            )}
                        </div>
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                        <span className="text-sm text-gray-600">Recent Activity (24h)</span>
                        <span className="text-sm font-medium text-gray-900">{stats.recent_activity}</span>
                    </div>

                    <div className="flex items-center justify-between py-2">
                        <span className="text-sm text-gray-600">Last Updated</span>
                        <span className="text-xs text-gray-500">
                            {new Date(stats.last_updated).toLocaleTimeString()}
                        </span>
                    </div>
                </div>

                {/* Mini Health History Chart */}
                {healthHistory.length > 1 && (
                    <div className="mt-6">
                        <h4 className="text-sm font-medium text-gray-700 mb-3">System Health Trend</h4>
                        <div className="flex items-end space-x-1 h-12">
                            {healthHistory.map((entry, index) => (
                                <div
                                    key={index}
                                    className={`flex-1 rounded-t ${entry.health === 'healthy' ? 'bg-green-200' :
                                            entry.health === 'busy' ? 'bg-yellow-200' : 'bg-red-200'
                                        }`}
                                    style={{
                                        height: `${Math.max(20, (entry.success_rate / 100) * 100)}%`
                                    }}
                                    title={`${entry.health} - ${entry.success_rate}% success rate`}
                                />
                            ))}
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>Past</span>
                            <span>Current</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SystemMonitor; 